"""Immutable local datasets: provenance, content hashes and explicit coverage."""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid
import ast

import pandas as pd

from qcompass.data.validation import DataQualityError
from qcompass.paths import project_root


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_files(root: Path, files: dict[str, str]) -> None:
    for relative, expected in files.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or file_hash(path) != expected:
            raise DataQualityError(f"Missing or modified source: {relative}")


def manifest_hash(manifest):
    material = {k: v for k, v in manifest.items() if k != "fingerprint"}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def verify_manifest(manifest):
    if manifest.get("schema_version") != 2:
        raise DataQualityError("Legacy manifest lacks metadata integrity; seal as a new snapshot first")
    if manifest.get("fingerprint") != manifest_hash(manifest):
        raise DataQualityError("Dataset metadata fingerprint mismatch")


def list_snapshots(root: Path | None = None) -> list[dict]:
    root = root or project_root()
    manifests = root / "data/manifests"
    records = [json.loads(p.read_text()) for p in sorted(manifests.glob("*.json"), reverse=True)]

    def version_time(record):
        value = record.get("reprocessed_at") or record.get("metadata_sealed_at") or record.get("retrieved_at")
        try:
            parsed = datetime.fromisoformat(value)
            return (
                parsed.replace(tzinfo=timezone.utc)
                if parsed.tzinfo is None
                else parsed.astimezone(timezone.utc)
            )
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    return sorted([r for r in records if r.get("schema_version") == 2], key=version_time, reverse=True)


def load_snapshot(dataset_id: str, root: Path | None = None, verify: bool = True):
    root = root or project_root()
    if Path(dataset_id).name != dataset_id:
        raise DataQualityError("Invalid snapshot identifier")
    manifest = json.loads((root / "data/manifests" / f"{dataset_id}.json").read_text())
    verify_manifest(manifest)
    if manifest["dataset_id"] != dataset_id:
        raise DataQualityError("Dataset identifier mismatch")
    if verify:
        verify_files(root, manifest["files"])
    folder = (root / manifest.get("processed_directory", f"data/processed/{dataset_id}")).resolve()
    if not folder.is_relative_to(root.resolve() / "data/processed"):
        raise DataQualityError("Invalid processed directory")
    for name in ["constituents.parquet", "prices.parquet"]:
        if str((folder / name).relative_to(root.resolve())) not in manifest["files"]:
            raise DataQualityError("Processed records must be covered by the manifest")
    return (
        manifest,
        pd.read_parquet(folder / "constituents.parquet"),
        pd.read_parquet(folder / "prices.parquet"),
    )


