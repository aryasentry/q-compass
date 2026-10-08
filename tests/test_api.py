import json
import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from qcompass.api.app import create_app
from qcompass.data.snapshots import file_hash, manifest_hash
from qcompass.experiments.runner import read_result
from qcompass.experiments.store import JobStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MUTATION_HEADERS = {"X-QCompass-Client": "local-ui"}


def client(root):
    return TestClient(create_app(root, launch_worker=False), base_url="http://localhost")


def make_dataset(root: Path, dataset_id: str = "fixture-dataset", quarantine_rows: int = 1) -> dict:
    processed = root / "data/processed" / dataset_id
    raw = root / "data/raw" / dataset_id
    manifests = root / "data/manifests"
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    manifests.mkdir(parents=True, exist_ok=True)
    constituents = pd.DataFrame(
        [
            {"symbol": "AAA", "company": "Alpha", "sector": "Energy", "isin": "INE000A"},
            {"symbol": "BBB", "company": "Beta", "sector": "Banking", "isin": "INE000B"},
            {"symbol": "CCC", "company": "Gamma", "sector": "IT", "isin": "INE000C"},
            {"symbol": "DDD", "company": "Delta", "sector": "Health", "isin": "INE000D"},
        ]
    )
    prices = pd.DataFrame(
        [
            {"symbol": symbol, "date": date, "adj_close": float(i + 100)}
            for i, (symbol, date) in enumerate(
                ([(symbol, date) for symbol in constituents.symbol for date in ["2026-01-02", "2026-01-05"]])
            )
        ]
    )
    quarantine = pd.DataFrame(
        [
            {"symbol": "AAA", "date": "2026-01-03", "reason": f"rejected-{index}"}
            for index in range(quarantine_rows)
        ]
    )
    constituents.to_parquet(processed / "constituents.parquet", index=False)
    prices.to_parquet(processed / "prices.parquet", index=False)
    quarantine.to_parquet(processed / "quarantined.parquet", index=False)
    (raw / "AAA.metadata.json").write_text('{"currency":"INR","exchangeName":"NSI"}')
    files = {
        str(path.relative_to(root)): file_hash(path)
        for path in [
            processed / "constituents.parquet",
            processed / "prices.parquet",
            processed / "quarantined.parquet",
            raw / "AAA.metadata.json",
        ]
    }
    manifest = {
        "schema_version": 2,
        "dataset_id": dataset_id,
        "retrieved_at": "2026-01-06T12:00:00+00:00",
        "first_date": "2026-01-02",
        "last_date": "2026-01-05",
        "stock_count": 4,
        "row_count": 8,
        "quarantined_row_count": quarantine_rows,
        "crosscheck": {"status": "passed", "date": "2026-01-05", "mismatches": []},
        "processed_directory": f"data/processed/{dataset_id}",
        "files": files,
    }
    manifest["fingerprint"] = manifest_hash(manifest)
    (manifests / f"{dataset_id}.json").write_text(json.dumps(manifest))
    return manifest


def copy_verified_run(
    root: Path, destination_id: str | None = None, kind: str | None = None
) -> tuple[str, dict]:
    for source in sorted((PROJECT_ROOT / "artifacts/runs").glob("*/result.json")):
        try:
            result = read_result(source)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if kind is not None and result.get("kind") != kind:
            continue
        run_id = destination_id or source.parent.name
        destination = root / "artifacts/runs" / run_id
        destination.mkdir(parents=True)
        copied = dict(result)
        copied["run_id"] = run_id
        result_path = destination / "result.json"
        result_path.write_text(json.dumps(copied, indent=2, allow_nan=False))
        (destination / "result.sha256").write_text(file_hash(result_path))
        return run_id, copied
    pytest.skip("No checksum-verified saved run fixture is available")


def assert_finite(value):
    if isinstance(value, float):
        assert math.isfinite(value)
    elif isinstance(value, dict):
        for nested in value.values():
            assert_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_finite(nested)


