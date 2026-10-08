# Dated data quarantine and immutable reprocessing

Implemented only the assigned data modules (`sources.py`, `validation.py`,
`snapshots.py`) and `tests/test_data_quarantine.py`. No commits were made.

## Result

New snapshot:

`nifty50-20260905T080605-28fd98-sealed-0d14f0-reprocessed-641edf`

Parent:

`nifty50-20260905T080605-28fd98-sealed-0d14f0`

The new version contains **50 partial genuine histories**, **92,859 valid dated
rows**, **12 quarantined rows**, **50 source records**, and **zero current source
failures**. All parent failures remain in `parent_failures`; dated validation
problems are additionally preserved with every offending row's date, symbol,
original row position and reason list in `audits` and `quarantined.parquet`.

Canonical schema-2 fingerprint:

`8edc0117f2410c0b9af143268a3f34d5548d4ea5c9e069d254d20ae76289b31c`

The output references the existing original Yahoo CSVs, provider metadata, official
source bytes, and parent manifests by their unchanged hashes. Raw files were not
copied or overwritten. Only a new processed directory and a new manifest were
materialized. The new manifest includes parent dataset, parent fingerprint, parent
manifest SHA-256, raw CSV and metadata hashes, and processing policy. Loading the
new version verifies canonical metadata, all referenced files, and the new
processed-directory contract. The parent's full file verification still passes.

## Corrected dated evidence and eligibility

Inspection corrected the initial expectation that all 12 defects were latest-date
missing closes:

- Eleven rows are missing Close/Adj Close on **2026-09-04**: LT, HINDALCO, GRASIM,
  DRREDDY, M&M, KOTAKBANK, NESTLEIND, TITAN, ULTRACEMCO, TRENT, BAJAJFINSV.
- INDIGO has a wholly missing OHLC/adjusted quote on **2026-05-01**. That date is
  absent from the frozen trading calendar. Its actual latest quote is present.

Therefore current-window eligibility is **38**, compared with the parent's 37,
not the initially expected unchanged 37. Eleven latest-session gaps remain
ineligible; TMPV remains excluded for the unresolved adjusted-price move above
35%. INDIGO becomes usable without introducing or replacing any prices.

For decision date **2025-09-04**, eligibility rises from **38 to 50**. LT now
provides all 253 authentic close observations for a 252-return estimation window.
Changing or removing LT's later bad 2026-09-04 record produces an identical past
window, while any current window requiring that missing session still raises.

The official same-date crosscheck was copied unchanged: **38 matches**, no added
or fabricated validations. In particular, the recovered INDIGO history has not
been retroactively added to that official crosscheck. Historical membership and
independent corporate-action verification flags remain false.

## APIs and behavior

`normalize_history(frame, symbol, validate=True)` retains its strict default.
`validate=False` permits normalization before dated partitioning. Empty provider
responses or missing required source columns remain source-level failures.

`partition_prices(normalized_frame)` returns `(valid, quarantined, audit)`.
It identifies nonfinite/nonnumeric values, nonpositive prices, negative volume or
actions, invalid OHLC bounds, invalid dates/missing symbols, and duplicate
symbol/date keys. Every copy of a duplicated key is quarantined; no arbitrary
duplicate winner is selected. Every detected reason is recorded. Input frames
are unchanged; accepted numbers remain original supplied values. Large adjusted
moves remain explicit audit items for the existing per-window preparation gate.

Future `fetch_snapshot` calls now use this partition and persist quarantined rows
instead of excluding an entire stock because of one dated problem. A genuine
partial history remains available for earlier windows. Source failures remain
separate from dated quarantined records. No gap filling or price replacement is
performed. The existing `aligned_window` continues enforcing every required
calendar quote, so a window containing a genuine quarantined-session gap fails.

`reprocess_snapshot(dataset_id, root=None)` requires a verified schema-2 parent,
reads every member's hashed original CSV and metadata, and writes a new immutable
version. Its source identity reader supports the first snapshot's legacy JSON
string containing a mapping repr: only literal top-level currency/exchange values
are read with Python AST inspection; Timestamp or arbitrary expression nodes are
never evaluated. Future downloads explicitly serialize a plain metadata dict.

`list_snapshots` now sorts newest first by reprocessed time, otherwise seal time,
otherwise retrieval time. Filename lexicography no longer hides a newer child
behind its sealed parent. Live verification confirms this new version is first.

## Test-first evidence

Initial `.venv/bin/python -m pytest tests/test_data_quarantine.py -q` produced
**4 failures** for missing partition/reprocess APIs before implementation.

Additional red-to-green regressions cover legacy repr metadata, newest-version
ordering, and empty responses being source failures. Tests use actual frozen LT
source data; deliberate mutations are corruption checks only, never fabricated
market histories or reported runs.

Final command:

`.venv/bin/python -m pytest tests/test_data.py tests/test_data_quarantine.py -q`

Observed **12 passed in 1.09 seconds**. Scoped Ruff checks passed.

The first materialization attempt found the legacy metadata representation and
stopped before creating an output directory. After its safe-reader regression
passed, one successful output snapshot was created. Subsequent checks only loaded
and verified that output; no duplicate reprocessed versions were produced.

Live evidence after materialization:

- Parent original-file hashes and parent manifest hash still match.
- New canonical manifest fingerprint matches and immutable loader succeeds.
- Official crosscheck equals the parent crosscheck exactly.
- 50 source records and 12 dated quarantine records are retained.
- Current eligible 38; past eligible 50; original parent past eligible 38.
- New reprocessed version is first in `list_snapshots()`.

## Limits

This fixes dated structural-quality exclusion leaking into earlier eligibility;
it does not turn current membership into verified historical constituents or
independently certify corporate actions. The current-snapshot survivorship caveat
still applies. Original provider metadata/price provenance is preserved, including
missing quotes and unverified adjustments. No additional source downloads,
interpolation, corporate-action repair, or delisting-price assumptions occurred.
