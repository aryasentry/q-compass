"""Fail closed on malformed records. No price interpolation or repair."""

from io import BytesIO

import numpy as np
import pandas as pd


class DataQualityError(ValueError):
    pass


def partition_prices(data: pd.DataFrame):
    """Separate bad dated records without letting future defects erase valid history.

    All copies of duplicate symbol/date keys are quarantined. No choice between
    conflicting originals, interpolation, or replacement value is made. The raw
    input is unchanged; rejected row positions/reasons retain source traceability.
    """
    numeric = ["open", "high", "low", "close", "adj_close", "volume", "dividends", "splits"]
    if not {"date", "symbol", *numeric}.issubset(data.columns):
        raise DataQualityError("Missing required daily price/action columns")
    rows = data.copy(deep=True).reset_index(drop=True)
    numbers = rows[numeric].apply(pd.to_numeric, errors="coerce")
    reasons = [[] for _ in range(len(rows))]

    def flag(mask, reason):
        for index in np.flatnonzero(np.asarray(mask, dtype=bool)):
            reasons[index].append(reason)

    dates = pd.to_datetime(rows.date, errors="coerce")
    flag(dates.isna(), "invalid_date")
    symbols = rows.symbol.astype("string")
    flag(symbols.isna() | symbols.str.strip().eq("").fillna(True), "missing_symbol")
    flag(rows.duplicated(["symbol", "date"], keep=False), "duplicate_symbol_date")
    for col in numeric:
        flag(~np.isfinite(numbers[col].to_numpy(float)), f"nonfinite_{col}")
        if col in ("open", "high", "low", "close", "adj_close"):
            flag(numbers[col] <= 0, f"nonpositive_{col}")
        else:
            flag(numbers[col] < 0, f"negative_{col}")
    flag(numbers.high + 1e-5 < numbers[["open", "close", "low"]].max(axis=1), "invalid_ohlc_high")
    flag(numbers.low - 1e-5 > numbers[["open", "close", "high"]].min(axis=1), "invalid_ohlc_low")
    rejected = np.array([bool(items) for items in reasons], dtype=bool)
    valid = rows.loc[~rejected].copy()
    # Normalize numeric types only; every retained number is the supplied value.
    valid[numeric] = numbers.loc[~rejected]
    bad = rows.loc[rejected].copy()
    bad["source_row"] = np.flatnonzero(rejected)
    bad["quarantine_reasons"] = [reasons[i] for i in np.flatnonzero(rejected)]
    audit = (
        validate_prices(valid)
        if not valid.empty
        else dict(
            rows=0,
            first_date=None,
            last_date=None,
            large_moves=[],
            validation="no_valid_rows",
            adjustment_audit="provider_adjusted_not_independently_certified",
        )
    )
    audit.update(
        input_rows=len(rows),
        quarantined_count=int(rejected.sum()),
        quarantined_rows=[
            dict(
                source_row=int(i),
                date=str(rows.at[i, "date"]),
                symbol=str(rows.at[i, "symbol"]),
                reasons=reasons[i],
            )
            for i in np.flatnonzero(rejected)
        ],
        quarantine_policy="dated-row exclusion; every duplicate-key copy rejected; no interpolation",
    )
    return valid.reset_index(drop=True), bad.reset_index(drop=True), audit


def parse_constituents(content: bytes) -> pd.DataFrame:
    data = pd.read_csv(BytesIO(content))
    columns = {
        "Company Name": "company",
        "Industry": "sector",
        "Symbol": "symbol",
        "Series": "series",
        "ISIN Code": "isin",
    }
    if not set(columns).issubset(data):
        raise DataQualityError("Not an official-format NSE constituent file")
    data = data.rename(columns=columns)[list(columns.values())]
    for col in data:
        data[col] = data[col].astype("string").str.strip()
    if data.isna().any().any() or (data == "").any().any():
        raise DataQualityError("Missing constituent identifiers or labels")
    if not data.symbol.is_unique or not data["isin"].is_unique:
        raise DataQualityError("Duplicate symbol or ISIN")
    if len(data) != 50 or not data.series.eq("EQ").all():
        raise DataQualityError("Expected exactly 50 NIFTY equity constituents")
    if not data["isin"].str.match(r"^IN[A-Z0-9]{10}$").all():
        raise DataQualityError("Invalid Indian security identifier")
    return data.sort_values("isin").reset_index(drop=True)


def validate_prices(data: pd.DataFrame) -> dict:
    required = {
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividends",
        "splits",
    }
    if not required.issubset(data) or data.empty:
        raise DataQualityError("Missing required daily price/action records")
    if data.duplicated(["symbol", "date"]).any():
        raise DataQualityError("Duplicate stock/date record")
    dates = pd.to_datetime(data.date, errors="coerce")
    if dates.isna().any():
        raise DataQualityError("Unparseable trading date")
    nums = data[["open", "high", "low", "close", "adj_close", "volume", "dividends", "splits"]]
    if not np.isfinite(nums.to_numpy(dtype=float)).all():
        raise DataQualityError("Missing or non-finite price/action value")
    if (nums[["open", "high", "low", "close", "adj_close"]] <= 0).any().any():
        raise DataQualityError("Non-positive market price")
    if (nums[["volume", "dividends", "splits"]] < 0).any().any():
        raise DataQualityError("Negative volume, dividend or split factor")
    if (data.high + 1e-5 < data[["open", "close", "low"]].max(axis=1)).any():
        raise DataQualityError("Daily high below another daily price")
    if (data.low - 1e-5 > data[["open", "close", "high"]].min(axis=1)).any():
        raise DataQualityError("Daily low above another daily price")
    changes = data.sort_values(["symbol", "date"]).groupby("symbol").adj_close.pct_change(fill_method=None)
    large = data.loc[changes.abs() > 0.35, ["symbol", "date"]].to_dict("records")
    return {
        "rows": len(data),
        "first_date": str(dates.min().date()),
        "last_date": str(dates.max().date()),
        "large_moves": large,
        "validation": "structural_pass",
        "adjustment_audit": "provider_adjusted_not_independently_certified",
    }
