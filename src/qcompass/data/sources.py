"""Source acquisition. Provider errors are recorded, never converted to prices."""

from datetime import datetime, timedelta
from io import BytesIO
import json
import time
import uuid
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import yfinance as yf

from qcompass.data.snapshots import file_hash, manifest_hash
from qcompass.data.validation import DataQualityError, parse_constituents, validate_prices, partition_prices
from qcompass.paths import project_root

CONSTITUENTS_URL = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"


def daily_cutoff() -> str:
    # Exclusive end date. Never collect an in-progress Indian session.
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return (now.date() + timedelta(days=1) if now.hour >= 19 else now.date()).isoformat()


def normalize_history(frame: pd.DataFrame, symbol: str, validate: bool = True) -> pd.DataFrame:
    required = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
    if frame.empty or not set(required).issubset(frame.columns):
        raise DataQualityError(f"{symbol}: provider omitted prices or actions")
    data = frame[required].copy()
    data.columns = ["open", "high", "low", "close", "adj_close", "volume", "dividends", "splits"]
    data.insert(0, "symbol", symbol)

    def trading_date(value):
        try:
            return str(pd.Timestamp(value).date())
        except (TypeError, ValueError):
            return str(value)

    data.insert(0, "date", [trading_date(x) for x in frame.index])
    data = data.reset_index(drop=True)
    if validate:
        validate_prices(data)
    return data