def seal_legacy_snapshot(dataset_id, root=None):
    """Bind observed metadata in a NEW version. Original files remain unchanged.

    Adds integrity from seal time forward, not a retroactive guarantee for older
    manifests. Intended only for explicitly migrating the first development snapshot.
    """
    root = root or project_root()
    if Path(dataset_id).name != dataset_id:
        raise DataQualityError("Invalid dataset identifier")
    source = root / "data/manifests" / f"{dataset_id}.json"
    manifest = json.loads(source.read_text())
    verify_files(root, manifest["files"])
    new_id = dataset_id + "-sealed-" + uuid.uuid4().hex[:6]
    manifest.update(
        schema_version=2,
        dataset_id=new_id,
        parent_dataset=dataset_id,
        processed_directory=f"data/processed/{dataset_id}",
        metadata_sealed_at=datetime.now(timezone.utc).isoformat(),
        metadata_integrity_scope="From seal time forward; original source files unchanged",
    )
    manifest["files"][str(source.relative_to(root))] = file_hash(source)
    manifest["fingerprint"] = manifest_hash(manifest)
    (root / "data/manifests" / f"{new_id}.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def reprocess_snapshot(dataset_id, root=None):
    """Create a new version from verified original CSVs, retaining all valid dated rows.

    Source bytes, prior processed files and prior metadata are never changed or
    copied. The new manifest references them with hashes and explicit lineage.
    """
    from qcompass.data.sources import normalize_history
    from qcompass.data.validation import partition_prices

    root = Path(root or project_root()).resolve()
    parent, members, _ = load_snapshot(dataset_id, root, verify=True)
    source_manifest = root / "data/manifests" / f"{dataset_id}.json"
    source_paths = {Path(name).name: name for name in parent["files"] if name.startswith("data/raw/")}
    old_records = {r["symbol"]: r for r in parent.get("source_records", [])}
    prices, quarantined, audits, failures, records = [], [], [], [], []
    for row in members.itertuples():
        symbol = row.symbol
        try:
            relative = source_paths.get(f"{symbol}.csv")
            metadata_relative = source_paths.get(f"{symbol}.metadata.json")
            if relative is None or metadata_relative is None:
                raise DataQualityError("Original provider CSV or source metadata unavailable")
            metadata = provider_identity(json.loads((root / metadata_relative).read_text()))
            if metadata.get("currency") != "INR" or metadata.get("exchangeName") not in ("NSI", "NSE"):
                raise DataQualityError("Original provider exchange/currency could not be verified")
            frame = pd.read_csv(root / relative, index_col=0)
            normalized = normalize_history(frame, symbol, validate=False)
            valid, bad, audit = partition_prices(normalized)
            audit.update(symbol=symbol, raw_source=relative, raw_source_sha256=parent["files"][relative])
            audits.append(audit)
            if not valid.empty:
                prices.append(valid)
            if not bad.empty:
                quarantined.append(bad)
            record = dict(
                old_records.get(
                    symbol,
                    dict(
                        symbol=symbol,
                        provider="Yahoo Finance via yfinance",
                        url=f"https://finance.yahoo.com/quote/{symbol}.NS/history/",
                        query=dict(
                            start=parent["requested_start"],
                            end_exclusive=parent["end_exclusive"],
                            auto_adjust=False,
                            repair=False,
                        ),
                        currency="INR",
                        exchange="NSE",
                    ),
                )
            )
            record.update(
                raw_source=relative,
                raw_source_sha256=parent["files"][relative],
                source_metadata=metadata_relative,
                source_metadata_sha256=parent["files"][metadata_relative],
            )
            records.append(record)
        except Exception as exc:
            failures.append(dict(symbol=symbol, error=f"{type(exc).__name__}: {exc}"))
    if not prices:
        raise DataQualityError(f"No valid original provider rows could be reprocessed: {failures}")
    combined = pd.concat(prices, ignore_index=True).sort_values(["symbol", "date"])
    new_id = dataset_id + "-reprocessed-" + uuid.uuid4().hex[:6]
    processed = root / "data/processed" / new_id
    processed.mkdir(parents=True, exist_ok=False)
    members.to_parquet(processed / "constituents.parquet", index=False)
    combined.to_parquet(processed / "prices.parquet", index=False)
    if quarantined:
        pd.concat(quarantined, ignore_index=True).to_parquet(processed / "quarantined.parquet", index=False)
    manifest = dict(parent)
    manifest.update(
        schema_version=2,
        dataset_id=new_id,
        parent_dataset=dataset_id,
        parent_fingerprint=parent["fingerprint"],
        parent_manifest_sha256=file_hash(source_manifest),
        processed_directory=str(processed.relative_to(root)),
        reprocessed_at=datetime.now(timezone.utc).isoformat(),
        processing_policy="dated-row-quarantine-v1; valid genuine history retained; no interpolation",
        parent_failures=parent.get("failures", []),
        failures=failures,
        source_failures=failures,
        source_records=records,
        audits=audits,
        stock_count=int(combined.symbol.nunique()),
        row_count=len(combined),
        first_date=min(combined.date),
        last_date=max(combined.date),
        quarantined_row_count=sum(a["quarantined_count"] for a in audits),
        quarantined_symbols=[a["symbol"] for a in audits if a["quarantined_count"]],
        raw_storage_policy="References verified parent source files; original bytes unchanged",
    )
    manifest["files"] = dict(parent["files"])
    manifest["files"][str(source_manifest.relative_to(root))] = file_hash(source_manifest)
    for path in sorted(processed.iterdir()):
        manifest["files"][str(path.relative_to(root))] = file_hash(path)
    manifest["fingerprint"] = manifest_hash(manifest)
    (root / "data/manifests" / f"{new_id}.json").write_text(json.dumps(manifest, indent=2, allow_nan=False))
    # Ensure the just-written version satisfies the same immutable-loader contract.
    load_snapshot(new_id, root, verify=True)
    return manifest


def provider_identity(metadata):
    """Extract only scalar identity fields from structured or legacy repr metadata.

    The first snapshot stored a provider mapping's repr as a JSON string. Its
    Timestamp(...) nodes are deliberately never evaluated. Only literal currency
    and exchange values from the top-level dictionary are inspected.
    """
    keys = {"currency", "exchangeName"}
    if isinstance(metadata, dict):
        return {key: metadata.get(key) for key in keys}
    if not isinstance(metadata, str):
        raise DataQualityError("Invalid provider metadata representation")
    try:
        node = ast.parse(metadata, mode="eval").body
        if not isinstance(node, ast.Dict):
            raise ValueError("Expected a literal top-level provider mapping")
        result = {}
        for key, value in zip(node.keys, node.values):
            literal_key = ast.literal_eval(key)
            if literal_key in keys:
                result[literal_key] = ast.literal_eval(value)
        return result
    except (SyntaxError, TypeError, ValueError) as exc:
        raise DataQualityError("Invalid provider metadata representation") from exc
