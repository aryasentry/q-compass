"""Reproducible real-data comparisons; optimization is not a backtest."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter
import uuid

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qcompass.adaptive.controller import adaptive_solve, TemporalRanker
from qcompass.classical.solvers import exact_select, greedy_select, scip_select
from qcompass.classical.weights import allocate, continuous_mvo, joint_select_weights
from qcompass.data.prepare import build_instance, validated_date
from qcompass.data.snapshots import file_hash, load_snapshot
from qcompass.paths import project_root
from qcompass.quantum.solver import QuantumConfig, solve_qaoa


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    batch_id: str | None = None
    n: int = Field(default=8, ge=4, le=20)
    k: int = Field(default=4, ge=1, le=20)
    sector_limit: int = Field(default=1, ge=1, le=20)
    risk_aversion: float = Field(default=1.0, ge=0, le=100)
    min_weight: float = Field(default=0.05, gt=0, le=1)
    max_weight: float = Field(default=0.5, gt=0, le=1)
    sector_weight_cap: float = Field(default=0.5, gt=0, le=1)
    batches: int = Field(default=48, ge=12, le=256)
    shots: int = Field(default=512, ge=64, le=4096)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    max_seconds: float = Field(default=180, ge=5, le=600)
    as_of: str | None = None
    symbols: list[str] | None = None
    extra_baselines: bool = True
    repair: bool = False
    include_adaptive: bool = True
    quantum_configs: list[dict] | None = None
    ranker_path: str | None = None

    @field_validator("as_of")
    @classmethod
    def valid_decision_date(cls, value):
        if value is not None:
            validated_date(value, "Decision date")
        return value

    @model_validator(mode="after")
    def valid_weights(self):
        if self.k > self.n or self.k * self.min_weight > 1 or self.k * self.max_weight < 1:
            raise ValueError("K and position bounds cannot form a fully invested portfolio")
        if self.min_weight > self.max_weight:
            raise ValueError("Minimum weight exceeds maximum")
        if not self.include_adaptive and self.ranker_path:
            raise ValueError("ranker_path requires include_adaptive=true")
        if self.quantum_configs is not None:
            if not 2 <= len(self.quantum_configs) <= 4:
                raise ValueError("Choose a small library of two to four quantum configurations")
            parsed = [QuantumConfig(**c) for c in self.quantum_configs]
            if len({c.name for c in parsed}) != len(parsed):
                raise ValueError("Quantum configuration names must be unique")
        return self


def software_record(root):
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except subprocess.CalledProcessError:
        revision = "uncommitted-initial-project"
    files = [p for folder in (root / "src", root / "app") for p in folder.rglob("*.py")]
    files += [root / "pyproject.toml", root / "uv.lock"]
    hashes = {str(p.relative_to(root)): file_hash(p) for p in sorted(files) if p.is_file()}
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: version(name)
            for name in [
                "qiskit",
                "qiskit-aer",
                "qiskit-optimization",
                "numpy",
                "pandas",
                "scipy",
                "cvxpy",
                "pyscipopt",
                "scikit-learn",
                "yfinance",
            ]
        },
        "revision": revision,
        "source_files": hashes,
        "source_fingerprint": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
    }


def save_result(result, root=None):
    root = root or project_root()
    payload = json.dumps(result, indent=2, allow_nan=False)
    run_id = result["run_id"]
    if Path(run_id).name != run_id:
        raise ValueError("Invalid run identifier")
    folder = root / "artifacts/runs" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "result.json"
    path.write_text(payload)
    (folder / "result.sha256").write_text(file_hash(path))
    rows = comparison_table(result)
    if not rows.empty:
        rows.to_parquet(folder / "comparison.parquet", index=False)
        rows.to_csv(folder / "comparison.csv", index=False)
    return path


def read_result(path):
    path = Path(path)
    if file_hash(path) != path.with_suffix(".sha256").read_text().strip():
        raise ValueError("Saved result checksum mismatch")
    return json.loads(path.read_text())


def comparison_table(result):
    return pd.DataFrame(
        [
            {
                key: row.get(key)
                for key in [
                    "method",
                    "status",
                    "objective",
                    "objective_gap",
                    "selection_feasible",
                    "allocation_feasible",
                    "feasible_fraction",
                    "seconds",
                    "total_seconds",
                    "evaluations",
                    "shots_used",
                    "num_qubits",
                ]
            }
            for row in result.get("results", [])
        ]
    )


def export_report(run_id, root=None):
    """Self-contained Plotly HTML from a checksum-verified real run."""
    import html
    import plotly.express as px

    root = root or project_root()
    if Path(run_id).name != run_id:
        raise ValueError("Invalid run identifier")
    folder = root / "artifacts/runs" / run_id
    result = read_result(folder / "result.json")
    table = comparison_table(result)
    if table.empty:
        raise ValueError("This report exporter requires an optimization comparison")
    measured = table.dropna(subset=["objective"])
    fig = px.bar(measured, x="method", y="objective", title="Original selection objective — lower is better")
    fig.update_layout(template="plotly_white")
    content = "<h1>Q-Compass experiment</h1><p>Optimization results, not realized investment returns.</p>"
    content += "<p>Dataset fingerprint: " + html.escape(result["dataset_fingerprint"]) + "</p>"
    content += table.to_html(index=False, na_rep="Unavailable")
    content += fig.to_html(full_html=False, include_plotlyjs=True)
    content += (
        "<h2>Limitations</h2><ul>"
        + "".join("<li>" + html.escape(x) + "</li>" for x in result["limitations"])
        + "</ul>"
    )
    path = folder / "report.html"
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>Q-Compass report</title>"
        "<style>body{font:16px system-ui;max-width:1200px;margin:48px auto;color:#112344}"
        "table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #ccd7e2}</style>"
        "</head><body>" + content + "</body></html>"
    )
    return path


def run_experiment(config, root=None, run_id=None, progress=print, cancel=None):
    root = root or project_root()
    cfg = config if isinstance(config, RunConfig) else RunConfig(**config)
    started = perf_counter()
    progress("Verifying frozen source files and preparing a past-only estimation window")
    manifest, _, _ = load_snapshot(cfg.dataset_id, root)
    instance, audit = build_instance(
        cfg.dataset_id, cfg.n, cfg.k, cfg.sector_limit, cfg.risk_aversion, cfg.as_of, root, cfg.symbols
    )
    methods = []
    progress(f"Prepared {instance.n} actual stocks; exactly {instance.k} holdings")
    configs = (
        [QuantumConfig(**c) for c in cfg.quantum_configs]
        if cfg.quantum_configs
        else [QuantumConfig("qaoa-x-p1"), QuantumConfig("qaoa-x-p2", depth=2)]
    )
    ranker = None
    if cfg.ranker_path:
        ranker = TemporalRanker.from_dict(json.loads(Path(cfg.ranker_path).read_text()))
        ranker.predict(instance)  # fail before any work if chronology is invalid
    results = []

    # Budget unit = one circuit sample batch. Reserve ALL final sampling batches.
    # Fixed: B-1 optimization + 1 final; adaptive: B-3 optimization + 3 finals.
    # Two pilots + continuation; any early stop underspends rather than overspends.
    def fixed(conf):
        return solve_qaoa(
            instance,
            conf,
            evaluations=cfg.batches - 1,
            shots=cfg.shots,
            seed=cfg.seed,
            progress=progress,
            cancel=cancel,
            max_seconds=cfg.max_seconds,
        )

    def adaptive():
        reserved = len(configs) + 1
        return adaptive_solve(
            instance,
            configs,
            evaluations=cfg.batches - reserved,
            pilot_evaluations=min(10, max(1, (cfg.batches - reserved) // reserved)),
            shots=cfg.shots,
            seed=cfg.seed,
            progress=progress,
            cancel=cancel,
            max_seconds=cfg.max_seconds,
            ranker=ranker,
        )

    def equal_search():
        runs = []
        t = perf_counter()
        for i, conf in enumerate(configs):
            batch_budget = cfg.batches // len(configs) + (1 if i < cfg.batches % len(configs) else 0)
            runs.append(
                solve_qaoa(
                    instance,
                    conf,
                    evaluations=batch_budget - 1,
                    shots=cfg.shots,
                    seed=cfg.seed + i * 1009,
                    progress=progress,
                    cancel=cancel,
                    max_seconds=max(0, cfg.max_seconds - (perf_counter() - t)),
                )
            )
            if cancel and cancel():
                break
        winner = min(
            runs,
            key=lambda r: (
                r["objective"] is None,
                r["objective"] if r["objective"] is not None else float("inf"),
            ),
        )
        return {
            **winner,
            "method": "equal-budget-search",
            "candidates": runs,
            "seconds": perf_counter() - t,
            "evaluations": sum(r["evaluations"] for r in runs),
            "shots_used": sum(r["shots_used"] for r in runs),
        }

    methods = [
        ("Exhaustive reference", lambda: exact_select(instance)),
        ("Greedy + local swaps", lambda: greedy_select(instance)),
        *[(c.name, lambda conf=c: fixed(conf)) for c in configs],
    ]
    if cfg.include_adaptive:
        methods.append(("Adaptive pilots", adaptive))
    if cfg.extra_baselines:
        methods.insert(2, ("SCIP subset reference", lambda: scip_select(instance, min(30, cfg.max_seconds))))
        if cfg.include_adaptive:
            methods.append(("Equal-budget configuration search", equal_search))
    weight_args = dict(
        min_weight=cfg.min_weight,
        max_weight=cfg.max_weight,
        sector_caps={s: cfg.sector_weight_cap for s in set(instance.sectors)},
    )
    for label, method in methods:
        if cancel and cancel():
            break
        progress(f"Running {label}")
        t = perf_counter()
        try:
            row = method()
            bits = row.get("bits")
            row["selection_feasible"] = bits is not None and instance.feasible(bits)
            row["selection_violations"] = (
                instance.violations(bits) if bits is not None else ["No selection found"]
            )
            row["allocation"] = allocate(instance, bits, **weight_args) if bits is not None else None
            row["allocation_feasible"] = bool(
                row["allocation"] and row["allocation"].get("weights") is not None
            )
            if cfg.repair:
                from qcompass.classical.weights import repair_selection

                row["repaired"] = (
                    repair_selection(instance, bits, **weight_args) if bits is not None else None
                )
            row["total_seconds"] = perf_counter() - t
            if row.get("shots_used", 0) > cfg.batches * cfg.shots:
                raise RuntimeError("Quantum sampling budget exceeded")
        except Exception as exc:
            row = {
                "method": label,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "seconds": perf_counter() - t,
                "total_seconds": perf_counter() - t,
            }
            progress(f"{label} failed: {exc}")
        results.append(row)
    reference = next((r for r in results if r.get("certified") and r.get("objective") is not None), None)
    for row in results:
        row["objective_gap"] = (
            row["objective"] - reference["objective"]
            if reference and row.get("objective") is not None
            else None
        )
        allocation = row.get("allocation")
        if allocation and allocation.get("weights") is not None:
            w = np.asarray(allocation["weights"])
            allocation["estimated_annual_return"] = float(instance.mu @ w)
            allocation["estimated_annual_volatility"] = float(np.sqrt(w @ instance.covariance @ w))
    extra = {}
    if cfg.extra_baselines and not (cancel and cancel()):
        progress("Running continuous and joint classical allocation references")
        for name, function in [("continuous_mvo", continuous_mvo), ("joint_classical", joint_select_weights)]:
            try:
                args = dict(weight_args)
                if name == "continuous_mvo":
                    args["min_weight"] = 0
                else:
                    args["time_limit"] = min(30, cfg.max_seconds)
                extra[name] = function(instance, **args)
            except Exception as exc:
                extra[name] = {"status": "failed", "error": str(exc)}
    output = {
        "schema_version": 1,
        "run_id": run_id or uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kind": "optimization_comparison",
        "config": cfg.model_dump(),
        "dataset_fingerprint": manifest["fingerprint"],
        "instance": instance.to_dict(),
        "preparation": audit,
        "results": results,
        "allocation_references": extra,
        "software": software_record(root),
        "context_ranker": ranker.to_dict() if ranker else None,
        "elapsed_seconds": perf_counter() - started,
        "cancelled": bool(cancel and cancel()),
        "budget": {
            "sampling_batches_per_quantum_method": cfg.batches,
            "shots_per_batch": cfg.shots,
            "max_shots_per_quantum_method": cfg.batches * cfg.shots,
            "includes": (
                "pilots, continuation, final sampling; total_seconds includes allocation/repair"
                if cfg.include_adaptive
                else "fixed-configuration tuning and final sampling; total_seconds includes allocation/repair"
            ),
            "not_equalized": "wall-clock and classical objective evaluation cost",
        },
        "limitations": [
            "Current-membership optimization experiment, not historical investment performance",
            "Binary equal-weight selection is a proxy; allocation is a separate classical stage",
            "Provider-adjusted prices are not independently certified across all corporate actions",
            *([
                "Past-only trained context ranker supplied; its comparative benefit is unproven"
                if ranker
                else "Pilot-only controller; no trained context model or best validation-selected configuration claimed"
            ] if cfg.include_adaptive else []),
        ],
    }
    path = save_result(output, root)
    progress(f"Saved verified run {output['run_id']}")
    return output, path
