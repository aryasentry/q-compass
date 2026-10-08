from itertools import combinations
from math import comb
from time import perf_counter

import numpy as np


def _result(instance, method, start, bits=None, status="optimal", certified=False, **extra):
    return dict(
        method=method,
        status=status,
        bits=bits,
        objective=instance.objective(bits) if bits is not None else None,
        seconds=perf_counter() - start,
        certified=certified,
        **extra,
    )


def exact_select(instance, max_combinations=1_000_000):
    start = perf_counter()
    size = comb(instance.n, instance.k)
    if size > max_combinations:
        return _result(instance, "exact", start, status="budget_exceeded", candidates=size)
    best, value, evaluated = None, float("inf"), 0
    for indices in combinations(range(instance.n), instance.k):
        x = [int(i in indices) for i in range(instance.n)]
        if instance.feasible(x):
            evaluated += 1
            score = instance.objective(x)
            if score < value:
                best, value = x, score
    return _result(
        instance,
        "exact",
        start,
        best,
        status="optimal" if best else "infeasible",
        certified=True,
        evaluations=evaluated,
    )


def greedy_select(instance):
    start, evaluated = perf_counter(), 0
    x = np.zeros(instance.n, dtype=int)
    # Satisfy disjoint sector lower bounds first; leave capacity for every remaining lower bound.
    for s in sorted(instance.sector_min):
        for _ in range(instance.sector_min[s]):
            candidates = [i for i in range(instance.n) if not x[i] and instance.sectors[i] == s]
            values = []
            for i in candidates:
                z = x.copy()
                z[i] = 1
                values.append((instance.objective(z), i))
                evaluated += 1
            x[min(values)[1]] = 1
    while x.sum() < instance.k:
        values = []
        for i in range(instance.n):
            s = instance.sectors[i]
            count = sum(x[j] for j in range(instance.n) if instance.sectors[j] == s)
            if not x[i] and count < instance.sector_max.get(s, instance.n):
                z = x.copy()
                z[i] = 1
                values.append((instance.objective(z), i))
                evaluated += 1
        if not values:
            return _result(instance, "greedy_swaps", start, status="infeasible", evaluations=evaluated)
        x[min(values)[1]] = 1
    score = instance.objective(x)
    while True:
        best = None
        for i in np.flatnonzero(x):
            for j in np.flatnonzero(1 - x):
                z = x.copy()
                z[i] = 0
                z[j] = 1
                if instance.feasible(z):
                    value = instance.objective(z)
                    evaluated += 1
                    if value < score - 1e-12:
                        best, score = z, value
        if best is None:
            break
        x = best
    return _result(instance, "greedy_swaps", start, x.tolist(), status="heuristic", evaluations=evaluated)


def scip_select(instance, time_limit=30):
    from pyscipopt import Model, quicksum

    start = perf_counter()
    m = Model("subset")
    m.hideOutput()
    m.setRealParam("limits/time", float(time_limit))
    m.setIntParam("parallel/maxnthreads", 1)
    x = [m.addVar(vtype="B", name=f"x{i}") for i in range(instance.n)]
    m.addCons(quicksum(x) == instance.k)
    for s in sorted(set(instance.sectors)):
        count = quicksum(x[i] for i in range(instance.n) if instance.sectors[i] == s)
        m.addCons(count >= instance.sector_min.get(s, 0))
        m.addCons(count <= instance.sector_max.get(s, instance.n))
    t = m.addVar(lb=-m.infinity(), name="epigraph")
    obj = quicksum(
        instance.risk_aversion * float(instance.covariance[i, j]) * x[i] * x[j] / instance.k**2
        for i in range(instance.n)
        for j in range(instance.n)
    )
    obj -= quicksum(float(instance.mu[i]) * x[i] / instance.k for i in range(instance.n))
    m.addCons(t >= obj)
    m.setObjective(t)
    m.optimize()
    status = str(m.getStatus())
    bits = [int(m.getVal(v) > 0.5) for v in x] if m.getNSols() else None
    if bits is not None and not instance.feasible(bits):
        bits = None
        status = "invalid_solution"
    return _result(
        instance,
        "scip_subset",
        start,
        bits,
        status,
        certified=status in ("optimal", "infeasible"),
        gap=float(m.getGap()) if bits else None,
    )