def test_health_reports_local_simulation_worker_limit_without_writing(tmp_path):
    response = client(tmp_path).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "simulation", "worker_threads": 4}
    assert not (tmp_path / "artifacts").exists()


def test_empty_root_lists_are_empty_and_gets_do_not_create_queue(tmp_path):
    api = client(tmp_path)

    assert api.get("/api/datasets").json() == {"datasets": [], "warnings": []}
    assert api.get("/api/runs").json() == {"runs": [], "warnings": []}
    assert api.get("/api/jobs").json() == {"jobs": []}
    assert not (tmp_path / "artifacts").exists()


def test_dataset_listing_skips_bad_metadata_and_detail_verifies_all_sources(tmp_path):
    expected = make_dataset(tmp_path)
    (tmp_path / "data/manifests/broken.json").write_text("not json")
    api = client(tmp_path)

    listed = api.get("/api/datasets").json()
    assert listed["datasets"] == [
        {
            "dataset_id": "fixture-dataset",
            "first_date": "2026-01-02",
            "last_date": "2026-01-05",
            "stock_count": 4,
            "row_count": 8,
            "fingerprint": expected["fingerprint"],
            "quarantined_count": 1,
            "retrieved_at": "2026-01-06T12:00:00+00:00",
            "crosscheck": {"status": "passed", "date": "2026-01-05", "mismatches": []},
        }
    ]
    assert len(listed["warnings"]) == 1
    detail = api.get("/api/datasets/fixture-dataset")
    assert detail.status_code == 200
    assert detail.json()["constituents"][0] == {
        "symbol": "AAA",
        "company": "Alpha",
        "sector": "Energy",
        "isin": "INE000A",
    }
    assert detail.json()["quarantine_count"] == 1
    assert detail.json()["quarantine"] == [
        {"symbol": "AAA", "date": "2026-01-03", "reason": "rejected-0"}
    ]

    (tmp_path / "data/raw/fixture-dataset/AAA.metadata.json").write_text("tampered")
    assert api.get("/api/datasets").status_code == 200
    assert api.get("/api/datasets/fixture-dataset").status_code == 409
    assert api.post(
        "/api/datasets/fixture-dataset/verify", headers=MUTATION_HEADERS
    ).status_code == 409


def test_dataset_quarantine_detail_is_capped_but_reports_full_count(tmp_path):
    make_dataset(tmp_path, quarantine_rows=101)

    payload = client(tmp_path).get("/api/datasets/fixture-dataset").json()

    assert payload["quarantine_count"] == 101
    assert len(payload["quarantine"]) == 100


def test_dataset_detail_normalizes_missing_parquet_values_to_json_null(tmp_path):
    manifest = make_dataset(tmp_path)
    quarantine_path = tmp_path / "data/processed/fixture-dataset/quarantined.parquet"
    quarantine = pd.read_parquet(quarantine_path)
    quarantine["observed"] = [float("nan")]
    quarantine["reasons"] = [["missing-value"]]
    quarantine.to_parquet(quarantine_path, index=False)
    relative = str(quarantine_path.relative_to(tmp_path))
    manifest["files"][relative] = file_hash(quarantine_path)
    manifest["fingerprint"] = manifest_hash(manifest)
    (tmp_path / "data/manifests/fixture-dataset.json").write_text(json.dumps(manifest))

    response = client(tmp_path).get("/api/datasets/fixture-dataset")

    assert response.status_code == 200
    assert response.json()["quarantine"][0]["observed"] is None
    assert response.json()["quarantine"][0]["reasons"] == ["missing-value"]


