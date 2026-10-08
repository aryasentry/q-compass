# Authentic data and provenance

## Sources actually used

- [NSE NIFTY 50 constituent CSV](https://archives.nseindia.com/content/indices/ind_nifty50list.csv)
  for company, symbol, industry, series and ISIN. It is a current snapshot, not
  historical membership. Retrieval time is recorded; there is no fabricated as-of field.
- [Yahoo Finance through yfinance](https://ranaroussi.github.io/yfinance/) for
  historical daily stock OHLC, adjusted close, volume, dividends and splits.
  This is a secondary provider; local educational use does not grant redistribution rights.
- [NSE daily report for 4 September 2026](https://archives.nseindia.com/products/content/sec_bhavdata_full_04092026.csv)
  for same-session close cross-checks. Provider and official prices are compared
  without mixing the official field into an incomplete provider history.
- Yahoo `^NSEI` session observations supply the initial trading calendar.
  This is not a total-return benchmark or a guaranteed official holiday calendar.
  A union-of-stock-sessions fallback is explicitly labelled in new downloads.

Raw provider-returned CSVs are saved before validation. These are original table
exports, not raw HTTP JSON responses. Adjustment fields remain separate:
Yahoo Close may already reflect splits; Adj Close follows Yahoo's own adjustment
convention. No local `repair`, auto adjustment, price interpolation or silent
source replacement is enabled.

## The first snapshot

Original collection: `nifty50-20260905T080605-28fd98`.
Metadata-protected version: `nifty50-20260905T080605-28fd98-sealed-0d14f0`.
Final row-quarantined version: `nifty50-20260905T080605-28fd98-sealed-0d14f0-reprocessed-641edf`.
The sealed version references unchanged original price files and binds the
original manifest's bytes as well. Protection starts at seal time; the original
development version is not retrospectively presented as already protected.

50 official constituents; 50 price downloads retained. The original conservative
whole-history validation rejected 12 histories. The final version instead retains
92,859 valid dated rows across all 50 stocks and separately quarantines 12 invalid
rows: 11 missing closes on 4 September 2026, and an all-missing INDIGO record on
1 May 2026 outside the observed trading calendar. Original bytes are unchanged.
Only affected windows are blocked, so future bad quotes cannot erase valid earlier
history. TMPV has an unresolved large adjusted-price movement in the default window.
Thus 38 stocks are currently eligible; no missing price is filled.

An eight-stock subset is chosen deterministically from eligible identities across
industries. 252 return observations need 253 complete daily adjusted-close
observations. Missing any expected session blocks that stock/window. Movements
above 35% in adjusted prices are conservative review flags, not automatic proof
of a bad price; flagged windows require reconciliation before use.

## Genuine file import

Create a directory containing:

- `constituents.csv` in the original official NSE format;
- one original Yahoo-format daily CSV per imported stock, with a date index and
  `Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits` columns;
- `provenance.json` with **actual**, not guessed, provider information:

```json
{
  "provider": "Actual provider name",
  "source_url": "Actual source page URL",
  "retrieved_at": "Actual retrieval timestamp",
  "membership_observed_at": "Actual membership retrieval timestamp",
  "currency": "INR",
  "exchange": "NSE",
  "adjustment_convention": "Actual provider adjustment convention",
  "files": {"RELIANCE": "RELIANCE.csv"}
}
```

This is a **schema example, not a data fixture**. Replace descriptions with the
real provenance of genuine downloaded files. The importer refuses missing source
fields, malformed identities and invalid prices. It records attribution as
supplied, not independently certified authenticity. It does not convert arbitrary
official raw-only data into adjusted prices. That needs an audited separate adapter.

## Historical evidence still required

[NSE Indices historical data](https://www.niftyindices.com/reports/historical-data)
and [data offerings](https://niftyindices.com/offerings/data-subscription) do not,
by themselves, establish a complete dated constituent history. Reconstruct a
verified baseline and every periodic/exceptional change, including identifiers,
effective dates, sources and corporate actions. Strict mode requires complete
50-member records at each change, sufficient coverage and explicit action evidence.
Structural flags are never a substitute for doing that verification.
