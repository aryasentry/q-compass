"""Data validation regressions use original exchange records, never invented prices."""

from pathlib import Path

import pandas as pd
import pytest

from qcompass.data.validation import DataQualityError, parse_constituents, validate_prices
from qcompass.data.snapshots import file_hash, verify_files


def test_official_constituents_have_unique_identifiers():
    source = Path("data/raw/bootstrap/ind_nifty50list.csv")
    if not source.exists():
        pytest.skip("Run the documented official constituent download first")
    records = parse_constituents(source.read_bytes())
    assert len(records) == 50
    assert records["isin"].is_unique
    assert records["symbol"].is_unique
    assert records["sector"].notna().all()
    # A duplicate identity must be rejected, not counted as another stock.
    original = pd.read_csv(source)
    duplicated = pd.concat([original, original.iloc[[0]]]).to_csv(index=False).encode()
    with pytest.raises(DataQualityError):
        parse_constituents(duplicated)


def test_changed_file_fails_integrity_check(tmp_path):
    target = tmp_path / "record.csv"
    target.write_bytes(b"authentic-source-file-test-integrity")
    expected = {"record.csv": file_hash(target)}
    verify_files(tmp_path, expected)
    target.write_bytes(b"altered")
    with pytest.raises(DataQualityError):
        verify_files(tmp_path, expected)


def test_real_prices_reject_duplicate_and_invalid_records():
    from qcompass.data.snapshots import list_snapshots, load_snapshot

    snapshots = list_snapshots()
    if not snapshots:
        pytest.skip("Download genuine price snapshot first")
    _, _, source = load_snapshot(snapshots[0]["dataset_id"])
    prices = source[source.symbol.eq("RELIANCE")].copy()
    assert validate_prices(prices)["rows"] > 252
    with pytest.raises(DataQualityError):
        validate_prices(pd.concat([prices, prices.iloc[[0]]]))
    bad = prices.copy()
    bad.loc[bad.index[0], "adj_close"] = -1
    with pytest.raises(DataQualityError):
        validate_prices(bad)


def test_import_refuses_unattributed_or_missing_market_files(tmp_path):
    from qcompass.data.importer import import_bundle

    with pytest.raises(DataQualityError):
        import_bundle(tmp_path, root=tmp_path)


def test_manifest_digest_binds_time_and_validation_metadata():
    from qcompass.data.snapshots import manifest_hash, verify_manifest

    value = {
        "schema_version": 2,
        "dataset_id": "unit-metadata",
        "sessions": ["2020-01-01"],
        "crosscheck": {"mismatches": []},
        "files": {"source.csv": "digest"},
    }
    value["fingerprint"] = manifest_hash(value)
    verify_manifest(value)
    value["sessions"] = ["2030-01-01"]
    with pytest.raises(DataQualityError):
        verify_manifest(value)
