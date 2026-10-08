"""Explicit import of genuine provider exports with required provenance.

An import records what a supplied source says; it does not certify authenticity
from a filename alone. No fabricated or replacement observations are generated.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import uuid

import pandas as pd

from qcompass.data.snapshots import file_hash, manifest_hash
from qcompass.data.sources import normalize_history
from qcompass.data.validation import DataQualityError, parse_constituents, validate_prices
from qcompass.paths import project_root


def import_bundle(bundle, root=None):
    bundle = Path(bundle).resolve()
    root = root or project_root()
    try:
        provenance = json.loads((bundle / "provenance.json").read_text())
        required = {
            "provider",
            "source_url",
            "retrieved_at",
            "membership_observed_at",
            "currency",
            "exchange",
            "adjustment_convention",
            "files",
        }
        if not required.issubset(provenance) or not all(provenance[k] for k in required):
            raise DataQualityError("Incomplete source provenance")
        if provenance["currency"] != "INR" or provenance["exchange"] != "NSE":
            raise DataQualityError("Require INR NSE stock records")
        members = parse_constituents((bundle / "constituents.csv").read_bytes())
        prices, audits = [], []
        for symbol, source in provenance["files"].items():
            if symbol not in members.symbol.values or Path(source).name != source:
                raise DataQualityError("Unknown constituent or unsafe source path")
            table = pd.read_csv(bundle / source, index_col=0)
            table.index = pd.to_datetime(table.index, utc=True).tz_convert("Asia/Kolkata")
            normalized = normalize_history(table, symbol)
            prices.append(normalized)
            audits.append({"symbol": symbol, **validate_prices(normalized)})
    except (OSError, ValueError, KeyError) as exc:
        raise DataQualityError(f"Source bundle rejected: {exc}") from exc
    if not prices:
        raise DataQualityError("No attributable stock histories")
    combined = pd.concat(prices, ignore_index=True).sort_values(["symbol", "date"])
    stamp = datetime.now(timezone.utc)
    dataset_id = f"import-{stamp:%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    raw, processed = root / "data/raw" / dataset_id, root / "data/processed" / dataset_id
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    for name in ["provenance.json", "constituents.csv", *provenance["files"].values()]:
        shutil.copy2(bundle / name, raw / name)
    members.to_parquet(processed / "constituents.parquet", index=False)
    combined.to_parquet(processed / "prices.parquet", index=False)
    manifest = {
        "schema_version": 2,
        "dataset_id": dataset_id,
        "retrieved_at": stamp.isoformat(),
        "universe": "NIFTY 50",
        "membership_mode": "current_snapshot",
        "membership_source": provenance["source_url"],
        "membership_observed_at": provenance["membership_observed_at"],
        "historical_membership_verified": False,
        "corporate_actions_independently_verified": False,
        "price_source": provenance["provider"]
        + " (supplied export; attribution recorded, independently unverified)",
        "source_records": [provenance],
        "first_date": min(combined.date),
        "last_date": max(combined.date),
        "stock_count": len(prices),
        "row_count": len(combined),
        "audits": audits,
        "failures": [],
        "sessions": sorted(combined.date.unique()),
        "calendar_source": "Union of supplied stock sessions; not independently complete",
        "crosscheck": {"status": "unavailable", "date": max(combined.date), "matches": [], "mismatches": []},
        "adjustment_convention": provenance["adjustment_convention"],
        "usage": "Local research; source redistribution rights must be checked",
    }
    manifest["files"] = {
        str(p.relative_to(root)): file_hash(p)
        for directory in [raw, processed]
        for p in sorted(directory.iterdir())
    }
    manifest["fingerprint"] = manifest_hash(manifest)
    dest = root / "data/manifests"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{dataset_id}.json").write_text(json.dumps(manifest, indent=2))
    return manifest
