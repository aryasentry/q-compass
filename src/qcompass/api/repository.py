"""Read-only artifact views and narrowly-scoped queue mutations for the API."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from filelock import FileLock
import pandas as pd

from qcompass.data.snapshots import load_snapshot, verify_manifest
from qcompass.experiments.runner import comparison_table, read_result
from qcompass.experiments.store import JobStore


class ResourceNotFound(Exception):
    """A requested local artifact does not exist."""


class CorruptResource(Exception):
    """A local artifact failed integrity or structural validation."""


class TokenConflict(Exception):
    """An idempotency token was reused for a different request."""


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")
FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc


def _identifier_value(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} has an invalid format")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}")
    return value


def _finite(value: Any, *, reject_nonfinite: bool = False) -> Any:
    """Reject non-standard JSON numbers and normalize common dataframe scalars."""
    if isinstance(value, float) and not math.isfinite(value):
        if reject_nonfinite:
            raise ValueError("Non-finite number in saved artifact")
        return None
    if isinstance(value, dict):
        return {
            str(key): _finite(nested, reject_nonfinite=reject_nonfinite)
            for key, nested in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_finite(nested, reject_nonfinite=reject_nonfinite) for nested in value]
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return _finite(converted, reject_nonfinite=reject_nonfinite)
    if not isinstance(value, (str, bytes, dict, list, tuple)) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return value


def _warning(path: Path, exc: Exception) -> str:
    return f"{path.name}: {type(exc).__name__}: {exc}"


class LocalRepository:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def list_datasets(self) -> tuple[list[dict], list[str]]:
        records, warnings = [], []
        for path in sorted((self.root / "data/manifests").glob("*.json"), reverse=True):
            try:
                manifest = json.loads(path.read_text())
                verify_manifest(manifest)
                dataset_id = _identifier_value(manifest.get("dataset_id"), "dataset_id")
                if dataset_id != path.stem:
                    raise ValueError("Dataset identifier does not match manifest filename")
                first_date = _date(manifest.get("first_date"), "first_date")
                last_date = _date(manifest.get("last_date"), "last_date")
                if first_date > last_date:
                    raise ValueError("Dataset date range is reversed")
                stock_count = _integer(manifest.get("stock_count"), "stock_count")
                row_count = _integer(manifest.get("row_count"), "row_count")
                fingerprint = manifest.get("fingerprint")
                if not isinstance(fingerprint, str) or not FINGERPRINT.fullmatch(fingerprint):
                    raise ValueError("fingerprint must be a SHA-256 digest")
                retrieved_at = manifest.get("retrieved_at")
                _timestamp(retrieved_at, "retrieved_at")
                crosscheck = manifest.get("crosscheck")
                if not isinstance(crosscheck, dict):
                    raise ValueError("crosscheck must be an object")
                quarantined_count = manifest.get("quarantined_row_count")
                if quarantined_count is None:
                    audits = manifest.get("audits", [])
                    if not isinstance(audits, list) or not all(isinstance(audit, dict) for audit in audits):
                        raise ValueError("audits must be an array of objects")
                    quarantined_count = sum(
                        _integer(audit.get("quarantined_count", 0), "audit quarantined_count")
                        for audit in audits
                    )
                quarantined_count = _integer(quarantined_count, "quarantined_count")
                summary = {
                    "dataset_id": dataset_id,
                    "first_date": manifest["first_date"],
                    "last_date": manifest["last_date"],
                    "stock_count": stock_count,
                    "row_count": row_count,
                    "fingerprint": fingerprint,
                    "quarantined_count": quarantined_count,
                    "retrieved_at": retrieved_at,
                    "crosscheck": crosscheck,
                }
                version_value = (
                    manifest.get("reprocessed_at")
                    or manifest.get("metadata_sealed_at")
                    or retrieved_at
                )
                version_time = _timestamp(version_value, "snapshot version timestamp")
                records.append((version_time, summary))
            except Exception as exc:
                warnings.append(_warning(path, exc))
        records.sort(key=lambda record: record[0], reverse=True)
        return _finite([summary for _, summary in records]), warnings

    def dataset(self, dataset_id: str) -> dict:
        manifest_path = self.root / "data/manifests" / f"{dataset_id}.json"
        if not manifest_path.is_file():
            raise ResourceNotFound("Dataset not found")
        try:
            manifest, constituents, _ = load_snapshot(dataset_id, self.root, verify=True)
            rows = []
            for record in constituents.to_dict(orient="records"):
                row = {
                    key: record.get(key)
                    for key in ("symbol", "company", "sector", "isin")
                    if key != "company" or record.get(key) is not None
                }
                rows.append(_finite(row))
            folder = (self.root / manifest.get("processed_directory", f"data/processed/{dataset_id}")).resolve()
            quarantine_path = folder / "quarantined.parquet"
            relative = str(quarantine_path.relative_to(self.root))
            quarantine = []
            if relative in manifest["files"] and quarantine_path.is_file():
                quarantine = [_finite(row) for row in pd.read_parquet(quarantine_path).head(100).to_dict("records")]
            count = int(
                manifest.get(
                    "quarantined_row_count",
                    sum(int(audit.get("quarantined_count", 0)) for audit in manifest.get("audits", [])),
                )
            )
            return {
                "manifest": _finite(manifest),
                "constituents": rows,
                "quarantine": quarantine,
                "quarantine_count": count,
            }
        except ResourceNotFound:
            raise
        except Exception as exc:
            raise CorruptResource(str(exc)) from exc

    def verify_dataset(self, dataset_id: str) -> dict:
        detail = self.dataset(dataset_id)
        return {"valid": True, "fingerprint": detail["manifest"]["fingerprint"]}

    def _read_run(self, run_id: str) -> dict:
        path = self.root / "artifacts/runs" / run_id / "result.json"
        if not path.is_file():
            raise ResourceNotFound("Run not found")
        try:
            result = read_result(path)
            if not isinstance(result, dict) or result.get("run_id") != run_id:
                raise ValueError("Run identifier does not match its folder")
            result = _finite(result, reject_nonfinite=True)
            self._validate_run(result)
            return result
        except Exception as exc:
            raise CorruptResource(str(exc)) from exc

    @staticmethod
    def _validate_run(result: dict) -> None:
        if result.get("schema_version") != 1:
            raise ValueError("Unsupported run schema version")
        _identifier_value(result.get("run_id"), "run_id")
        _timestamp(result.get("created_at"), "created_at")
        fingerprint = result.get("dataset_fingerprint")
        if not isinstance(fingerprint, str) or not FINGERPRINT.fullmatch(fingerprint):
            raise ValueError("dataset_fingerprint must be a SHA-256 digest")
        config = result.get("config")
        if not isinstance(config, dict):
            raise ValueError("Run config must be an object")
        _identifier_value(config.get("dataset_id"), "config.dataset_id")
        for field in ("n", "k", "seed"):
            _integer(config.get(field), f"config.{field}")
        kind = result.get("kind")
        if kind == "optimization_comparison":
            if not isinstance(result.get("instance"), dict):
                raise ValueError("Optimization instance must be an object")
            rows = result.get("results")
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise ValueError("Optimization results must be an array of objects")
            for row in rows:
                if not isinstance(row.get("method"), str) or not row["method"]:
                    raise ValueError("Every optimization result requires a method")
                for field in ("selection_feasible", "allocation_feasible"):
                    if row.get(field) is not None and type(row[field]) is not bool:
                        raise ValueError(f"Result {field} must be boolean or null")
            if type(result.get("cancelled")) is not bool:
                raise ValueError("Optimization cancelled must be boolean")
            as_of = config.get("as_of") or result["instance"].get("as_of")
            if as_of is not None:
                _date(as_of, "as_of")
        elif kind == "fixed_universe_study":
            if not isinstance(config.get("method"), str) or not config["method"]:
                raise ValueError("Study method is required")
            start = _date(config.get("start"), "config.start")
            end = _date(config.get("end"), "config.end")
            if start > end:
                raise ValueError("Study date range is reversed")
            if not isinstance(result.get("decisions"), list):
                raise ValueError("Study decisions must be an array")
            if not isinstance(result.get("cost_sensitivity"), dict):
                raise ValueError("Study cost_sensitivity must be an object")
        else:
            raise ValueError("Unsupported run kind")

    def run(self, run_id: str) -> dict:
        return self._read_run(run_id)

    @staticmethod
    def _run_summary(result: dict) -> dict:
        config = result.get("config") or {}
        rows = result.get("results") or []
        methods = [row.get("method") for row in rows if row.get("method")]
        feasible = [
            row["method"]
            for row in rows
            if row.get("method")
            and row.get("selection_feasible") is True
            and row.get("allocation_feasible") is True
        ]
        if not methods and config.get("method"):
            methods = [config["method"]]
            feasible = methods
        instance = result.get("instance") or {}
        return {
            "run_id": result["run_id"],
            "kind": result.get("kind", "optimization_comparison"),
            "created_at": result.get("created_at"),
            "dataset_id": config.get("dataset_id"),
            "as_of": config.get("as_of") or instance.get("as_of") or config.get("start"),
            "n": config.get("n") or (len(instance.get("symbols", [])) or None),
            "k": config.get("k"),
            "seed": config.get("seed"),
            "methods": methods,
            "feasible_methods": feasible,
            "cancelled": bool(result.get("cancelled", False)),
        }

    def list_runs(self, limit: int) -> tuple[list[dict], list[str]]:
        records, warnings = [], []
        for path in sorted((self.root / "artifacts/runs").glob("*/result.json")):
            try:
                records.append(self._run_summary(self._read_run(path.parent.name)))
            except Exception as exc:
                warnings.append(_warning(path.parent, exc))
        records.sort(key=lambda record: record.get("created_at") or "", reverse=True)
        return _finite(records[:limit]), warnings

    def export_run(self, run_id: str, export_format: str) -> tuple[bytes, str, str]:
        result = self._read_run(run_id)
        if export_format == "json":
            body = json.dumps(result, indent=2, allow_nan=False).encode()
            return body, "application/json", f"{run_id}.json"
        table = comparison_table(result)
        if table.empty:
            raise CorruptResource("CSV export requires an optimization comparison")
        body = table.to_csv(index=False).encode()
        return body, "text/csv; charset=utf-8", f"{run_id}-comparison.csv"

    def _jobs_read_connection(self) -> sqlite3.Connection | None:
        path = self.root / "artifacts/jobs.sqlite"
        if not path.is_file():
            return None
        database = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=15)
        database.row_factory = sqlite3.Row
        return database

    @staticmethod
    def _decode_job(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        job = dict(row)
        config = json.loads(job["config"])
        if not isinstance(config, dict):
            raise ValueError("Job config must be an object")
        job["config"] = config
        return job

    def _job_view(self, job: dict) -> dict:
        view = dict(job)
        result = view.pop("result", None)
        view["cancel_requested"] = bool(view.get("cancel_requested"))
        config = view.get("config") or {}
        if result and view.get("status") == "completed" and config.get("kind", "experiment") == "experiment":
            path = Path(result)
            expected_parent = (self.root / "artifacts/runs").resolve()
            try:
                resolved = path.resolve()
                if resolved.name == "result.json" and resolved.parent.parent == expected_parent:
                    view["result_id"] = resolved.parent.name
            except OSError:
                pass
        return _finite(view)

    def list_jobs(self) -> list[dict]:
        database = self._jobs_read_connection()
        if database is None:
            return []
        try:
            rows = database.execute("SELECT * FROM jobs ORDER BY created DESC").fetchall()
            return [self._job_view(self._decode_job(row)) for row in rows]
        except (sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
            raise CorruptResource(str(exc)) from exc
        finally:
            database.close()

    def job(self, job_id: str) -> tuple[dict, list[dict]]:
        database = self._jobs_read_connection()
        if database is None:
            raise ResourceNotFound("Job not found")
        try:
            job = self._decode_job(database.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
            if job is None:
                raise ResourceNotFound("Job not found")
            events = [
                dict(row)
                for row in database.execute("SELECT * FROM events WHERE job_id=? ORDER BY id", (job_id,))
            ]
            return self._job_view(job), _finite(events)
        except ResourceNotFound:
            raise
        except (sqlite3.Error, ValueError, json.JSONDecodeError) as exc:
            raise CorruptResource(str(exc)) from exc
        finally:
            database.close()

    def _submit(self, config: dict, token: str, verify_new=None) -> tuple[str, bool]:
        folder = self.root / "artifacts"
        folder.mkdir(parents=True, exist_ok=True)
        with FileLock(folder / "submission.lock"):
            store = JobStore(self.root)
            with store.connect() as database:
                row = database.execute("SELECT id,config FROM jobs WHERE token=?", (token,)).fetchone()
            if row is not None:
                previous = json.loads(row["config"])
                if previous != config:
                    raise TokenConflict("Idempotency token was already used with a different payload")
                return row["id"], False
            if verify_new is not None:
                verify_new()
            return store.submit(config, token=token), True

    def submit_experiment(self, config: dict, token: str) -> tuple[str, bool]:
        def verify_new():
            dataset_id = config["dataset_id"]
            manifest_path = self.root / "data/manifests" / f"{dataset_id}.json"
            if not manifest_path.is_file():
                raise ResourceNotFound("Dataset not found")
            try:
                load_snapshot(dataset_id, self.root, verify=True)
            except Exception as exc:
                raise CorruptResource(str(exc)) from exc

        return self._submit(config, token, verify_new)

    def submit_download(self, token: str) -> tuple[str, bool]:
        return self._submit({"kind": "download"}, token)

    def cancel_job(self, job_id: str) -> dict:
        path = self.root / "artifacts/jobs.sqlite"
        store = JobStore(self.root) if path.is_file() else None
        job = store.get(job_id) if store is not None else None
        if job is None:
            raise ResourceNotFound("Job not found")
        store.cancel(job_id)
        updated = store.get(job_id)
        return {
            "job_id": job_id,
            "status": updated["status"],
            "cancel_requested": bool(updated["cancel_requested"]),
        }
