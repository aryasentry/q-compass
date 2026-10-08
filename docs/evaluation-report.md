# Evaluation core: API, evidence, and limits

Files owned by this implementation: `src/qcompass/evaluation/`,
`tests/test_evaluation_core.py`, and this report. Existing engine files were not
edited during this task.

## Public API

```python
from qcompass.evaluation import (
    monthly_schedule, fixed_universe_backtest, strict_historical_backtest,
    run_backtest, performance_metrics, strict_backtest_gate,
)

schedule = monthly_schedule(sessions, start='2025-01-01', end='2025-03-05')
# Fill each entry with decision-time weights supplied by the caller:
# {'decision_date': ISO_date, 'execution_date': ISO_date,
#  'weights': {'SYMBOL': weight, ...}, 'eligible_symbols': [...]}  # eligible optional

result = fixed_universe_backtest(actual_adjusted_prices, decisions, cost_bps=10)
# Explicit strict alternative; failure NEVER falls back to fixed-universe mode:
result = strict_historical_backtest(actual_adjusted_prices, decisions, manifest,
                                   membership_evidence=None, cost_bps=10)
# Generic core requires an explicit keyword mode:
result = run_backtest(actual_adjusted_prices, decisions, cost_bps=10,
                      mode='fixed_universe')
```

Prices are a wide pandas DataFrame, actual adjusted closes by symbol, indexed by
unique ascending ISO dates containing the complete trading calendar. No filling,
interpolation, synthetic returns, or fabricated liquidation prices occurs.
Decisions must be ordered completed month ends and execute at the immediately
following available session close. Incomplete final months are omitted by the
schedule helper. The helper uses the supplied trading calendar, including special
sessions; the authentic test snapshot includes Saturday 2025-02-01.

Each output includes `equity` and `returns` dictionaries by date, `trades`,
`metrics`, `total_cost`, `cost_bps`, mode, eligibility and explicit execution/price
conventions. The fixed-universe label warns against historical index claims and
sets `historical_index_claim_eligible=False`. Selection/estimation callbacks and
data preparation remain the parent's responsibility.

## Accounting

The replay starts with wealth 1 in cash on the first decision date. Initial
holdings receive no preexecution asset returns. At each later execution close,
old holdings first earn returns through that close; their marked-to-market weights
are the prior weights for rebalancing. New holdings only earn returns after the
execution close. Provider-adjusted units preserve the supplied adjusted-return
convention; raw-share corporate-action processing is not simulated separately.

Target weights must be nonnegative and sum to exactly one within numerical
tolerance. No automatic normalization occurs. Eligible symbols, when supplied,
must contain all positive target holdings. Existing holdings outside that list
are sold using their actual execution close, included in traded notional and
turnover, and separately exposed as `forced_sales` and `forced_sales_by_symbol`.
Missing any held-asset quote stops the replay with `BacktestDataError`, even when
that holding is about to be liquidated. A true unquoted delisting therefore blocks
until an actual, documented liquidation treatment is available.

Turnover is half the L1 difference between target and drifted pretrade security
weights. Initial fully invested purchases from cash have security turnover 0.5;
cash is not counted as a security. Actual fees are independently self-financing:

`fee = (cost_bps / 10000) * sum(abs(target_weight * (pretrade_wealth - fee) - old_value))`

This scalar equation is solved numerically before target units are acquired.
Thus fees equal the reported actual traded notional times the fee rate, and
posttrade wealth plus fee exactly equals pretrade wealth. 0, 10 and 25 bps are
covered; other finite rates in [0,10000) are accepted. No slippage or taxes are
silently added. Initial construction also pays its actual purchase fee.

`performance_metrics(equity, returns=None, turnovers=None, periods_per_year=252)`
computes realized net return, annualized sample return standard deviation,
negative peak-to-trough max drawdown, arithmetic daily Sharpe with risk-free rate
explicitly zero, and total/mean rebalance turnover. Supplied returns must agree
with equity. Undefined Sharpe (zero variance or too little data) is `None`.

