"""Allocation layer; weight caps/turnover are distinct from subset count constraints.

Turnover is half the L1 change, including forced liquidation outside the universe.
Fees apply to total traded notional (twice turnover). No historical holdings means
an initial portfolio, for which turnover and trading costs are not estimated.
"""

from itertools import combinations
from time import perf_counter

import numpy as np


def _previous(instance, previous_weights):
    if previous_weights is None:
        return np.zeros(instance.n), 0.0, False
    if isinstance(previous_weights, dict):
        all_values = np.asarray(list(previous_weights.values()), float)
        prior = np.array([previous_weights.get(s, 0.0) for s in instance.symbols], float)
        outside = sum(float(w) for s, w in previous_weights.items() if s not in instance.symbols)
    else:
        prior = np.asarray(previous_weights, float)
        all_values, outside = prior, 0.0
        if prior.shape != (instance.n,):
            raise ValueError("Previous weights must align with symbols or use a symbol dictionary.")
    if not np.isfinite(all_values).all() or np.any(all_values < 0) or not np.isclose(all_values.sum(), 1):
        raise ValueError("Previous portfolio must be finite, long-only and fully invested.")
    return prior, float(outside), True


def _validate(min_weight, max_weight, sector_caps, turnover_limit, cost_bps):
    if not 0 <= min_weight <= max_weight <= 1:
        raise ValueError("Require 0 <= min_weight <= max_weight <= 1.")
    if any(not np.isfinite(c) or not 0 <= c <= 1 for c in (sector_caps or {}).values()):
        raise ValueError("Sector weight caps must lie in [0,1].")
    if turnover_limit is not None and (not np.isfinite(turnover_limit) or turnover_limit < 0):
        raise ValueError("Turnover limit must be finite and nonnegative.")
    if not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be finite and nonnegative.")


def _weight_violations(
    instance,
    weights,
    support,
    min_weight,
    max_weight,
    sector_caps,
    previous,
    outside,
    has_previous,
    turnover_limit,
):
    tol, errors = 2e-5, []
    if abs(sum(weights) - 1) > tol:
        errors.append("full investment")
    if np.any(weights < min_weight * support - tol) or np.any(weights > max_weight * support + tol):
        errors.append("support/weight bounds")
    for sector, cap in (sector_caps or {}).items():
        if sum(weights[i] for i, s in enumerate(instance.sectors) if s == sector) > cap + tol:
            errors.append(f"sector weight cap: {sector}")
    turnover = 0.5 * (np.abs(weights - previous).sum() + outside) if has_previous else None
    if has_previous and turnover_limit is not None and turnover > turnover_limit + tol:
        errors.append("turnover limit")
    return errors, turnover


def allocate(
    instance,
    bits,
    min_weight=0.05,
    max_weight=0.5,
    sector_caps=None,
    previous_weights=None,
    turnover_limit=None,
    cost_bps=10,
):
    return _continuous(
        instance,
        bits,
        min_weight,
        max_weight,
        sector_caps,
        previous_weights,
        turnover_limit,
        cost_bps,
        "conditional_allocation",
    )


def continuous_mvo(
    instance,
    min_weight=0.0,
    max_weight=0.5,
    sector_caps=None,
    previous_weights=None,
    turnover_limit=None,
    cost_bps=10,
):
    """Continuous relaxation: no exact-K or sector *count* requirements."""
    return _continuous(
        instance,
        None,
        min_weight,
        max_weight,
        sector_caps,
        previous_weights,
        turnover_limit,
        cost_bps,
        "continuous_mvo",
    )


def _continuous(
    instance, bits, min_weight, max_weight, sector_caps, previous_weights, turnover_limit, cost_bps, method
):
    import cvxpy as cp

    start = perf_counter()
    _validate(min_weight, max_weight, sector_caps, turnover_limit, cost_bps)
    prior, outside, has_previous = _previous(instance, previous_weights)
    if turnover_limit is not None and not has_previous:
        raise ValueError("A turnover limit requires previous holdings.")
    errors = instance.violations(bits) if bits is not None else []
    support = np.asarray(bits if bits is not None else np.ones(instance.n), float)
    if errors:
        return dict(
            method=method,
            status="infeasible_selection",
            weights=None,
            objective=None,
            seconds=perf_counter() - start,
            violations=errors,
        )
    w = cp.Variable(instance.n)
    constraints = [cp.sum(w) == 1, w >= min_weight * support, w <= max_weight * support]
    for s, c in (sector_caps or {}).items():
        ids = [i for i in range(instance.n) if instance.sectors[i] == s]
        if ids:
            constraints.append(cp.sum(w[ids]) <= c)
    traded = cp.norm1(w - prior) + outside if has_previous else 0
    if turnover_limit is not None:
        constraints.append(traded <= 2 * turnover_limit)
    objective = instance.risk_aversion * cp.quad_form(w, cp.psd_wrap(instance.covariance)) - instance.mu @ w
    objective += cost_bps / 10000 * traded
    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(solver="CLARABEL")
    if w.value is None:
        return dict(
            method=method,
            status=str(problem.status),
            weights=None,
            objective=None,
            seconds=perf_counter() - start,
            violations=["allocation constraints infeasible"],
        )
    weights = np.asarray(w.value).ravel()
    errors, turnover = _weight_violations(
        instance,
        weights,
        support,
        min_weight,
        max_weight,
        sector_caps,
        prior,
        outside,
        has_previous,
        turnover_limit,
    )
    weights[np.abs(weights) < 1e-9] = 0
    return dict(
        method=method,
        status=str(problem.status) if not errors else "invalid_solution",
        weights=weights.tolist() if not errors else None,
        objective=float(problem.value),
        seconds=perf_counter() - start,
        violations=errors,
        turnover=turnover,
        forced_sales=outside,
        transaction_cost=cost_bps / 10000 * 2 * turnover if has_previous else 0.0,
        count_constraints_applied=bits is not None,
    )