def test_dataset_listing_orders_new_versions_by_version_timestamp(tmp_path):
    make_dataset(tmp_path, "older")
    newer = make_dataset(tmp_path, "newer")
    newer["retrieved_at"] = "2025-01-01T00:00:00+00:00"
    newer["reprocessed_at"] = "2026-02-01T00:00:00+00:00"
    newer["fingerprint"] = manifest_hash(newer)
    (tmp_path / "data/manifests/newer.json").write_text(json.dumps(newer))

    records = client(tmp_path).get("/api/datasets").json()["datasets"]

    assert [record["dataset_id"] for record in records] == ["newer", "older"]


def test_dataset_listing_skips_fingerprint_valid_invalid_summary_types(tmp_path):
    make_dataset(tmp_path, "valid")
    malformed = make_dataset(tmp_path, "malformed")
    malformed["stock_count"] = "four"
    malformed["reprocessed_at"] = ["not", "a", "timestamp"]
    malformed["fingerprint"] = manifest_hash(malformed)
    (tmp_path / "data/manifests/malformed.json").write_text(json.dumps(malformed))

    response = client(tmp_path).get("/api/datasets")

    assert response.status_code == 200
    assert [record["dataset_id"] for record in response.json()["datasets"]] == ["valid"]
    assert len(response.json()["warnings"]) == 1


def test_dataset_verify_and_identifier_errors_are_structured(tmp_path):
    manifest = make_dataset(tmp_path)
    api = client(tmp_path)

    verified = api.post("/api/datasets/fixture-dataset/verify", headers=MUTATION_HEADERS)
    assert verified.status_code == 200
    assert verified.json() == {"valid": True, "fingerprint": manifest["fingerprint"]}
    assert api.get("/api/datasets/missing").status_code == 404
    invalid = api.get("/api/datasets/bad.id")
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "invalid_identifier"


def test_run_listing_verifies_checksums_skips_corruption_and_is_json_safe(tmp_path):
    run_id, result = copy_verified_run(tmp_path)
    corrupt_id, _ = copy_verified_run(tmp_path, "corrupt-run")
    corrupt_path = tmp_path / "artifacts/runs" / corrupt_id / "result.json"
    corrupt_path.write_text(corrupt_path.read_text() + " ")
    api = client(tmp_path)

    payload = api.get("/api/runs?limit=50").json()
    assert len(payload["runs"]) == 1
    assert len(payload["warnings"]) == 1
    summary = payload["runs"][0]
    assert summary == {
        "run_id": run_id,
        "kind": result["kind"],
        "created_at": result["created_at"],
        "dataset_id": result["config"]["dataset_id"],
        "as_of": result["config"]["as_of"] or result["instance"]["as_of"],
        "n": result["config"]["n"],
        "k": result["config"]["k"],
        "seed": result["config"]["seed"],
        "methods": [row["method"] for row in result["results"]],
        "feasible_methods": [
            row["method"] for row in result["results"] if row.get("allocation_feasible")
        ],
        "cancelled": result["cancelled"],
    }
    assert_finite(payload)


def test_run_summary_requires_final_selection_and_allocation_feasibility(tmp_path):
    run_id, result = copy_verified_run(tmp_path)
    selected_only = next(row for row in result["results"] if row.get("selection_feasible"))
    selected_only["allocation_feasible"] = False
    result_path = tmp_path / "artifacts/runs" / run_id / "result.json"
    result_path.write_text(json.dumps(result, indent=2, allow_nan=False))
    result_path.with_suffix(".sha256").write_text(file_hash(result_path))

    summary = client(tmp_path).get("/api/runs").json()["runs"][0]

    assert selected_only["method"] not in summary["feasible_methods"]


def test_raw_run_missing_and_checksum_mismatch_have_distinct_statuses(tmp_path):
    run_id, _ = copy_verified_run(tmp_path)
    api = client(tmp_path)

    assert api.get("/api/runs/missing").status_code == 404
    result_path = tmp_path / "artifacts/runs" / run_id / "result.json"
    result_path.write_text(result_path.read_text() + " ")
    corrupt = api.get(f"/api/runs/{run_id}")
    assert corrupt.status_code == 409
    assert corrupt.json()["detail"]["code"] == "corrupt_run"


