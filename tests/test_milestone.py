"""Objective 1/2 milestone behavior; market integration uses only the sealed snapshot."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
import pytest

from qcompass.experiments.runner import RunConfig
from qcompass.portfolio.models import PortfolioInstance


PINNED_DATASET = "nifty50-20260905T080605-28fd98-sealed-0d14f0-reprocessed-641edf"


def _small_instance():
    return PortfolioInstance(
        symbols=["A", "B", "C", "D"],
        sectors=["one", "two", "three", "four"],
        mu=np.array([0.10, 0.08, 0.06, 0.04]),
        covariance=np.eye(4) * 0.04,
        k=2,
        sector_min={},
        sector_max={"one": 1, "two": 1, "three": 1, "four": 1},
        as_of="2026-09-04",
        dataset_id="verified-fixture",
    )


def _run_method_names(monkeypatch, tmp_path, include_adaptive):
    from qcompass.experiments import runner

    instance = _small_instance()
    bits = [1, 1, 0, 0]

    def selection(method, status="completed", certified=False, **extra):
        return {
            "method": method,
            "status": status,
            "bits": bits,
            "objective": instance.objective(bits),
            "certified": certified,
            "counts": {"0011": 64} if method.startswith("qaoa-") else {},
            "evaluations": extra.get("evaluations", 1),
            "shots_used": extra.get("shots_used", 64 if method.startswith("qaoa-") else 0),
        }

    monkeypatch.setattr(runner, "load_snapshot", lambda *args: ({"fingerprint": "f" * 64}, None, None))
    monkeypatch.setattr(runner, "build_instance", lambda *args: (instance, {"return_observations": 252}))
    monkeypatch.setattr(runner, "exact_select", lambda value: selection("exact", "optimal", True))
    monkeypatch.setattr(runner, "greedy_select", lambda value: selection("greedy_swaps", "heuristic"))
    monkeypatch.setattr(runner, "scip_select", lambda *args: selection("scip_subset", "optimal", True))
    monkeypatch.setattr(
        runner,
        "solve_qaoa",
        lambda value, config, evaluations, shots, **kwargs: selection(
            config.name, evaluations=evaluations, shots_used=(evaluations + 1) * shots
        ),
    )
    monkeypatch.setattr(runner, "adaptive_solve", lambda *args, **kwargs: selection("adaptive"))
    monkeypatch.setattr(
        runner,
        "allocate",
        lambda *args, **kwargs: {"status": "optimal", "weights": [0.5, 0.5, 0.0, 0.0]},
    )
    monkeypatch.setattr(runner, "continuous_mvo", lambda *args, **kwargs: {"status": "optimal"})
    monkeypatch.setattr(runner, "joint_select_weights", lambda *args, **kwargs: {"status": "optimal"})
    monkeypatch.setattr(runner, "software_record", lambda root: {"source_fingerprint": "s" * 64})

    result, _ = runner.run_experiment(
        RunConfig(dataset_id="verified-fixture", include_adaptive=include_adaptive),
        root=tmp_path,
        progress=lambda value: None,
    )
    return result


def test_adaptive_methods_remain_default_but_baseline_only_omits_them(monkeypatch, tmp_path):
    assert RunConfig(dataset_id="verified-fixture").include_adaptive is True
    default = _run_method_names(monkeypatch, tmp_path / "default", True)
    baseline = _run_method_names(monkeypatch, tmp_path / "baseline", False)

    assert [row["method"] for row in default["results"]] == [
        "exact",
        "greedy_swaps",
        "scip_subset",
        "qaoa-x-p1",
        "qaoa-x-p2",
        "adaptive",
        "equal-budget-search",
    ]
    assert [row["method"] for row in baseline["results"]] == [
        "exact",
        "greedy_swaps",
        "scip_subset",
        "qaoa-x-p1",
        "qaoa-x-p2",
    ]
    assert set(baseline["allocation_references"]) == {"continuous_mvo", "joint_classical"}
    assert not any("controller" in limitation.lower() for limitation in baseline["limitations"])
    assert "pilot" not in baseline["budget"]["includes"].lower()


def test_baseline_only_rejects_a_ranker_before_work_starts():
    with pytest.raises(ValueError, match="ranker"):
        RunConfig(dataset_id="verified-fixture", include_adaptive=False, ranker_path="ranker.json")


def _accepted_pair():
    instance = _small_instance()
    requested_quantum = [
        {
            "name": "qaoa-x-p1",
            "depth": 1,
            "mixer": "x",
            "optimizer": "cobyla",
            "alpha": 1.0,
        },
        {
            "name": "qaoa-x-p2",
            "depth": 2,
            "mixer": "x",
            "optimizer": "cobyla",
            "alpha": 1.0,
        },
    ]
    config = RunConfig(
        dataset_id="verified-fixture",
        n=4,
        k=2,
        sector_limit=1,
        min_weight=0.1,
        max_weight=0.6,
        sector_weight_cap=0.6,
        batches=12,
        shots=64,
        include_adaptive=False,
        extra_baselines=False,
        as_of="2026-09-04",
        quantum_configs=requested_quantum,
    ).model_dump()
    common = {
        "bits": [1, 1, 0, 0],
        "objective": -0.07,
        "selection_feasible": True,
        "allocation_feasible": True,
        "allocation": {"status": "optimal", "weights": [0.5, 0.5, 0.0, 0.0]},
    }
    rows = [
        {**common, "method": "exact", "status": "optimal", "certified": True, "evaluations": 6},
        {**common, "method": "greedy_swaps", "status": "heuristic", "evaluations": 9},
        {
            **common,
            "method": "qaoa-x-p1",
            "status": "completed",
            "counts": {"0011": 64},
            "evaluations": 11,
            "shots_used": 768,
            "num_qubits": 4,
            "config": {
                **requested_quantum[0],
                "penalty_multiplier": 1.0,
                "initial_point": None,
                "noise": 0.0,
            },
            "metadata": {"final_sampling_shots": 64},
        },
        {
            **common,
            "method": "qaoa-x-p2",
            "status": "completed",
            "counts": {"0011": 64},
            "evaluations": 11,
            "shots_used": 768,
            "num_qubits": 4,
            "config": {
                **requested_quantum[1],
                "penalty_multiplier": 1.0,
                "initial_point": None,
                "noise": 0.0,
            },
            "metadata": {"final_sampling_shots": 64},
        },
    ]
    base = {
        "schema_version": 1,
        "run_id": "run-a",
        "config": config,
        "dataset_fingerprint": "f" * 64,
        "software": {"source_fingerprint": "s" * 64},
        "instance": instance.to_dict(),
        "results": rows,
        "cancelled": False,
    }
    other = deepcopy(base)
    other["run_id"] = "run-b"
    return base, other


def test_evidence_accepts_two_complete_identical_baseline_runs():
    from qcompass.experiments.milestone import assess_runs

    first, second = _accepted_pair()
    evidence = assess_runs(first, second)
    assert evidence["passed"] is True
    assert all(method["selection_feasibility"]["passed"] for method in evidence["methods"])
    assert all(method["allocation_feasibility"]["passed"] for method in evidence["methods"])


def test_evidence_rejects_matched_nonstandard_qaoa_records():
    from qcompass.experiments.milestone import assess_runs

    first, second = _accepted_pair()
    for run in (first, second):
        for row in run["results"]:
            if row["method"].startswith("qaoa-"):
                row["config"].update(mixer="xy", optimizer="spsa", alpha=0.25, depth=4, noise=0.1)
                row["config"]["initial_point"] = [0.1] * 8
    evidence = assess_runs(first, second)
    assert evidence["passed"] is False
    failed = {check["name"] for check in evidence["checks"] if not check["passed"]}
    assert "run_a.qaoa-x-p1.standard_baseline" in failed
    assert "run_b.qaoa-x-p2.config_matches_request" in failed


def test_evidence_rejects_internal_config_instance_cardinality_drift():
    from qcompass.experiments.milestone import assess_runs

    first, second = _accepted_pair()
    first["config"]["k"] = 3
    second["config"]["k"] = 3
    evidence = assess_runs(first, second)
    assert evidence["passed"] is False
    failed = {check["name"] for check in evidence["checks"] if not check["passed"]}
    assert "run_a.config_instance_consistency" in failed
    assert "run_b.config_instance_consistency" in failed


def test_evidence_binds_both_payloads_to_trusted_preflight_inputs():
    from qcompass.experiments.milestone import assess_runs

    first, second = _accepted_pair()
    trusted_config = RunConfig(**deepcopy(first["config"]))
    trusted_instance = PortfolioInstance.from_dict(deepcopy(first["instance"]))
    for run in (first, second):
        run["instance"]["mu"][0] += 0.01
        changed = PortfolioInstance.from_dict(run["instance"])
        for row in run["results"]:
            row["objective"] = changed.objective(row["bits"])
    evidence = assess_runs(
        first,
        second,
        trusted_config=trusted_config,
        trusted_instance=trusted_instance,
    )
    assert evidence["passed"] is False
    failed = {check["name"] for check in evidence["checks"] if not check["passed"]}
    assert "run_a.trusted_instance" in failed
    assert "run_b.trusted_instance" in failed


@pytest.mark.parametrize(
    ("mutation", "failed_check"),
    [
        ("bits", "reproducibility.bits"),
        ("counts", "reproducibility.counts"),
        ("weights", "reproducibility.weights"),
        ("objective", "reproducibility.objective"),
        ("missing", "run_b.required_methods"),
        ("cancelled", "run_a.not_cancelled"),
        ("failed", "run_b.qaoa-x-p1.status"),
        ("invalid_counts", "run_b.qaoa-x-p1.counts"),
        ("malformed_bits", "run_b.qaoa-x-p1.selection_feasibility"),
    ],
)
def test_evidence_fails_closed_for_altered_or_invalid_results(mutation, failed_check):
    from qcompass.experiments.milestone import assess_runs

    first, second = _accepted_pair()
    quantum = next(row for row in second["results"] if row["method"] == "qaoa-x-p1")
    if mutation == "bits":
        quantum["bits"] = [1, 0, 1, 0]
        quantum["objective"] = -0.06
        quantum["allocation"]["weights"] = [0.5, 0.0, 0.5, 0.0]
    elif mutation == "counts":
        quantum["counts"] = {"0011": 63, "0101": 1}
    elif mutation == "weights":
        quantum["allocation"]["weights"] = [0.49, 0.51, 0.0, 0.0]
    elif mutation == "objective":
        quantum["objective"] = -0.069
    elif mutation == "missing":
        second["results"] = [row for row in second["results"] if row["method"] != "qaoa-x-p2"]
    elif mutation == "cancelled":
        first["cancelled"] = True
    elif mutation == "failed":
        quantum["status"] = "failed"
    elif mutation == "invalid_counts":
        quantum["counts"] = {"00x1": 65, "0011": -1}
    elif mutation == "malformed_bits":
        quantum["bits"] = [1, None, 0, 0]

    evidence = assess_runs(first, second)
    assert evidence["passed"] is False
    failed = {check["name"] for check in evidence["checks"] if not check["passed"]}
    assert any(name.startswith(failed_check) for name in failed)


@pytest.mark.parametrize("settings_text", ["not-json", '{"dataset_id":"missing","n":8,"k":4}'])
def test_milestone_bad_input_writes_failed_evidence_without_starting_solver(
    tmp_path, monkeypatch, settings_text
):
    from qcompass.experiments import milestone

    settings = tmp_path / "settings.json"
    settings.write_text(settings_text)
    solver_started = False

    def forbidden_solver(*args, **kwargs):
        nonlocal solver_started
        solver_started = True
        raise AssertionError("solver must not start")

    monkeypatch.setattr(milestone, "run_experiment", forbidden_solver, raising=False)
    with pytest.raises(milestone.MilestoneFailure):
        milestone.run_milestone(settings, root=tmp_path, progress=lambda value: None)
    packages = list((tmp_path / "artifacts/milestones").iterdir())
    assert len(packages) == 1
    evidence = json.loads((packages[0] / "evidence.json").read_text())
    assert evidence["passed"] is False
    assert evidence["status"] == "failed"
    assert evidence["failure"]["stage"] == "preflight"
    assert solver_started is False


def test_milestone_cli_returns_nonzero_and_points_to_failed_evidence(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from qcompass.cli import app

    monkeypatch.setenv("QCOMPASS_ROOT", str(tmp_path))
    settings = tmp_path / "broken.json"
    settings.write_text("not-json")
    answer = CliRunner().invoke(app, ["milestone", "--settings", str(settings)])
    assert answer.exit_code == 1
    assert "FAILED" in answer.output
    package = next((tmp_path / "artifacts/milestones").iterdir())
    assert str(package / "evidence.json") in answer.output


def _write_small_real_settings(path, **overrides):
    values = {
        "dataset_id": PINNED_DATASET,
        "as_of": "2026-09-04",
        "n": 8,
        "k": 4,
        "sector_limit": 1,
        "min_weight": 0.05,
        "max_weight": 0.5,
        "sector_weight_cap": 0.5,
        "batches": 12,
        "shots": 64,
        "seed": 42,
        "max_seconds": 120,
        "extra_baselines": False,
        "repair": False,
        "include_adaptive": False,
        "quantum_configs": [
            {
                "name": "qaoa-x-p1",
                "depth": 1,
                "mixer": "x",
                "optimizer": "cobyla",
                "alpha": 1.0,
            },
            {
                "name": "qaoa-x-p2",
                "depth": 2,
                "mixer": "x",
                "optimizer": "cobyla",
                "alpha": 1.0,
            },
        ],
    }
    values.update(overrides)
    path.write_text(json.dumps(values))
    return path


@pytest.mark.realdata
def test_nonstandard_quantum_settings_fail_preflight_before_solver(tmp_path, monkeypatch):
    from qcompass.experiments import milestone

    root = Path(__file__).resolve().parents[1]
    if not (root / "data/manifests" / f"{PINNED_DATASET}.json").exists():
        pytest.skip("Pinned verified NIFTY snapshot is absent")
    settings = _write_small_real_settings(tmp_path / "nonstandard.json")
    values = json.loads(settings.read_text())
    values["quantum_configs"][0].update(mixer="xy", optimizer="spsa", alpha=0.25, depth=4)
    settings.write_text(json.dumps(values))
    solver_started = False

    def forbidden_solver(*args, **kwargs):
        nonlocal solver_started
        solver_started = True
        raise AssertionError("solver must not start")

    monkeypatch.setattr(milestone, "run_experiment", forbidden_solver)
    package = None
    try:
        with pytest.raises(milestone.MilestoneFailure) as failure:
            milestone.run_milestone(settings, root=root, progress=lambda value: None)
        package = failure.value.package
        evidence = json.loads((package / "evidence.json").read_text())
        assert evidence["failure"]["stage"] == "preflight"
        assert "standard X-mixer p1/p2" in evidence["failure"]["error"]
        assert solver_started is False
    finally:
        if package is not None:
            shutil.rmtree(package, ignore_errors=True)


@pytest.mark.realdata
def test_second_run_failure_preserves_first_run_and_renders_failure(tmp_path, monkeypatch):
    from qcompass.data.snapshots import load_snapshot
    from qcompass.experiments import milestone
    from qcompass.experiments.runner import save_result

    root = Path(__file__).resolve().parents[1]
    if not (root / "data/manifests" / f"{PINNED_DATASET}.json").exists():
        pytest.skip("Pinned verified NIFTY snapshot is absent")
    load_snapshot(PINNED_DATASET, root)
    settings = _write_small_real_settings(tmp_path / "partial-failure.json")
    first, _ = _accepted_pair()
    first["run_id"] = f"partial-{uuid.uuid4().hex}"
    calls = 0

    def fail_second(config, root, progress):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second run crashed")
        path = save_result(first, root)
        return first, path

    monkeypatch.setattr(milestone, "run_experiment", fail_second)
    package = None
    try:
        with pytest.raises(milestone.MilestoneFailure) as failure:
            milestone.run_milestone(settings, root=root, progress=lambda value: None)
        package = failure.value.package
        evidence = json.loads((package / "evidence.json").read_text())
        report = (package / "report.md").read_text()
        assert evidence["failure"]["stage"] == "run_b"
        assert evidence["runs"] == [
            {
                "run_id": first["run_id"],
                "path": str(root / "artifacts/runs" / first["run_id"] / "result.json"),
            }
        ]
        assert "## Failure" in report
        assert "run_b" in report
        assert "RuntimeError: second run crashed" in report
        assert first["run_id"] in report
    finally:
        shutil.rmtree(root / "artifacts/runs" / first["run_id"], ignore_errors=True)
        if package is not None:
            shutil.rmtree(package, ignore_errors=True)


@pytest.mark.realdata
@pytest.mark.slow
def test_actual_sealed_snapshot_milestone_end_to_end_uses_no_fabricated_prices(tmp_path):
    from qcompass.data.snapshots import load_snapshot
    from qcompass.experiments.milestone import assess_runs, run_milestone
    from qcompass.experiments.runner import read_result

    root = Path(__file__).resolve().parents[1]
    dataset_id = PINNED_DATASET
    manifest_path = root / "data/manifests" / f"{dataset_id}.json"
    if not manifest_path.exists():
        pytest.skip("Pinned verified NIFTY snapshot is absent")
    load_snapshot(dataset_id, root)
    settings = _write_small_real_settings(tmp_path / "small-real-milestone.json")
    package = None
    run_ids = []
    try:
        evidence, package = run_milestone(settings, root=root, progress=lambda value: None)
        run_ids = [record["run_id"] for record in evidence["runs"]]
        assert evidence["passed"] is True
        assert evidence["provenance"]["coverage"]["retained_rows"] == 92859
        assert evidence["provenance"]["eligibility"]["eligible_count"] == 38
        assert evidence["provenance"]["quarantine"]["row_count"] == 12
        assert evidence["provenance"]["crosscheck"]["matched"] == 38
        assert evidence["provenance"]["crosscheck"]["mismatched"] == 0
        assert evidence["dataset_integrity"]["source_files_unchanged"] is True
        assert len(run_ids) == 2 and run_ids[0] != run_ids[1]
        assert (package / "evidence.json").is_file()
        assert (package / "comparison.csv").is_file()
        assert (package / "report.md").is_file()
        assert (package / "selected_adjusted_prices.csv").is_file()
        assert (package / "daily_returns.csv").is_file()
        assert (package / "annualized_expected_returns.csv").is_file()
        assert (package / "covariance.csv").is_file()
        assert (package / "constraints.json").is_file()
        assert evidence["derived_data"]["observation_label"].startswith(
            "Derived from checksum-verified authentic observations"
        )
        saved = [read_result(root / "artifacts/runs" / run_id / "result.json") for run_id in run_ids]
        trusted_config = RunConfig(**deepcopy(saved[0]["config"]))
        trusted_instance = PortfolioInstance.from_dict(deepcopy(saved[0]["instance"]))

        nonstandard = deepcopy(saved)
        for run in nonstandard:
            for row in run["results"]:
                if row["method"].startswith("qaoa-"):
                    row["config"].update(mixer="xy", optimizer="spsa", alpha=0.25, depth=4, noise=0.1)
                    row["config"]["initial_point"] = [0.1] * 8
        rejected = assess_runs(
            *nonstandard,
            trusted_config=trusted_config,
            trusted_instance=trusted_instance,
        )
        assert rejected["passed"] is False
        assert any(
            check["name"].endswith("standard_baseline") and not check["passed"]
            for check in rejected["checks"]
        )

        altered_inputs = deepcopy(saved)
        for run in altered_inputs:
            run["instance"]["mu"][0] += 0.01
            changed_instance = PortfolioInstance.from_dict(run["instance"])
            for row in run["results"]:
                if row.get("bits") is not None:
                    row["objective"] = changed_instance.objective(row["bits"])
        rejected = assess_runs(
            *altered_inputs,
            trusted_config=trusted_config,
            trusted_instance=trusted_instance,
        )
        assert rejected["passed"] is False
        assert any(
            check["name"].endswith("trusted_instance") and not check["passed"]
            for check in rejected["checks"]
        )
    finally:
        for run_id in run_ids:
            shutil.rmtree(root / "artifacts/runs" / run_id, ignore_errors=True)
        if package is not None:
            shutil.rmtree(package, ignore_errors=True)
