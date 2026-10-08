"""Dated quarantine checks on actual frozen Yahoo records, never synthetic histories."""

import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def actual_history():
    from qcompass.data.snapshots import load_snapshot

    dataset_id = "nifty50-20260905T080605-28fd98-sealed-0d14f0"
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/manifests" / f"{dataset_id}.json").exists():
        pytest.skip("Verified original snapshot required; no substitute price data.")
    manifest, _, _ = load_snapshot(dataset_id, root)
    path = next(root / name for name in manifest["files"] if name.endswith("/LT.csv"))
    return manifest, pd.read_csv(path, index_col=0)


def test_one_bad_future_quote_retains_genuine_history_and_raw_unchanged(actual_history):
    from qcompass.data.sources import normalize_history
    from qcompass.data.validation import partition_prices

    _, raw = actual_history
    original = raw.copy(deep=True)
    normalized = normalize_history(raw, "LT", validate=False)
    valid, bad, audit = partition_prices(normalized)
    assert len(valid) == len(raw) - 1
    assert bad.date.tolist() == ["2026-09-04"]
    assert audit["quarantined_count"] == 1
    assert audit["quarantined_rows"][0]["reasons"]
    assert valid["close"].notna().all()
    pd.testing.assert_frame_equal(raw, original)


def test_future_bad_rows_do_not_change_past_window_and_current_still_blocks(actual_history):
    from qcompass.data.sources import normalize_history
    from qcompass.data.validation import partition_prices, DataQualityError
    from qcompass.data.prepare import aligned_window

    manifest, raw = actual_history
    original = normalize_history(raw, "LT", validate=False)
    altered = original.copy()
    altered.loc[altered.date.eq("2026-09-04"), "close"] = -1  # corruption test, never a reported history
    variants = [original, altered, original[original.date.ne("2026-09-04")]]
    windows = []
    for rows in variants:
        valid, _, _ = partition_prices(rows)
        windows.append(aligned_window(valid, ["LT"], manifest["sessions"], "2025-09-04"))
        with pytest.raises(DataQualityError, match="Missing session prices"):
            aligned_window(valid, ["LT"], manifest["sessions"], "2026-09-04")
    pd.testing.assert_frame_equal(windows[0], windows[1])
    pd.testing.assert_frame_equal(windows[0], windows[2])


def test_duplicate_keys_all_quarantined_and_all_row_errors_audited(actual_history):
    from qcompass.data.sources import normalize_history
    from qcompass.data.validation import partition_prices

    _, raw = actual_history
    rows = normalize_history(raw.iloc[-4:-1], "LT")
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    rows.loc[1, "high"] = rows.loc[1, "low"] - 1
    rows.loc[1, "volume"] = -1
    valid, bad, audit = partition_prices(rows)
    assert len(valid) == 1 and len(bad) == 3
    assert audit["quarantined_count"] == 3
    duplicate = [r for r in audit["quarantined_rows"] if "duplicate_symbol_date" in r["reasons"]]
    assert len(duplicate) == 2
    corrupt = next(r for r in audit["quarantined_rows"] if r["source_row"] == 1)
    assert "invalid_ohlc_high" in corrupt["reasons"] and "negative_volume" in corrupt["reasons"]


def test_reprocess_rejects_unsealed_or_tampered_manifest(tmp_path):
    from qcompass.data.snapshots import reprocess_snapshot, manifest_hash
    from qcompass.data.validation import DataQualityError

    folder = tmp_path / "data/manifests"
    folder.mkdir(parents=True)
    source = folder / "test.json"
    source.write_text(json.dumps({"schema_version": 1, "dataset_id": "test", "files": {}}))
    with pytest.raises(DataQualityError):
        reprocess_snapshot("test", root=tmp_path)
    manifest = dict(schema_version=2, dataset_id="test", files={})
    manifest["fingerprint"] = manifest_hash(manifest)
    manifest["stock_count"] = 50
    source.write_text(json.dumps(manifest))
    with pytest.raises(DataQualityError, match="fingerprint"):
        reprocess_snapshot("test", root=tmp_path)


def test_legacy_source_metadata_repr_is_read_without_execution(actual_history):
    from qcompass.data.snapshots import provider_identity

    manifest, _ = actual_history
    root = Path(__file__).resolve().parents[1]
    path = next(root / name for name in manifest["files"] if name.endswith("/LT.metadata.json"))
    metadata = json.loads(path.read_text())
    assert provider_identity(metadata) == {"currency": "INR", "exchangeName": "NSI"}
    # Arbitrary expression strings are not executed as metadata.
    with pytest.raises(ValueError):
        provider_identity("__import__('os').getcwd()")


def test_snapshots_order_by_version_time_not_filename(tmp_path):
    from qcompass.data.snapshots import list_snapshots

    folder = tmp_path / "data/manifests"
    folder.mkdir(parents=True)
    parent = dict(
        schema_version=2,
        dataset_id="snapshot",
        retrieved_at="2026-09-01T00:00:00+00:00",
        metadata_sealed_at="2026-09-02T00:00:00+00:00",
    )
    child = dict(parent, dataset_id="snapshot-reprocessed-abc", reprocessed_at="2026-09-03T00:00:00+00:00")
    (folder / "snapshot.json").write_text(json.dumps(parent))
    (folder / "snapshot-reprocessed-abc.json").write_text(json.dumps(child))
    assert [m["dataset_id"] for m in list_snapshots(tmp_path)] == ["snapshot-reprocessed-abc", "snapshot"]


def test_empty_source_is_a_failure_not_an_unaudited_history(actual_history):
    from qcompass.data.sources import normalize_history
    from qcompass.data.validation import DataQualityError

    _, raw = actual_history
    with pytest.raises(DataQualityError):
        normalize_history(raw.iloc[:0], "LT", validate=False)
