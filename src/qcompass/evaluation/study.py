"""Bridge real-data decisions to the tested execution engine."""

from datetime import datetime, timezone
from time import perf_counter
import uuid

from qcompass.classical.solvers import exact_select, greedy_select
from qcompass.classical.weights import allocate
from qcompass.adaptive.controller import adaptive_solve
from qcompass.data.prepare import build_instance
from qcompass.data.snapshots import load_snapshot
from qcompass.evaluation.backtest import monthly_schedule, run_backtest
from qcompass.evaluation.gates import strict_backtest_gate
from qcompass.experiments.runner import RunConfig, save_result, software_record
from qcompass.paths import project_root


def balance_roundoff(weights):
    """Account explicitly for continuous-solver numerical roundoff, not rule repair."""
    weights = dict(weights)
    delta = 1.0 - sum(weights.values())
    if not weights or abs(delta) > 2e-5:
        raise ValueError("Allocation sum differs materially from one")
    symbol = min(weights, key=weights.get) if delta > 0 else max(weights, key=weights.get)
    weights[symbol] += delta
    if weights[symbol] < 0:
        raise ValueError("Roundoff balancing would create a short position")
    return weights, {"symbol": symbol, "delta": delta, "reason": "continuous solver numerical tolerance"}


def validate_study_config(dataset_id, n, k, batches, shots, seed):
    return RunConfig(dataset_id=dataset_id, n=n, k=k, batches=batches, shots=shots, seed=seed)


def run_study(
    dataset_id,
    start,
    end,
    method="exact",
    mode="strict_historical",
    n=8,
    k=4,
    batches=24,
    shots=256,
    seed=42,
    root=None,
    progress=print,
):
    root = root or project_root()
    validate_study_config(dataset_id, n, k, batches, shots, seed)
    manifest, _, prices = load_snapshot(dataset_id, root)
    if start < manifest["first_date"] or end > manifest["last_date"]:
        raise ValueError("Requested study interval exceeds dataset coverage")
    if mode == "strict_historical":
        strict_backtest_gate(manifest)
        # The current importer has no independently verified historical member ledger.
        # Do not turn a metadata flag into a joint historical selection pipeline.
        raise ValueError(
            "Strict eligibility passed, but point-in-time candidate construction must be supplied before strategy evaluation"
        )
    if mode != "fixed_universe":
        raise ValueError("Explicit historical or fixed-universe mode required")
    if method not in {"exact", "greedy", "adaptive"}:
        raise ValueError("Supported methods: exact, greedy, adaptive")
    started = perf_counter()
    schedule = monthly_schedule(manifest["sessions"], start, end)
    if not schedule:
        raise ValueError("No completed monthly decision and following execution inside requested interval")
    decisions, evidence = [], []
    for index, step in enumerate(schedule):
        date = step["decision_date"]
        decision_seed = (seed + index * 1009) % (2**31 - 1)
        progress(f"Preparing {date}; execution will be {step['execution_date']}")
        instance, audit = build_instance(dataset_id, n, k, as_of=date, root=root)
        if method == "exact":
            selected = exact_select(instance)
        elif method == "greedy":
            selected = greedy_select(instance)
        else:
            selected = adaptive_solve(
                instance,
                evaluations=batches - 3,
                pilot_evaluations=min(6, (batches - 3) // 3),
                shots=shots,
                seed=decision_seed,
                max_seconds=180,
            )
        if selected.get("bits") is None:
            raise ValueError(f"No feasible {method} selection on {date}; no substitute method used")
        allocation = allocate(instance, selected["bits"], sector_caps={s: 0.5 for s in set(instance.sectors)})
        if allocation.get("weights") is None:
            raise ValueError(f"No feasible investment weights on {date}")
        weights = {s: float(w) for s, w in zip(instance.symbols, allocation["weights"]) if w > 0}
        weights, roundoff = balance_roundoff(weights)
        allocation["roundoff_balance_adjustment"] = roundoff
        decisions.append({**step, "weights": weights, "eligible_symbols": instance.symbols})
        evidence.append(
            {
                "instance": instance.to_dict(),
                "decision_seed": decision_seed,
                "preparation": audit,
                "selection": selected,
                "allocation": allocation,
            }
        )
    wide = prices.pivot(index="date", columns="symbol", values="adj_close")
    sessions = [d for d in manifest["sessions"] if schedule[0]["decision_date"] <= d <= end]
    wide = wide.reindex(sessions)  # missing values remain missing and block held-asset valuation
    costs = {
        str(bps): run_backtest(wide, decisions, cost_bps=bps, mode="fixed_universe") for bps in [0, 10, 25]
    }
    result = {
        "schema_version": 1,
        "run_id": uuid.uuid4().hex,
        "kind": "fixed_universe_study",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_fingerprint": manifest["fingerprint"],
        "config": {
            "dataset_id": dataset_id,
            "start": start,
            "end": end,
            "method": method,
            "n": n,
            "k": k,
            "batches": batches,
            "shots": shots,
            "seed": seed,
            "mode": mode,
        },
        "decisions": decisions,
        "decision_evidence": evidence,
        "cost_sensitivity": costs,
        "software": software_record(root),
        "elapsed_seconds": perf_counter() - started,
        "limitations": [
            "Current constituent universe, not a bias-free historical NIFTY backtest",
            "Candidate availability changes with validated history; not a historical index reconstruction",
            "Turnover is measured; no turnover limit or prior-weight transaction-cost term is imposed in this study bridge",
            "All cost scenarios replay the same gross target decisions; no cost-specific retuning",
        ],
    }
    path = save_result(result, root)
    for bps, output in costs.items():
        import pandas as pd

        pd.DataFrame({"equity": output["equity"], "return": output["returns"]}).to_parquet(
            path.parent / f"equity-{bps}bps.parquet"
        )
    return result, path
