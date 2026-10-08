"""Commands use the same validated package as the dashboard."""

import json
from pathlib import Path

import typer

from qcompass.data.snapshots import list_snapshots, load_snapshot
from qcompass.experiments.runner import RunConfig, comparison_table, read_result, run_experiment
from qcompass.experiments.store import JobStore
from qcompass.paths import project_root

app = typer.Typer(no_args_is_help=True, help="Q-Compass: real NIFTY data, local quantum simulation")


def latest(dataset):
    if dataset:
        return dataset
    snapshots = list_snapshots()
    if not snapshots:
        raise typer.BadParameter("No authentic dataset. Run qcompass fetch or import-data first")
    return snapshots[0]["dataset_id"]


def progress(value):
    if isinstance(value, dict):
        if value.get("phase") == "complete":
            typer.echo(
                f"  {value['method']}: {value['evaluations']} evaluations, valid fraction {value['feasible_fraction']:.3f}"
            )
    else:
        typer.echo(value)


@app.command()
def fetch(start: str = "2019-01-01", end: str | None = None):
    """Download official identifiers and genuine provider prices; freeze a new snapshot."""
    from qcompass.data.sources import fetch_snapshot

    data = fetch_snapshot(start=start, end=end, progress=progress)
    typer.echo(data["dataset_id"])


@app.command("import-data")
def import_data(bundle: Path):
    """Import a genuine CSV bundle with provenance.json; never infer provenance."""
    from qcompass.data.importer import import_bundle

    typer.echo(import_bundle(bundle)["dataset_id"])


@app.command()
def datasets():
    """List frozen coverage and acquisition failures."""
    for data in list_snapshots():
        typer.echo(
            f"{data['dataset_id']} | {data['stock_count']}/50 histories | {data['first_date']}–{data['last_date']} | {len(data['failures'])} excluded histories"
        )


@app.command()
def validate(dataset: str | None = None):
    """Check all file fingerprints and structural price validity."""
    from qcompass.data.validation import validate_prices

    manifest, _, prices = load_snapshot(latest(dataset))
    audit = validate_prices(prices)
    typer.echo(
        json.dumps(
            {
                "dataset": manifest["dataset_id"],
                "fingerprint": manifest["fingerprint"],
                "audit": audit,
                "crosscheck": manifest["crosscheck"]["status"],
            },
            indent=2,
        )
    )


@app.command()
def experiment(
    dataset: str | None = None,
    settings: Path | None = None,
    n: int = 8,
    k: int = 4,
    batches: int = 48,
    shots: int = 512,
    seed: int = 42,
    as_of: str | None = None,
    queue: bool = False,
):
    """Run a current-universe optimization comparison, not a backtest."""
    config = (
        json.loads(settings.read_text())
        if settings
        else dict(n=n, k=k, batches=batches, shots=shots, seed=seed, as_of=as_of)
    )
    config["dataset_id"] = latest(dataset or config.get("dataset_id"))
    cfg = RunConfig(**config)
    if queue:
        from qcompass.experiments.worker import start_worker

        job = JobStore().submit(cfg.model_dump())
        start_worker()
        typer.echo(f"Queued {job}")
    else:
        from filelock import FileLock

        root = project_root()
        (root / "artifacts").mkdir(exist_ok=True)
        with FileLock(root / "artifacts/worker.lock", timeout=0):
            result, path = run_experiment(cfg, progress=progress)
        typer.echo(comparison_table(result).to_string(index=False))
        typer.echo(f"Saved: {path}")


