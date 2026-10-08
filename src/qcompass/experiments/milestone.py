"""Fail-closed evidence for the bounded Objectives 1 and 2 milestone."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import uuid

import numpy as np
import pandas as pd

from qcompass.data.prepare import aligned_window, build_instance
from qcompass.data.snapshots import load_snapshot
from qcompass.data.validation import DataQualityError, validate_prices
from qcompass.experiments.runner import RunConfig, read_result, run_experiment
from qcompass.portfolio.models import PortfolioInstance
from qcompass.quantum.solver import QuantumConfig


REQUIRED_METHODS = ("exact", "greedy_swaps", "qaoa-x-p1", "qaoa-x-p2")
OBJECTIVE_TOLERANCE = 1e-10
WEIGHT_TOLERANCE = 2e-5
SUCCESS_STATUS = {
    "exact": "optimal",
    "greedy_swaps": "heuristic",
    "qaoa-x-p1": "completed",
    "qaoa-x-p2": "completed",
}
STANDARD_QUANTUM_CONFIGS = {
    "qaoa-x-p1": QuantumConfig("qaoa-x-p1"),
    "qaoa-x-p2": QuantumConfig("qaoa-x-p2", depth=2),
}


class MilestoneFailure(RuntimeError):
    """A milestone package was written but one or more acceptance checks failed."""

    def __init__(self, message, package):
        super().__init__(message)
        self.package = Path(package)


def _check(checks, name, passed, detail):
    checks.append({"name": name, "passed": bool(passed), "detail": str(detail)})
    return bool(passed)


def _method_map(run):
    rows = run.get("results") if isinstance(run, dict) else None
    if not isinstance(rows, list):
        return {}, False
    mapped = {}
    unique = True
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("method"), str):
            unique = False
            continue
        if row["method"] in mapped:
            unique = False
        mapped[row["method"]] = row
    return mapped, unique


def _requested_quantum_configs(config):
    if config.quantum_configs is None:
        raise ValueError("Milestone settings must explicitly configure standard QAOA p1 and p2")
    parsed = [QuantumConfig(**value) for value in config.quantum_configs]
    return {value.name: asdict(value) for value in parsed}


def _validate_milestone_config(config):
    requested = _requested_quantum_configs(config)
    expected = {name: asdict(value) for name, value in STANDARD_QUANTUM_CONFIGS.items()}
    if config.include_adaptive or config.repair or config.ranker_path:
        raise ValueError("Milestone requires no adaptive controller, repair, or context ranker")
    if requested != expected:
        raise ValueError(
            "Milestone requires standard X-mixer p1/p2, mean objective, COBYLA, "
            "default penalty, no noise, and no warm start"
        )
    return requested


def _instances_match(left, right):
    if not isinstance(left, PortfolioInstance) or not isinstance(right, PortfolioInstance):
        return False
    return bool(
        left.dataset_id == right.dataset_id
        and left.as_of == right.as_of
        and left.symbols == right.symbols
        and left.sectors == right.sectors
        and left.k == right.k
        and left.sector_min == right.sector_min
        and left.sector_max == right.sector_max
        and left.risk_aversion == right.risk_aversion
        and np.array_equal(left.mu, right.mu)
        and np.array_equal(left.covariance, right.covariance)
    )


def _config_matches_instance(config, instance):
    symbols_match = config.symbols is None or config.symbols == instance.symbols
    expected_sectors = {sector: config.sector_limit for sector in set(instance.sectors)}
    return bool(
        config.dataset_id == instance.dataset_id
        and config.as_of == instance.as_of
        and config.n == instance.n
        and config.k == instance.k
        and symbols_match
        and instance.sector_min == {}
        and instance.sector_max == expected_sectors
        and config.risk_aversion == instance.risk_aversion
    )


def _valid_bits(bits, instance):
    if not isinstance(bits, list) or len(bits) != instance.n:
        return False, {"binary": False, "cardinality": False, "sector_counts": {}}
    binary = all(type(value) is int and value in (0, 1) for value in bits)
    if not binary:
        return False, {
            "binary": False,
            "cardinality": False,
            "selected_count": None,
            "required_count": instance.k,
            "sector_counts": {},
            "sector_bounds": False,
        }
    cardinality = sum(bits) == instance.k
    sector_counts = {
        sector: sum(bits[i] for i, value in enumerate(instance.sectors) if value == sector)
        for sector in sorted(set(instance.sectors))
    }
    sector_bounds = binary and all(
        instance.sector_min.get(sector, 0)
        <= sector_counts[sector]
        <= instance.sector_max.get(sector, instance.n)
        for sector in sector_counts
    )
    return binary and cardinality and sector_bounds, {
        "binary": binary,
        "cardinality": cardinality,
        "selected_count": sum(bits) if binary else None,
        "required_count": instance.k,
        "sector_counts": sector_counts,
        "sector_bounds": sector_bounds,
    }


def _valid_weights(row, bits, instance, config):
    allocation = row.get("allocation")
    weights = allocation.get("weights") if isinstance(allocation, dict) else None
    details = {
        "full_investment": False,
        "position_bounds": False,
        "sector_weight_caps": False,
        "finite": False,
    }
    if not isinstance(weights, list) or len(weights) != instance.n:
        return False, details
    try:
        values = np.asarray(weights, dtype=float)
    except (TypeError, ValueError):
        return False, details
    finite = bool(np.isfinite(values).all())
    details["finite"] = finite
    if (
        not finite
        or not isinstance(bits, list)
        or len(bits) != instance.n
        or not all(type(value) is int and value in (0, 1) for value in bits)
    ):
        return False, details
    support = np.asarray(bits, dtype=float)
    full = abs(float(values.sum()) - 1.0) <= WEIGHT_TOLERANCE
    positions = bool(
        np.all(values >= config.min_weight * support - WEIGHT_TOLERANCE)
        and np.all(values <= config.max_weight * support + WEIGHT_TOLERANCE)
    )
    sector_weights = {
        sector: float(sum(values[i] for i, value in enumerate(instance.sectors) if value == sector))
        for sector in sorted(set(instance.sectors))
    }
    sectors = all(value <= config.sector_weight_cap + WEIGHT_TOLERANCE for value in sector_weights.values())
    details.update(
        full_investment=full,
        total_weight=float(values.sum()),
        position_bounds=positions,
        sector_weight_caps=sectors,
        sector_weights=sector_weights,
    )
    return finite and full and positions and sectors, details


def _valid_counts(row, config):
    counts = row.get("counts")
    qubits = row.get("num_qubits")
    metadata = row.get("metadata")
    final_shots = metadata.get("final_sampling_shots") if isinstance(metadata, dict) else None
    if not isinstance(counts, dict) or not counts or type(qubits) is not int or qubits <= 0:
        return False, "counts, register width, and final sampling metadata are required"
    valid_entries = all(
        isinstance(key, str)
        and len(key.replace(" ", "")) == qubits
        and set(key.replace(" ", "")) <= {"0", "1"}
        and type(value) is int
        and value >= 0
        for key, value in counts.items()
    )
    observed = sum(counts.values()) if valid_entries else None
    passed = valid_entries and final_shots == config.shots and observed == config.shots
    return passed, f"valid_entries={valid_entries}, observed={observed}, expected={config.shots}"


def _assess_run(run, label, checks):
    rows, unique = _method_map(run)
    _check(checks, f"{label}.method_names_unique", unique, "method names must be present and unique")
    missing = [name for name in REQUIRED_METHODS if name not in rows]
    _check(checks, f"{label}.required_methods", not missing, f"missing={missing}")
    _check(checks, f"{label}.not_cancelled", run.get("cancelled") is False, run.get("cancelled"))
    try:
        config = RunConfig(**run["config"])
        instance = PortfolioInstance.from_dict(run["instance"])
        setup_ok = True
    except (KeyError, TypeError, ValueError) as exc:
        _check(checks, f"{label}.stored_problem", False, f"{type(exc).__name__}: {exc}")
        return rows, {}, None, None
    _check(checks, f"{label}.stored_problem", setup_ok, "configuration and instance decoded")
    _check(
        checks,
        f"{label}.config_instance_consistency",
        _config_matches_instance(config, instance),
        "dataset, date, N, K, symbols, sector bounds, and risk aversion must agree",
    )
    try:
        requested_quantum = _validate_milestone_config(config)
        milestone_settings_ok = True
        settings_detail = "standard baseline settings"
    except (TypeError, ValueError) as exc:
        requested_quantum = {}
        milestone_settings_ok = False
        settings_detail = f"{type(exc).__name__}: {exc}"
    _check(checks, f"{label}.standard_milestone_settings", milestone_settings_ok, settings_detail)

    measured = {}
    exact = rows.get("exact", {})
    exact_objective = exact.get("objective")
    exact_certified = exact.get("certified") is True and isinstance(exact_objective, (int, float))
    exact_certified = exact_certified and isfinite(float(exact_objective))
    _check(checks, f"{label}.exact.certified", exact_certified, exact.get("certified"))

    for method in REQUIRED_METHODS:
        row = rows.get(method)
        if not isinstance(row, dict):
            continue
        status_ok = row.get("status") == SUCCESS_STATUS[method]
        _check(checks, f"{label}.{method}.status", status_ok, row.get("status"))
        objective = row.get("objective")
        objective_ok = isinstance(objective, (int, float)) and isfinite(float(objective))
        _check(checks, f"{label}.{method}.objective_finite", objective_ok, objective)
        bits = row.get("bits")
        selection_ok, selection_details = _valid_bits(bits, instance)
        _check(checks, f"{label}.{method}.selection_feasibility", selection_ok, selection_details)
        objective_recomputed = False
        recomputed = None
        if selection_ok and objective_ok:
            recomputed = instance.objective(bits)
            objective_recomputed = abs(float(objective) - recomputed) <= OBJECTIVE_TOLERANCE
        _check(
            checks,
            f"{label}.{method}.objective_recomputed",
            objective_recomputed,
            f"stored={objective}, recomputed={recomputed}",
        )
        not_below_exact = (
            exact_certified
            and objective_ok
            and float(objective) >= float(exact_objective) - OBJECTIVE_TOLERANCE
        )
        _check(
            checks,
            f"{label}.{method}.not_below_certified_exact",
            not_below_exact,
            f"objective={objective}, exact={exact_objective}",
        )
        allocation_ok, allocation_details = _valid_weights(row, bits, instance, config)
        _check(checks, f"{label}.{method}.allocation_feasibility", allocation_ok, allocation_details)
        if method.startswith("qaoa-"):
            row_config = row.get("config")
            try:
                recorded_config = asdict(QuantumConfig(**row_config))
            except (TypeError, ValueError):
                recorded_config = None
            standard_config = asdict(STANDARD_QUANTUM_CONFIGS[method])
            _check(
                checks,
                f"{label}.{method}.standard_baseline",
                recorded_config == standard_config,
                f"recorded={recorded_config}",
            )
            _check(
                checks,
                f"{label}.{method}.config_matches_request",
                recorded_config is not None and recorded_config == requested_quantum.get(method),
                "recorded solver configuration must equal requested configuration",
            )
            evaluations = row.get("evaluations")
            shots_used = row.get("shots_used")
            budget_ok = (
                type(evaluations) is int
                and 0 <= evaluations <= config.batches - 1
                and type(shots_used) is int
                and shots_used == (evaluations + 1) * config.shots
                and shots_used <= config.batches * config.shots
            )
            _check(
                checks,
                f"{label}.{method}.budget",
                budget_ok,
                f"evaluations={evaluations}, shots_used={shots_used}",
            )
            counts_ok, counts_detail = _valid_counts(row, config)
            _check(checks, f"{label}.{method}.counts", counts_ok, counts_detail)
        measured[method] = {
            "method": method,
            "category": "exact" if method == "exact" else "heuristic" if method == "greedy_swaps" else "quantum",
            "status": row.get("status"),
            "objective": objective,
            "bits": bits,
            "evaluations": row.get("evaluations"),
            "shots_used": row.get("shots_used"),
            "selection_feasibility": {"passed": selection_ok, **selection_details},
            "allocation_feasibility": {"passed": allocation_ok, **allocation_details},
            "weights": (row.get("allocation") or {}).get("weights"),
        }
    return rows, measured, config, instance


def assess_runs(first, second, trusted_config=None, trusted_instance=None):
    """Assess two checksum-verified result payloads without trusting stored flags."""
    checks = []
    left, methods, first_config, first_instance = _assess_run(first, "run_a", checks)
    right, _, second_config, second_instance = _assess_run(second, "run_b", checks)
    _check(
        checks,
        "reproducibility.instance",
        _instances_match(first_instance, second_instance),
        "stored dataset, date, symbols, K, sector bounds, risk aversion, mu, and covariance must match",
    )
    if trusted_config is not None:
        expected_config = (
            trusted_config
            if isinstance(trusted_config, RunConfig)
            else RunConfig(**trusted_config)
        )
        for label, stored in (("run_a", first_config), ("run_b", second_config)):
            _check(
                checks,
                f"{label}.trusted_config",
                isinstance(stored, RunConfig) and stored.model_dump() == expected_config.model_dump(),
                "saved configuration must equal verified preflight configuration",
            )
    if trusted_instance is not None:
        expected_instance = (
            trusted_instance
            if isinstance(trusted_instance, PortfolioInstance)
            else PortfolioInstance.from_dict(trusted_instance)
        )
        for label, stored in (("run_a", first_instance), ("run_b", second_instance)):
            _check(
                checks,
                f"{label}.trusted_instance",
                _instances_match(stored, expected_instance),
                "saved instance must equal the verified preflight instance",
            )
    _check(
        checks,
        "reproducibility.dataset_fingerprint",
        bool(first.get("dataset_fingerprint"))
        and first.get("dataset_fingerprint") == second.get("dataset_fingerprint"),
        "dataset fingerprints must match",
    )
    left_source = (first.get("software") or {}).get("source_fingerprint")
    right_source = (second.get("software") or {}).get("source_fingerprint")
    _check(
        checks,
        "reproducibility.source_fingerprint",
        bool(left_source) and left_source == right_source,
        "source fingerprints must match",
    )
    _check(
        checks,
        "reproducibility.settings",
        isinstance(first.get("config"), dict) and first.get("config") == second.get("config"),
        "stored configurations must match exactly",
    )
    _check(
        checks,
        "reproducibility.method_set",
        set(left) == set(right),
        f"run_a={sorted(left)}, run_b={sorted(right)}",
    )
    for method in sorted(set(left) | set(right)):
        a, b = left.get(method), right.get(method)
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        for field in ("method", "status", "bits", "counts", "evaluations", "shots_used"):
            _check(
                checks,
                f"reproducibility.{field}.{method}",
                a.get(field) == b.get(field),
                "exact comparison",
            )
        a_objective, b_objective = a.get("objective"), b.get("objective")
        objective_match = (
            isinstance(a_objective, (int, float))
            and isinstance(b_objective, (int, float))
            and isfinite(float(a_objective))
            and isfinite(float(b_objective))
            and abs(float(a_objective) - float(b_objective)) <= OBJECTIVE_TOLERANCE
        )
        _check(
            checks,
            f"reproducibility.objective.{method}",
            objective_match,
            f"absolute_tolerance={OBJECTIVE_TOLERANCE}",
        )
        a_weights = (a.get("allocation") or {}).get("weights")
        b_weights = (b.get("allocation") or {}).get("weights")
        weights_match = False
        if isinstance(a_weights, list) and isinstance(b_weights, list) and len(a_weights) == len(b_weights):
            try:
                weights_match = bool(
                    np.isfinite(np.asarray(a_weights, float)).all()
                    and np.isfinite(np.asarray(b_weights, float)).all()
                    and np.allclose(a_weights, b_weights, atol=WEIGHT_TOLERANCE, rtol=0)
                )
            except (TypeError, ValueError):
                weights_match = False
        _check(
            checks,
            f"reproducibility.weights.{method}",
            weights_match,
            f"absolute_tolerance={WEIGHT_TOLERANCE}",
        )
    return {
        "passed": bool(checks) and all(check["passed"] for check in checks),
        "tolerances": {
            "objective_absolute": OBJECTIVE_TOLERANCE,
            "weight_absolute": WEIGHT_TOLERANCE,
        },
        "checks": checks,
        "methods": list(methods.values()),
    }


def _new_package(root):
    base = root / "artifacts/milestones"
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package = base / f"objectives-1-2-{stamp}-{uuid.uuid4().hex[:10]}"
    package.mkdir(exist_ok=False)
    return package


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def _preflight(settings_path, root):
    raw = json.loads(settings_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Milestone settings must be a JSON object")
    if not raw.get("dataset_id") or not raw.get("as_of"):
        raise ValueError("Milestone settings must pin dataset_id and as_of")
    config = RunConfig(**raw)
    _validate_milestone_config(config)
    manifest, members, prices = load_snapshot(config.dataset_id, root, verify=True)
    price_audit = validate_prices(prices)
    instance, preparation = build_instance(
        config.dataset_id,
        config.n,
        config.k,
        config.sector_limit,
        config.risk_aversion,
        config.as_of,
        root,
        config.symbols,
    )
    window = aligned_window(prices, instance.symbols, manifest["sessions"], config.as_of)
    returns = window.pct_change(fill_method=None).iloc[1:]
    if len(returns) != preparation["return_observations"]:
        raise DataQualityError("Exported return window disagrees with prepared instance")

    processed = (root / manifest.get("processed_directory", f"data/processed/{config.dataset_id}")).resolve()
    quarantine_path = processed / "quarantined.parquet"
    quarantined = pd.read_parquet(quarantine_path) if quarantine_path.is_file() else pd.DataFrame()
    declared_quarantine = int(manifest.get("quarantined_row_count", 0))
    if len(quarantined) != declared_quarantine:
        raise DataQualityError("Quarantine file count disagrees with verified manifest")

    crosscheck = manifest.get("crosscheck") or {}
    provenance = {
        "source": {
            "universe": manifest.get("universe"),
            "membership_source": manifest.get("membership_source"),
            "price_source": manifest.get("price_source"),
            "source_record_count": len(manifest.get("source_records", [])),
            "membership_mode": manifest.get("membership_mode"),
            "historical_membership_verified": bool(manifest.get("historical_membership_verified")),
            "corporate_actions_independently_verified": bool(
                manifest.get("corporate_actions_independently_verified")
            ),
        },
        "coverage": {
            "constituents": int(len(members)),
            "retained_rows": int(len(prices)),
            "symbols_with_retained_rows": int(prices.symbol.nunique()),
            "first_date": str(pd.to_datetime(prices.date).min().date()),
            "last_date": str(pd.to_datetime(prices.date).max().date()),
            "structural_validation": price_audit,
        },
        "eligibility": {
            "decision_date": preparation["decision_date"],
            "eligible_count": int(preparation["eligible_count"]),
            "excluded_count": len(preparation["excluded"]),
            "excluded": preparation["excluded"],
            "selected": preparation["selected"],
            "selection_policy": preparation["policy"],
        },
        "quarantine": {
            "row_count": int(len(quarantined)),
            "symbols": sorted(set(quarantined.symbol.astype(str))) if not quarantined.empty else [],
            "policy": manifest.get("processing_policy"),
        },
        "crosscheck": {
            "status": crosscheck.get("status"),
            "date": crosscheck.get("date"),
            "matched": len(crosscheck.get("matches", [])),
            "mismatched": len(crosscheck.get("mismatches", [])),
            "source_url": crosscheck.get("source_url"),
        },
    }
    return config, manifest, instance, preparation, window, returns, provenance


def _export_derived(package, config, instance, window, returns):
    window.rename_axis("date").reset_index().to_csv(package / "selected_adjusted_prices.csv", index=False)
    returns.rename_axis("date").reset_index().to_csv(package / "daily_returns.csv", index=False)
    pd.DataFrame(
        {"symbol": instance.symbols, "annualized_expected_return": instance.mu.tolist()}
    ).to_csv(package / "annualized_expected_returns.csv", index=False)
    pd.DataFrame(instance.covariance, index=instance.symbols, columns=instance.symbols).rename_axis(
        "symbol"
    ).to_csv(package / "covariance.csv")
    constraints = {
        "observation_label": (
            "Derived from checksum-verified authentic observations; no synthetic, repaired, "
            "or interpolated prices"
        ),
        "selection_objective": "risk_aversion * x^T covariance x / K^2 - mu^T x / K",
        "selection": {
            "candidate_count": instance.n,
            "cardinality_K": instance.k,
            "binary": True,
            "sector_count_min": instance.sector_min,
            "sector_count_max": instance.sector_max,
            "equal_weight_proxy": True,
        },
        "allocation": {
            "classical_post_selection_stage": True,
            "fully_invested": True,
            "min_weight": config.min_weight,
            "max_weight": config.max_weight,
            "sector_weight_cap": config.sector_weight_cap,
        },
    }
    _write_json(package / "constraints.json", constraints)
    return constraints


def _comparison_rows(first, second, assessment):
    left, _ = _method_map(first)
    right, _ = _method_map(second)
    method_assessment = {row["method"]: row for row in assessment["methods"]}
    rows = []
    for method in sorted(set(left) | set(right)):
        a, b = left.get(method, {}), right.get(method, {})
        gate = method_assessment.get(method, {})
        rows.append(
            {
                "method": method,
                "category": gate.get(
                    "category",
                    "classical_reference" if method == "scip_subset" else "additional",
                ),
                "run_a_status": a.get("status"),
                "run_b_status": b.get("status"),
                "run_a_objective": a.get("objective"),
                "run_b_objective": b.get("objective"),
                "run_a_bits": json.dumps(a.get("bits")),
                "run_b_bits": json.dumps(b.get("bits")),
                "run_a_weights": json.dumps((a.get("allocation") or {}).get("weights")),
                "run_b_weights": json.dumps((b.get("allocation") or {}).get("weights")),
                "run_a_evaluations": a.get("evaluations"),
                "run_b_evaluations": b.get("evaluations"),
                "run_a_shots_used": a.get("shots_used"),
                "run_b_shots_used": b.get("shots_used"),
                "selection_feasible_rechecked": (gate.get("selection_feasibility") or {}).get("passed"),
                "allocation_feasible_rechecked": (gate.get("allocation_feasibility") or {}).get("passed"),
            }
        )
    return rows


def _write_report(package, evidence, constraints):
    passed = evidence.get("passed", False)
    lines = [
        "# Q-Compass Objectives 1 and 2 evidence",
        "",
        f"**Status: {'PASS' if passed else 'FAIL'}**",
        "",
        (
            "This package evaluates a reproducible authentic-data pipeline and exact, heuristic, "
            "and standard simulated QAOA baselines. It does not claim quantum optimality or advantage."
        ),
        "",
    ]
    failure = evidence.get("failure")
    if failure:
        lines += [
            "## Failure",
            "",
            f"- Stage: `{failure.get('stage')}`",
            f"- Error: {failure.get('error')}",
            "",
        ]
    runs = evidence.get("runs", [])
    if runs:
        lines += ["## Saved runs", ""]
        for record in runs:
            lines.append(
                f"- [{record['run_id']}](../../runs/{record['run_id']}/result.json) — `{record['path']}`"
            )
        lines.append("")
    provenance = evidence.get("provenance")
    if provenance:
        source, coverage = provenance["source"], provenance["coverage"]
        eligibility, quarantine = provenance["eligibility"], provenance["quarantine"]
        crosscheck = provenance["crosscheck"]
        lines += [
            "## Provenance and coverage",
            "",
            f"- Membership source: {source['membership_source']}",
            f"- Price source: {source['price_source']}",
            f"- Retained observations: {coverage['retained_rows']:,} across "
            f"{coverage['symbols_with_retained_rows']} symbols, {coverage['first_date']} to "
            f"{coverage['last_date']}",
            f"- Decision-date eligibility: {eligibility['eligible_count']} eligible; "
            f"{eligibility['excluded_count']} excluded; selected {', '.join(eligibility['selected'])}",
            f"- Quarantine: {quarantine['row_count']} original dated rows excluded, never filled",
            f"- Latest-session cross-check: {crosscheck['matched']} matched, "
            f"{crosscheck['mismatched']} mismatched on {crosscheck['date']}",
            "- The current 50-stock membership snapshot is not historical membership evidence.",
            "- Provider-adjusted histories are not independently certified for every corporate action.",
            "",
            "### Eligibility exclusions",
            "",
        ]
        lines += [f"- {row['symbol']}: {row['reason']}" for row in eligibility["excluded"]] or ["- None"]
        lines.append("")
    if constraints:
        lines += [
            "## Objective and constraint responsibilities",
            "",
            f"- Binary selection objective: `{constraints['selection_objective']}`.",
            f"- Selection enforces exactly K={constraints['selection']['cardinality_K']} and sector counts.",
            "- Binary scores use an equal-weight selection proxy.",
            "- A later classical allocation stage enforces full investment, position bounds, and sector caps.",
            "",
        ]
    methods = evidence.get("methods", [])
    if methods:
        lines += [
            "## Required measured methods (run A)",
            "",
            "| Method | Type | Status | Objective | Selection | Allocation | Evaluations | Shots |",
            "|---|---|---|---:|---|---|---:|---:|",
        ]
        for row in methods:
            lines.append(
                f"| {row['method']} | {row['category']} | {row['status']} | {row['objective']} | "
                f"{'PASS' if row['selection_feasibility']['passed'] else 'FAIL'} | "
                f"{'PASS' if row['allocation_feasibility']['passed'] else 'FAIL'} | "
                f"{row.get('evaluations')} | {row.get('shots_used')} |"
            )
        lines.append("")
    checks = evidence.get("checks", [])
    if checks:
        lines += ["## Acceptance and reproducibility checks", ""]
        lines += [
            f"- {'PASS' if check['passed'] else 'FAIL'} — `{check['name']}`: {check['detail']}"
            for check in checks
        ]
        lines.append("")
    limitations = evidence.get("limitations", [])
    lines += ["## Limitations", ""]
    lines += [f"- {value}" for value in limitations] or ["- Milestone failed during preflight; no result claim."]
    lines += [
        "",
        "Runtime is deliberately excluded from equality checks. Floating objectives use absolute "
        f"tolerance {OBJECTIVE_TOLERANCE}; weights use {WEIGHT_TOLERANCE}.",
    ]
    (package / "report.md").write_text("\n".join(lines) + "\n")


def _failure_evidence(package, settings_path, stage, exc, runs=None):
    evidence = {
        "schema_version": 1,
        "kind": "objectives_1_2_milestone",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "passed": False,
        "settings_path": str(settings_path),
        "package_path": str(package),
        "failure": {"stage": stage, "error": f"{type(exc).__name__}: {exc}"},
        "runs": list(runs or []),
        "checks": [],
        "limitations": [],
    }
    _write_json(package / "evidence.json", evidence)
    _write_report(package, evidence, None)
    return evidence


def run_milestone(settings_path, root=None, progress=print):
    """Preflight authentic data, run twice sequentially, and write fail-closed evidence."""
    root = Path(root or Path.cwd()).resolve()
    settings_path = Path(settings_path)
    package = _new_package(root)
    stage = "preflight"
    known_runs = []
    try:
        config, manifest, instance, preparation, window, returns, provenance = _preflight(
            settings_path, root
        )
        constraints = _export_derived(package, config, instance, window, returns)
        progress(f"Milestone package: {package}")
        stage = "run_a"
        first, first_path = run_experiment(config, root=root, progress=progress)
        known_runs.append({"run_id": first["run_id"], "path": str(first_path)})
        stage = "run_b"
        second, second_path = run_experiment(config, root=root, progress=progress)
        known_runs.append({"run_id": second["run_id"], "path": str(second_path)})
        stage = "readback"
        first = read_result(first_path)
        second = read_result(second_path)
        after_manifest, _, _ = load_snapshot(config.dataset_id, root, verify=True)
        assessment = assess_runs(
            first,
            second,
            trusted_config=config,
            trusted_instance=instance,
        )
        source_files_unchanged = (
            after_manifest.get("fingerprint") == manifest.get("fingerprint")
            and after_manifest.get("files") == manifest.get("files")
        )
        _check(
            assessment["checks"],
            "dataset.source_files_unchanged",
            source_files_unchanged,
            "snapshot reload and manifest-bound source hashes verified after both runs",
        )
        assessment["passed"] = all(check["passed"] for check in assessment["checks"])
        assessment.update(
            schema_version=1,
            kind="objectives_1_2_milestone",
            created_at=datetime.now(timezone.utc).isoformat(),
            status="passed" if assessment["passed"] else "failed",
            settings_path=str(settings_path),
            package_path=str(package),
            settings=config.model_dump(),
            runs=known_runs,
            dataset_integrity={
                "dataset_id": config.dataset_id,
                "fingerprint": manifest["fingerprint"],
                "source_files_unchanged": source_files_unchanged,
            },
            provenance=provenance,
            derived_data={
                "observation_label": constraints["observation_label"],
                "estimation_start": preparation["estimation_start"],
                "estimation_end": preparation["estimation_end"],
                "return_observations": preparation["return_observations"],
                "files": [
                    "selected_adjusted_prices.csv",
                    "daily_returns.csv",
                    "annualized_expected_returns.csv",
                    "covariance.csv",
                    "constraints.json",
                ],
            },
            limitations=list(dict.fromkeys(first.get("limitations", []) + second.get("limitations", []))),
        )
        comparison = _comparison_rows(first, second, assessment)
        _write_json(package / "evidence.json", assessment)
        pd.DataFrame(comparison).to_csv(package / "comparison.csv", index=False)
        _write_report(package, assessment, constraints)
        if not assessment["passed"]:
            raise MilestoneFailure("Milestone acceptance checks failed", package)
        return assessment, package
    except MilestoneFailure:
        raise
    except Exception as exc:
        _failure_evidence(package, settings_path, stage, exc, known_runs)
        raise MilestoneFailure(f"Milestone failed during {stage}: {exc}", package) from exc