## Strict historical eligibility schema

The manifest must have membership mode `historical_verified` or `point_in_time`,
both `historical_membership_verified=True` and
`corporate_actions_independently_verified=True`, plus dated `first_date` and
`last_date`. Flags alone are insufficient. The current downloaded snapshot fails
this gate as intended.

Membership evidence is passed explicitly or stored as `manifest.membership_evidence`:

```json
{
  "verified": true,
  "complete_history": true,
  "coverage_start": "YYYY-MM-DD",
  "coverage_end": "YYYY-MM-DD",
  "records": [
    {"effective_date": "YYYY-MM-DD", "symbols": ["..."], "source": "verified source reference"}
  ]
}
```

Full constituent records must be unique, ordered and begin by the coverage start;
the coverage interval must contain the manifest interval. Downloading selected
reconstitution releases does not establish `complete_history`.

`manifest.corporate_action_evidence` must contain `verified=True`,
`coverage_complete=True`, coverage dates, nonempty `sources`, and `symbols`
covering the union of historical members. This verifies the structure of an
upstream verification record, not the truth of arbitrary caller assertions.
The upstream data verification process must substantiate these fields.

Strict replay additionally checks that its actual price interval is covered,
every manifest-calendar session appears, and targets belong to verified
decision-date membership. Missing historical or corporate-action coverage raises
`HistoricalEligibilityError`; it never produces a purported historical result.

## Tests and authentic-data demonstration

Initial test-first command:
`.venv/bin/python -m pytest tests/test_evaluation_core.py -q`

Observed **7 failed** for missing evaluation modules before implementation.
Additional tests caught a missing strict replay interval/calendar guard; that
guard was added before final verification. An initially assumed weekday execution
date was corrected to the actual snapshot's 2025-02-01 trading session.

Final command: `.venv/bin/python -m pytest tests/test_evaluation_core.py -q`

Observed **10 passed in 0.57 seconds**. Scoped Ruff check over the evaluation
directory and test file passed. Tests cover no preexecution gains, execution lag,
drift, forced sales, self-financing costs at 0/10/25 bps, missing liquidation
quotes, target eligibility, monthly scheduling, metrics, strict current-snapshot
rejection, missing evidence, symbol coverage, interval and session completeness.

Price fixtures are real INFY/SBIN adjusted-price slices from hash-verified
snapshot `nifty50-20260905T080605-28fd98`, spanning 2025-01-30 to 2025-03-05.
If the snapshot is unavailable, those tests skip rather than create prices.
Pure wealth algebra and structural verification metadata are used only in unit
checks, never as financial histories or claimed verified historical runs.

A fixed-universe accounting demonstration bought 50% INFY/50% SBIN at the
2025-02-01 close, then switched to SBIN at the 2025-03-03 close. The restricted
eligible list in this scripted test exercises forced-sale accounting; it is NOT
a claim that INFY left the actual index. Across 24 equity observations, net
returns were -3.8562% (0 bps), -4.0490% (10 bps), and -4.3371% (25 bps). Total
security turnover was 1.0041494 in all three runs. These are implementation
checks on authentic quotes, not an optimized strategy or historical NIFTY claim.

## Limits

- Fixed-universe input dates must already be a complete trading calendar; only
  strict mode has manifest calendar evidence to detect an entirely omitted row.
- No point-in-time membership or corporate-action completeness was fabricated.
  The current dataset remains blocked for strict historical evaluation.
- No slippage, exchange impact, taxes, borrowing, cash interest, intraday fills,
  or synthetic delisting prices are modeled. Costs cover actual traded notional.
- Annualized statistics from the short demonstration are not performance claims.
- The engine replays supplied decisions; it does not certify how callers obtained
  their estimates, selected weights, or historical information.