@app.command()
def milestone(
    settings: Path = typer.Option(
        Path("configs/objectives-1-2.json"),
        "--settings",
        help="Pinned Objectives 1/2 milestone settings",
    ),
):
    """Run and independently verify two seeded baseline comparisons."""
    from filelock import FileLock

    from qcompass.experiments.milestone import MilestoneFailure, run_milestone

    root = project_root()
    settings_path = settings if settings.is_absolute() else root / settings
    (root / "artifacts").mkdir(exist_ok=True)
    try:
        with FileLock(root / "artifacts/worker.lock", timeout=0):
            evidence, package = run_milestone(settings_path, root=root, progress=progress)
    except MilestoneFailure as exc:
        typer.echo(f"FAILED — evidence: {exc.package / 'evidence.json'}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"PASS — evidence: {package / 'evidence.json'}")
    typer.echo(f"Saved runs: {', '.join(record['run_id'] for record in evidence['runs'])}")


@app.command()
def replay(run_id: str):
    """Verify and print a stored result without running any optimizer."""
    if Path(run_id).name != run_id:
        raise typer.BadParameter("Use the run identifier, not a path")
    result = read_result(project_root() / "artifacts/runs" / run_id / "result.json")
    typer.echo(comparison_table(result).to_string(index=False))
    typer.echo(f"Dataset fingerprint: {result['dataset_fingerprint']}")


@app.command()
def reproduce(run_id: str):
    """Rerun exact saved settings against unchanged source data and compare discrete outputs."""
    if Path(run_id).name != run_id:
        raise typer.BadParameter("Invalid run identifier")
    previous = read_result(project_root() / "artifacts/runs" / run_id / "result.json")
    from filelock import FileLock

    with FileLock(project_root() / "artifacts/worker.lock", timeout=0):
        current, path = run_experiment(previous["config"], progress=progress)
    exact_keys = ["method", "status", "bits", "counts", "evaluations", "shots_used"]
    left = [{k: r.get(k) for k in exact_keys} for r in previous["results"]]
    right = [{k: r.get(k) for k in exact_keys} for r in current["results"]]
    matched = left == right and previous["dataset_fingerprint"] == current["dataset_fingerprint"]
    typer.echo(
        f"Seeded discrete outputs identical: {matched}. Runtime is not expected to match. New run: {path.parent.name}"
    )
    if previous["software"]["source_fingerprint"] != current["software"]["source_fingerprint"]:
        typer.echo("Source code changed since the original run; both code fingerprints are recorded.")
    if not matched:
        raise typer.Exit(code=1)


@app.command()
def jobs():
    for job in JobStore().list():
        typer.echo(f"{job['id']} | {job['status']} | {job['error'] or ''}")


@app.command()
def cancel(job_id: str):
    JobStore().cancel(job_id)
    typer.echo("Cancellation requested. A running bounded circuit job must finish first.")


@app.command()
def worker(once: bool = False):
    from qcompass.experiments.worker import work

    work(once=once)


@app.command()
def batch(settings: Path, seeds: str = "11,42,73", sizes: str = "8", dataset: str | None = None):
    """Queue an explicit small seed/size campaign; never an unbounded Cartesian sweep."""
    import uuid
    from qcompass.experiments.worker import start_worker

    selected_seeds = [int(v.strip()) for v in seeds.split(",")]
    selected_sizes = [int(v.strip()) for v in sizes.split(",")]
    if not 1 <= len(selected_seeds) * len(selected_sizes) <= 12:
        raise typer.BadParameter("Queue one to twelve explicit jobs at a time")
    settings_data = json.loads(settings.read_text())
    dataset_id = latest(dataset or settings_data.get("dataset_id"))
    batch_id = uuid.uuid4().hex
    configs = [
        RunConfig(**{**settings_data, "dataset_id": dataset_id, "n": n, "seed": s, "batch_id": batch_id})
        for n in selected_sizes
        for s in selected_seeds
    ]
    store = JobStore()
    for i, config in enumerate(configs):
        store.submit(config.model_dump(), token=f"{batch_id}-{i}")
    start_worker()
    typer.echo(
        f"Queued batch {batch_id}: {len(configs)} serial jobs. Use jobs / cancel; interrupted jobs remain explicit."
    )


@app.command("resume-batch")
def resume_batch(batch_id: str):
    """Create new attempts only for failed/interrupted/cancelled configurations."""
    from qcompass.experiments.worker import start_worker

    store = JobStore()
    candidates = [j for j in reversed(store.list()) if j["config"].get("batch_id") == batch_id]
    newest = {}
    for j in candidates:
        newest[json.dumps(j["config"], sort_keys=True)] = j
    count = 0
    for j in newest.values():
        if j["status"] in {"failed", "interrupted", "cancelled"}:
            store.submit(j["config"], token=f"resume-{j['id']}")
            count += 1
    if count:
        start_worker()
    typer.echo(f"Queued {count} new attempts; completed and active work was not duplicated")


@app.command()
def report(run_id: str):
    """Export measured comparison tables and an offline interactive figure."""
    from qcompass.experiments.runner import export_report

    typer.echo(str(export_report(run_id)))


@app.command("train-ranker")
def train_ranker(target_date: str = "2023-01-01"):
    """Fit a tree ONLY from saved 2020–2022 experiment observations. No exact-oracle labels."""
    from qcompass.adaptive.controller import TemporalRanker

    records = []
    for path in (project_root() / "artifacts/runs").glob("*/result.json"):
        run = read_result(path)
        instance = run.get("instance", {})
        as_of = instance.get("as_of", "")
        if not "2020-01-01" <= as_of <= "2022-12-31" or as_of >= target_date:
            continue
        candidates = [
            r
            for r in run.get("results", [])
            if r.get("config")
            and r.get("method") not in {"adaptive", "equal-budget-search"}
            and r.get("objective") is not None
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: (r["objective"], -r["feasible_fraction"]))
        records.append(
            {
                "as_of": as_of,
                "split": "train",
                "features": instance["features"],
                "best_config": best["config"]["name"],
                "config": best["config"],
                "n": len(instance["symbols"]),
                "num_qubits": best["num_qubits"],
                "parameters": best["parameters"],
                "source_run": run["run_id"],
            }
        )
    ranker = TemporalRanker().fit(records, target_date)
    folder = project_root() / "artifacts/models"
    folder.mkdir(parents=True, exist_ok=True)
    import uuid

    path = folder / f"tree-{uuid.uuid4().hex[:12]}.json"
    path.write_text(json.dumps(ranker.to_dict(), indent=2, allow_nan=False))
    typer.echo(f"Trained on {len(records)} genuine earlier runs; saved {path}")


@app.command()
def backtest(
    start: str, end: str, dataset: str | None = None, method: str = "exact", fixed_universe: bool = False
):
    """Strict by default; --fixed-universe explicitly allows a separately labelled research study."""
    from qcompass.evaluation.study import run_study
    from filelock import FileLock

    root = project_root()
    (root / "artifacts").mkdir(exist_ok=True)
    with FileLock(root / "artifacts/worker.lock", timeout=0):
        result, path = run_study(
            latest(dataset),
            start,
            end,
            method,
            "fixed_universe" if fixed_universe else "strict_historical",
            progress=progress,
        )
    typer.echo(f"Saved {path}")
    typer.echo(
        json.dumps({bps: value["metrics"] for bps, value in result["cost_sensitivity"].items()}, indent=2)
    )


if __name__ == "__main__":
    app()