def test_run_listing_includes_studies_with_their_kind(tmp_path):
    run_id, result = copy_verified_run(tmp_path, kind="fixed_universe_study")

    summary = client(tmp_path).get("/api/runs").json()["runs"][0]

    assert summary["run_id"] == run_id
    assert summary["kind"] == "fixed_universe_study"
    assert summary["methods"] == [result["config"]["method"]]
    assert summary["cancelled"] is False


def test_checksum_valid_structurally_malformed_runs_are_isolated(tmp_path):
    malformed_id = "malformed-run"
    folder = tmp_path / "artifacts/runs" / malformed_id
    folder.mkdir(parents=True)
    path = folder / "result.json"
    path.write_text(json.dumps({"run_id": malformed_id}))
    path.with_suffix(".sha256").write_text(file_hash(path))
    valid_id, valid = copy_verified_run(tmp_path)
    bad_time_id, bad_time = copy_verified_run(tmp_path, "bad-time")
    bad_time["created_at"] = "not-a-timestamp"
    bad_time_path = tmp_path / "artifacts/runs" / bad_time_id / "result.json"
    bad_time_path.write_text(json.dumps(bad_time, indent=2, allow_nan=False))
    bad_time_path.with_suffix(".sha256").write_text(file_hash(bad_time_path))

    api = client(tmp_path)
    listed = api.get("/api/runs")

    assert listed.status_code == 200
    assert [record["run_id"] for record in listed.json()["runs"]] == [valid_id]
    assert len(listed.json()["warnings"]) == 2
    assert api.get(f"/api/runs/{malformed_id}").status_code == 409
    assert valid["kind"] == listed.json()["runs"][0]["kind"]


def test_export_reverifies_result_and_derives_csv_in_memory(tmp_path):
    run_id, result = copy_verified_run(tmp_path)
    folder = tmp_path / "artifacts/runs" / run_id
    (folder / "comparison.csv").write_text("stale,unverified\n")
    api = client(tmp_path)

    exported = api.get(f"/api/runs/{run_id}/export?format=csv")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    assert exported.text.startswith("method,status,objective,")
    assert "stale,unverified" not in exported.text
    json_export = api.get(f"/api/runs/{run_id}/export?format=json")
    assert json_export.status_code == 200
    assert json.loads(json_export.content) == result
    assert api.get(f"/api/runs/{run_id}/export?format=xml").status_code == 422


def valid_job_payload(seed: int = 42):
    return {
        "token": "one-click",
        "config": {"dataset_id": "fixture-dataset", "n": 4, "k": 4, "seed": seed},
    }


def test_mutations_require_local_client_json_and_allowed_browser_origin(tmp_path):
    make_dataset(tmp_path)
    api = client(tmp_path)
    path = "/api/jobs"

    assert api.post(path, json=valid_job_payload()).status_code == 403
    hostile = {**MUTATION_HEADERS, "Origin": "https://attacker.example"}
    assert api.post(path, json=valid_job_payload(), headers=hostile).status_code == 403
    allowed = {**MUTATION_HEADERS, "Origin": "http://localhost:3000"}
    assert api.post(path, json=valid_job_payload(), headers=allowed).status_code == 202
    assert api.post(path, content="x=1", headers=MUTATION_HEADERS).status_code == 415

    evil_host = TestClient(create_app(tmp_path, launch_worker=False), base_url="http://evil.example")
    rejected_host = evil_host.get("/api/health")
    assert rejected_host.status_code == 400
    assert rejected_host.json()["detail"]["code"] == "invalid_host"