def joint_select_weights(
    instance,
    min_weight=0.05,
    max_weight=0.5,
    sector_caps=None,
    previous_weights=None,
    turnover_limit=None,
    cost_bps=10,
    time_limit=30,
):
    from pyscipopt import Model, quicksum

    start = perf_counter()
    _validate(min_weight, max_weight, sector_caps, turnover_limit, cost_bps)
    if min_weight <= 0:
        raise ValueError("Joint exact-K support requires positive min_weight.")
    prior, outside, has_previous = _previous(instance, previous_weights)
    if turnover_limit is not None and not has_previous:
        raise ValueError("A turnover limit requires previous holdings.")
    m = Model("joint")
    m.hideOutput()
    m.setRealParam("limits/time", float(time_limit))
    x = [m.addVar(vtype="B") for _ in range(instance.n)]
    w = [m.addVar(lb=0, ub=max_weight) for _ in range(instance.n)]
    m.addCons(quicksum(x) == instance.k)
    m.addCons(quicksum(w) == 1)
    for i in range(instance.n):
        m.addCons(w[i] >= min_weight * x[i])
        m.addCons(w[i] <= max_weight * x[i])
    for s in set(instance.sectors):
        ids = [i for i in range(instance.n) if instance.sectors[i] == s]
        m.addCons(quicksum(x[i] for i in ids) >= instance.sector_min.get(s, 0))
        m.addCons(quicksum(x[i] for i in ids) <= instance.sector_max.get(s, instance.n))
        if s in (sector_caps or {}):
            m.addCons(quicksum(w[i] for i in ids) <= sector_caps[s])
    traded = 0.0
    if has_previous:
        changes = [m.addVar(lb=0) for _ in range(instance.n)]
        for i in range(instance.n):
            m.addCons(changes[i] >= w[i] - float(prior[i]))
            m.addCons(changes[i] >= float(prior[i]) - w[i])
        traded = quicksum(changes) + outside
        if turnover_limit is not None:
            m.addCons(traded <= 2 * turnover_limit)
    t = m.addVar(lb=-m.infinity())
    obj = quicksum(
        instance.risk_aversion * float(instance.covariance[i, j]) * w[i] * w[j]
        for i in range(instance.n)
        for j in range(instance.n)
    )
    obj -= quicksum(float(instance.mu[i]) * w[i] for i in range(instance.n))
    obj += cost_bps / 10000 * traded
    m.addCons(t >= obj)
    m.setObjective(t)
    m.optimize()
    status = str(m.getStatus())
    if not m.getNSols():
        return dict(
            method="scip_joint",
            status=status,
            weights=None,
            bits=None,
            objective=None,
            seconds=perf_counter() - start,
            violations=[status],
            certified=status == "infeasible",
        )
    bits, weights = [int(m.getVal(v) > 0.5) for v in x], np.array([m.getVal(v) for v in w])
    errors, turnover = _weight_violations(
        instance,
        weights,
        np.array(bits),
        min_weight,
        max_weight,
        sector_caps,
        prior,
        outside,
        has_previous,
        turnover_limit,
    )
    errors += instance.violations(bits)
    value = float(instance.risk_aversion * weights @ instance.covariance @ weights - instance.mu @ weights)
    value += cost_bps / 10000 * 2 * turnover if has_previous else 0
    return dict(
        method="scip_joint",
        status=status if not errors else "invalid_solution",
        weights=weights.tolist() if not errors else None,
        bits=bits if not errors else None,
        objective=value,
        seconds=perf_counter() - start,
        violations=errors,
        certified=status == "optimal" and not errors,
        gap=float(m.getGap()),
        turnover=turnover,
    )


def repair_selection(instance, bits, max_candidates=200, **allocation_kwargs):
    """Bounded nearest-support search; never replaces or conceals the raw result."""
    start = perf_counter()
    raw = allocate(instance, bits, **allocation_kwargs)
    if raw["weights"] is not None:
        return dict(raw=raw, repaired=None, seconds=perf_counter() - start, candidates=0)
    # Enumerate bounded supports, prioritizing their overlap with the raw selection.
    order = sorted(range(instance.n), key=lambda i: (-int(bits[i]), -float(instance.mu[i]), i))
    best, count = None, 0
    for indices in combinations(order, instance.k):
        if count >= max_candidates:
            break
        x = [int(i in indices) for i in range(instance.n)]
        count += 1
        if instance.feasible(x):
            a = allocate(instance, x, **allocation_kwargs)
            if a["weights"] is not None and (best is None or a["objective"] < best["objective"]):
                best = dict(a, bits=x)
    return dict(raw=raw, repaired=best, seconds=perf_counter() - start, candidates=count)