def fetch_snapshot(start="2019-01-01", end=None, root=None, progress=print, cancel=None) -> dict:
    root = root or project_root()
    end = end or daily_cutoff()
    stamp = datetime.now(ZoneInfo("UTC"))
    dataset_id = "nifty50-" + stamp.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    raw = root / "data/raw" / dataset_id
    processed = root / "data/processed" / dataset_id
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    with httpx.Client(timeout=25, follow_redirects=True) as client:
        response = client.get(CONSTITUENTS_URL)
        response.raise_for_status()
    (raw / "constituents.csv").write_bytes(response.content)
    members = parse_constituents(response.content)
    members.to_parquet(processed / "constituents.parquet", index=False)
    yf.set_tz_cache_location(str(root / ".tools/yfinance"))
    prices, audits, failures, sources, quarantined = [], [], [], [], []
    progress("Official 50-stock membership downloaded. Fetching real daily prices.")
    for i, row in members.iterrows():
        if cancel and cancel():
            raise InterruptedError(
                "Download cancelled; partial original files are retained but not an experiment snapshot"
            )
        symbol = row.symbol
        try:
            ticker = yf.Ticker(symbol + ".NS")
            frame = ticker.history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
                back_adjust=False,
                repair=False,
                actions=True,
                keepna=True,
                raise_errors=True,
                timeout=20,
            )
            # Keep the provider-returned table before normalization, including original labels/index.
            frame.to_csv(raw / f"{symbol}.csv")
            meta = dict(ticker.history_metadata)
            (raw / f"{symbol}.metadata.json").write_text(json.dumps(meta, default=str, indent=2))
            if meta.get("currency") != "INR" or meta.get("exchangeName") not in {"NSI", "NSE"}:
                raise DataQualityError(
                    f"Unexpected exchange/currency: {meta.get('exchangeName')}/{meta.get('currency')}"
                )
            normalized, bad, audit = partition_prices(normalize_history(frame, symbol, validate=False))
            audit["symbol"] = symbol
            audits.append(audit)
            if not normalized.empty:
                prices.append(normalized)
            if not bad.empty:
                quarantined.append(bad)
            sources.append(
                {
                    "symbol": symbol,
                    "provider": "Yahoo Finance via yfinance",
                    "url": f"https://finance.yahoo.com/quote/{symbol}.NS/history/",
                    "query": {"start": start, "end_exclusive": end, "auto_adjust": False, "repair": False},
                    "currency": "INR",
                    "exchange": "NSE",
                }
            )
        except Exception as exc:
            failures.append({"symbol": symbol, "error": f"{type(exc).__name__}: {exc}"})
        progress(
            f"{i + 1}/50 {symbol}: {'downloaded' if prices and prices[-1].symbol.iloc[0] == symbol else 'unavailable'}"
        )
        time.sleep(0.15)
    if not prices:
        raise DataQualityError(f"No authentic stock histories could be downloaded. Sources retained at {raw}")
    combined = pd.concat(prices, ignore_index=True).sort_values(["symbol", "date"])
    combined.to_parquet(processed / "prices.parquet", index=False)
    if quarantined:
        pd.concat(quarantined, ignore_index=True).to_parquet(processed / "quarantined.parquet", index=False)
    # An exchange-derived daily calendar from the index is a missing-session reference,
    # not a substitute for stock prices or a total-return benchmark.
    try:
        calendar = yf.Ticker("^NSEI").history(
            start=start, end=end, auto_adjust=False, repair=False, actions=False, raise_errors=True
        )
        calendar.to_csv(raw / "NIFTY50-index-calendar.csv")
        sessions = sorted({str(pd.Timestamp(d).date()) for d in calendar.index})
        calendar_source = "Yahoo Finance ^NSEI historical trading sessions (secondary)"
    except Exception:
        sessions = sorted(combined.date.unique().tolist())
        calendar_source = "Fallback: union of downloaded stock sessions; not independently complete"
    latest = max(combined.date)
    crosscheck = {"status": "unavailable", "date": latest, "matches": [], "mismatches": []}
    # Check same-date unadjusted close against the official exchange daily report.
    tag = datetime.strptime(latest, "%Y-%m-%d").strftime("%d%m%Y")
    bhav_url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{tag}.csv"
    try:
        r = httpx.get(bhav_url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        (raw / "official-bhavcopy.csv").write_bytes(r.content)
        bhav = pd.read_csv(BytesIO(r.content), skipinitialspace=True)
        bhav.columns = bhav.columns.str.strip()
        eq = bhav[bhav.SERIES.astype(str).str.strip().eq("EQ")].set_index("SYMBOL")
        for item in combined[combined.date.eq(latest)].itertuples():
            if item.symbol not in eq.index:
                continue
            expected = float(eq.loc[item.symbol, "CLOSE_PRICE"])
            difference = abs(item.close - expected)
            record = {"symbol": item.symbol, "provider_close": item.close, "nse_close": expected}
            crosscheck["matches" if difference <= max(0.06, expected * 0.0001) else "mismatches"].append(
                record
            )
        crosscheck["status"] = (
            "passed" if crosscheck["matches"] and not crosscheck["mismatches"] else "review_required"
        )
        crosscheck["source_url"] = bhav_url
    except Exception as exc:
        crosscheck["reason"] = str(exc)
    manifest = {
        "schema_version": 2,
        "dataset_id": dataset_id,
        "retrieved_at": stamp.isoformat(),
        "universe": "NIFTY 50",
        "membership_mode": "current_snapshot",
        "membership_source": CONSTITUENTS_URL,
        "membership_observed_at": stamp.isoformat(),
        "historical_membership_verified": False,
        "corporate_actions_independently_verified": False,
        "price_source": "Yahoo Finance via yfinance (secondary)",
        "source_records": sources,
        "requested_start": start,
        "end_exclusive": end,
        "stock_count": len(prices),
        "row_count": len(combined),
        "first_date": min(combined.date),
        "last_date": latest,
        "sessions": sessions,
        "calendar_source": calendar_source,
        "audits": audits,
        "failures": failures,
        "source_failures": failures,
        "quarantined_row_count": sum(a["quarantined_count"] for a in audits),
        "quarantined_symbols": [a["symbol"] for a in audits if a["quarantined_count"]],
        "processing_policy": "dated-row-quarantine-v1; valid genuine history retained; no interpolation",
        "crosscheck": crosscheck,
        "adjustment_convention": "Yahoo Close is provider close (may already reflect splits); Adj Close includes provider dividend/split adjustments. No local repair or interpolation.",
        "raw_format": "Original provider-returned tables and official source bytes",
        "usage": "Local educational research only. Check provider rights before redistribution.",
    }
    manifest["files"] = {
        str(p.relative_to(root)): file_hash(p)
        for folder in [raw, processed]
        for p in sorted(folder.iterdir())
        if p.is_file()
    }
    manifest["fingerprint"] = manifest_hash(manifest)
    dest = root / "data/manifests"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{dataset_id}.json").write_text(json.dumps(manifest, indent=2))
    progress(f"Frozen snapshot {dataset_id}: {len(prices)} stocks, {len(combined)} records.")
    return manifest
