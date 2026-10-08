"""All price histories are slices of the downloaded authenticated-hash snapshot."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def real_prices():
    from qcompass.data.snapshots import load_snapshot, list_snapshots

    snapshots = list_snapshots()
    if not snapshots:
        pytest.skip("Download an authentic snapshot first")
    dataset = snapshots[0]["dataset_id"]
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/manifests" / f"{dataset}.json").exists():
        pytest.skip("Verified downloaded snapshot required; never synthesize financial prices.")
    manifest, _, prices = load_snapshot(dataset, root)
    selected = prices[prices.symbol.isin(["INFY", "SBIN"])]
    wide = selected.pivot(index="date", columns="symbol", values="adj_close").sort_index()
    return manifest, wide.loc["2025-01-30":"2025-03-05"]


def decisions():
    return [
        dict(decision_date="2025-01-31", execution_date="2025-02-01", weights={"INFY": 0.5, "SBIN": 0.5}),
        dict(
            decision_date="2025-02-28",
            execution_date="2025-03-03",
            weights={"SBIN": 1.0},
            eligible_symbols=["SBIN"],
        ),
    ]


def test_no_preexecution_return_drift_and_forced_sale(real_prices):
    from qcompass.evaluation.backtest import fixed_universe_backtest

    _, prices = real_prices
    result = fixed_universe_backtest(prices, decisions(), cost_bps=0)
    equity = result["equity"]
    assert equity["2025-01-31"] == 1
    assert equity["2025-02-01"] == 1
    next_date = prices.index[prices.index.get_loc("2025-02-01") + 1]
    expected = 0.5 * (prices.loc[next_date] / prices.loc["2025-02-01"]).sum()
    assert equity[next_date] == pytest.approx(expected)
    # Holdings earn old asset returns through the rebalance execution close.
    holding_values = 0.5 * prices.loc["2025-03-03"] / prices.loc["2025-02-01"]
    drifted = holding_values / holding_values.sum()
    trade = result["trades"][1]
    assert trade["previous_weights"]["INFY"] == pytest.approx(drifted["INFY"])
    assert trade["turnover"] == pytest.approx(drifted["INFY"])
    assert trade["forced_sales"] == pytest.approx(holding_values["INFY"])
    assert equity["2025-03-03"] == pytest.approx(holding_values.sum())
    assert "fixed" in result["mode"]
    assert result["historical_index_claim_eligible"] is False


@pytest.mark.parametrize("bps", [10, 25])
def test_self_financing_costs_match_actual_trades(real_prices, bps):
    from qcompass.evaluation.backtest import fixed_universe_backtest

    _, prices = real_prices
    result = fixed_universe_backtest(prices, decisions(), cost_bps=bps)
    first = result["trades"][0]
    assert result["equity"]["2025-02-01"] == pytest.approx(1 / (1 + bps / 10000))
    assert first["cost"] == pytest.approx(first["traded_notional"] * bps / 10000)
    assert first["post_trade_equity"] + first["cost"] == pytest.approx(first["pre_trade_equity"])
    for trade in result["trades"]:
        assert trade["cost"] == pytest.approx(trade["traded_notional"] * bps / 10000)


def test_missing_delisting_quote_never_filled(real_prices):
    from qcompass.evaluation.backtest import fixed_universe_backtest, BacktestDataError

    _, prices = real_prices
    broken = prices.copy()
    broken.loc["2025-03-03", "INFY"] = np.nan
    with pytest.raises(BacktestDataError, match="INFY"):
        fixed_universe_backtest(broken, decisions())


def test_schedules_weights_and_next_session_validated(real_prices):
    from qcompass.evaluation.backtest import fixed_universe_backtest, BacktestDataError, monthly_schedule

    _, prices = real_prices
    schedule = monthly_schedule(prices.index, "2025-01-01", "2025-03-05")
    assert schedule == [
        dict(decision_date="2025-01-31", execution_date="2025-02-01"),
        dict(decision_date="2025-02-28", execution_date="2025-03-03"),
    ]
    bad = decisions()
    bad[0]["execution_date"] = "2025-02-04"
    with pytest.raises(BacktestDataError):
        fixed_universe_backtest(prices, bad)
    bad = decisions()
    bad[0]["weights"] = {"INFY": 0.7}
    with pytest.raises(BacktestDataError):
        fixed_universe_backtest(prices, bad)
    bad = decisions()
    bad[1]["weights"] = {"INFY": 1.0}
    with pytest.raises(BacktestDataError):
        fixed_universe_backtest(prices, bad)


def test_strict_gate_blocks_current_snapshot_and_flags_without_evidence(real_prices):
    from qcompass.evaluation.gates import strict_backtest_gate, HistoricalEligibilityError

    manifest, _ = real_prices
    with pytest.raises(HistoricalEligibilityError):
        strict_backtest_gate(manifest)
    flags = dict(
        manifest,
        historical_membership_verified=True,
        corporate_actions_independently_verified=True,
        membership_mode="historical_verified",
    )
    with pytest.raises(HistoricalEligibilityError):
        strict_backtest_gate(flags)


def test_metrics_on_equity_algebra():
    # Pure wealth algebra, not a generated market price history or reported run.
    from qcompass.evaluation.metrics import performance_metrics

    m = performance_metrics([1.0, 1.1, 0.99], turnovers=[0.5, 0.2])
    assert m["net_return"] == pytest.approx(-0.01)
    assert m["max_drawdown"] == pytest.approx(-0.1)
    assert m["annualized_volatility"] == pytest.approx(np.sqrt(0.02 * 252))
    assert m["sharpe_ratio"] == pytest.approx(0.0, abs=1e-12)
    assert m["risk_free_rate"] == 0
    assert m["total_turnover"] == pytest.approx(0.7)


def verification_metadata(prices):
    """Structural gate fixture only; not a claim that these assets were independently verified."""
    start, end = prices.index[0], prices.index[-1]
    # Real current identifiers for STRUCTURAL tests only, not historical membership claims.
    symbols = pd.read_csv("data/raw/bootstrap/ind_nifty50list.csv")["Symbol"].tolist()
    membership = dict(
        verified=True,
        complete_history=True,
        coverage_start=start,
        coverage_end=end,
        records=[dict(effective_date=start, symbols=symbols, source="unit-test source reference")],
    )
    return dict(
        membership_mode="historical_verified",
        historical_membership_verified=True,
        corporate_actions_independently_verified=True,
        first_date=start,
        last_date=end,
        sessions=prices.index.tolist(),
        membership_evidence=membership,
        corporate_action_evidence=dict(
            verified=True,
            coverage_complete=True,
            coverage_start=start,
            coverage_end=end,
            symbols=symbols,
            sources=["unit-test source reference"],
        ),
    )


def test_gate_requires_complete_corporate_coverage_and_dated_membership(real_prices):
    from qcompass.evaluation.gates import strict_backtest_gate, HistoricalEligibilityError

    _, prices = real_prices
    metadata = verification_metadata(prices)
    assert strict_backtest_gate(metadata)["eligible"] is True
    incomplete = verification_metadata(prices)
    incomplete["membership_evidence"]["records"][0]["symbols"] = ["INFY"]
    with pytest.raises(HistoricalEligibilityError):
        strict_backtest_gate(incomplete)
    metadata["corporate_action_evidence"]["symbols"] = ["INFY"]
    with pytest.raises(HistoricalEligibilityError):
        strict_backtest_gate(metadata)
    metadata = verification_metadata(prices)
    metadata["membership_evidence"]["complete_history"] = False
    with pytest.raises(HistoricalEligibilityError):
        strict_backtest_gate(metadata)


def test_strict_replay_rejects_uncovered_interval_and_missing_calendar_session(real_prices):
    from qcompass.evaluation.backtest import strict_historical_backtest, BacktestDataError

    _, prices = real_prices
    metadata = verification_metadata(prices)
    metadata["first_date"] = "2025-02-01"
    with pytest.raises(BacktestDataError):
        strict_historical_backtest(prices, decisions(), metadata)
    metadata = verification_metadata(prices)
    omitted = prices.drop(index="2025-02-03")
    with pytest.raises(BacktestDataError):
        strict_historical_backtest(omitted, decisions(), metadata)


def test_metrics_reject_inconsistent_returns_and_undefined_sharpe():
    from qcompass.evaluation.metrics import performance_metrics

    with pytest.raises(ValueError):
        performance_metrics([1, 1.1], returns=[0.2])
    assert performance_metrics([1, 1, 1])["sharpe_ratio"] is None