def test_job_validation_rejects_invalid_config_and_ranker_paths(tmp_path):
    make_dataset(tmp_path)
    api = client(tmp_path)
    invalid = valid_job_payload()
    invalid["config"]["n"] = 3
    assert api.post("/api/jobs", json=invalid, headers=MUTATION_HEADERS).status_code == 422
    ranker = valid_job_payload()
    ranker["config"]["ranker_path"] = "/tmp/model.json"
    response = api.post("/api/jobs", json=ranker, headers=MUTATION_HEADERS)
    assert response.status_code == 422
    assert "ranker_path" in response.text
    traversal = valid_job_payload()
    traversal["config"]["dataset_id"] = "../../outside"
    assert api.post("/api/jobs", json=traversal, headers=MUTATION_HEADERS).status_code == 422


def test_job_token_is_idempotent_but_conflicting_payload_is_rejected(tmp_path):
    make_dataset(tmp_path)
    api = client(tmp_path)

    first = api.post("/api/jobs", json=valid_job_payload(), headers=MUTATION_HEADERS)
    second = api.post("/api/jobs", json=valid_job_payload(), headers=MUTATION_HEADERS)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert len(JobStore(tmp_path).list()) == 1
    conflict = api.post("/api/jobs", json=valid_job_payload(43), headers=MUTATION_HEADERS)
    assert conflict.status_code == 409
    assert len(JobStore(tmp_path).list()) == 1


def test_exact_job_replay_precedes_reverification_but_conflict_still_wins(tmp_path):
    make_dataset(tmp_path)
    api = client(tmp_path)
    first = api.post("/api/jobs", json=valid_job_payload(), headers=MUTATION_HEADERS)
    (tmp_path / "data/raw/fixture-dataset/AAA.metadata.json").write_text("tampered")

    replay = api.post("/api/jobs", json=valid_job_payload(), headers=MUTATION_HEADERS)
    conflict = api.post("/api/jobs", json=valid_job_payload(43), headers=MUTATION_HEADERS)

    assert replay.status_code == 202
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "token_conflict"


def test_job_listing_detail_cancellation_and_result_path_redaction(tmp_path):
    make_dataset(tmp_path)
    api = client(tmp_path)
    created = api.post("/api/jobs", json=valid_job_payload(), headers=MUTATION_HEADERS).json()
    job_id = created["job_id"]
    detail = api.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["events"] == []
    cancelled = api.post(f"/api/jobs/{job_id}/cancel", headers=MUTATION_HEADERS)
    assert cancelled.json() == {"job_id": job_id, "status": "cancelled", "cancel_requested": True}
    assert api.get("/api/jobs/missing").status_code == 404

    result_id, _ = copy_verified_run(tmp_path)
    store = JobStore(tmp_path)
    completed_id = store.submit(valid_job_payload()["config"], token="completed-token")
    store.finish(completed_id, "completed", str(tmp_path / "artifacts/runs" / result_id / "result.json"))
    rows = api.get("/api/jobs").json()["jobs"]
    completed = next(row for row in rows if row["id"] == completed_id)
    assert "result" not in completed
    assert completed["result_id"] == result_id


def test_job_gets_use_existing_sqlite_without_initializing_job_store(tmp_path, monkeypatch):
    store = JobStore(tmp_path)
    job_id = store.submit({"kind": "download"}, token="read-only-job")

    def reject_constructor(*args, **kwargs):
        raise AssertionError("GET must not initialize the write-capable JobStore")

    monkeypatch.setattr(JobStore, "__init__", reject_constructor)
    api = client(tmp_path)

    listed = api.get("/api/jobs")
    detail = api.get(f"/api/jobs/{job_id}")

    assert listed.status_code == 200
    assert listed.json()["jobs"][0]["id"] == job_id
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == job_id


def test_download_submission_is_idempotent(tmp_path):
    api = client(tmp_path)
    body = {"token": "refresh-data"}

    first = api.post("/api/downloads", json=body, headers=MUTATION_HEADERS)
    second = api.post("/api/downloads", json=body, headers=MUTATION_HEADERS)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert JobStore(tmp_path).list()[0]["config"] == {"kind": "download"}
