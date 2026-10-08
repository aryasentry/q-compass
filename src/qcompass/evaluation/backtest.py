"""Monthly close-execution replay of actual adjusted prices without quote filling."""

from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .gates import strict_backtest_gate
from .metrics import performance_metrics


class BacktestDataError(ValueError):
    pass


def _dates(values):
    values = list(values)
    try:
        if any(not isinstance(v, str) or str(date.fromisoformat(v)) != v for v in values):
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise BacktestDataError("Session dates must be ISO YYYY-MM-DD strings.") from exc
    if not values or values != sorted(set(values)):
        raise BacktestDataError("Session dates must be nonempty, unique and increasing.")
    return values


def monthly_schedule(sessions, start, end):
    """Completed month-end decisions and immediately following session closes.

    A later-month session must exist to establish completion. An incomplete final
    month is omitted. The supplied calendar must contain every trading session.
    """
    sessions = _dates(sessions)
    if str(date.fromisoformat(start)) != start or str(date.fromisoformat(end)) != end or start > end:
        raise BacktestDataError("Invalid schedule interval.")
    return [
        dict(decision_date=a, execution_date=b)
        for a, b in zip(sessions[:-1], sessions[1:])
        if a[:7] != b[:7] and start <= a and b <= end
    ]


def fixed_universe_backtest(prices, decisions, cost_bps=10):
    return run_backtest(prices, decisions, cost_bps, mode="fixed_universe")


def strict_historical_backtest(prices, decisions, manifest, membership_evidence=None, cost_bps=10):
    return run_backtest(
        prices,
        decisions,
        cost_bps,
        mode="strict_historical",
        manifest=manifest,
        membership_evidence=membership_evidence,
    )


def run_backtest(prices, decisions, cost_bps=10, *, mode, manifest=None, membership_evidence=None):
    """Replay normalized wealth; prices index is the complete trading calendar.

    Each scheduled dictionary has decision_date, execution_date, weights, and
    optionally eligible_symbols. Full investment is required. At execution the
    existing holdings first drift to that close; then costs and target trades
    occur. New holdings earn returns only on subsequent session intervals.
    """
    if mode not in ("fixed_universe", "strict_historical"):
        raise BacktestDataError("Choose explicit fixed_universe or strict_historical mode.")
    eligibility = (
        strict_backtest_gate(manifest or {}, membership_evidence) if mode == "strict_historical" else None
    )
    if not isinstance(prices, pd.DataFrame) or not prices.columns.is_unique:
        raise BacktestDataError("Prices must be a DataFrame with unique symbol columns.")
    sessions = _dates(prices.index)
    if mode == "strict_historical":
        if sessions[0] < manifest["first_date"] or sessions[-1] > manifest["last_date"]:
            raise BacktestDataError("Price interval exceeds verified dataset coverage.")
        calendar = _dates(manifest.get("sessions", []))
        expected = [d for d in calendar if sessions[0] <= d <= sessions[-1]]
        if sessions != expected:
            raise BacktestDataError("Price frame must contain every verified trading-calendar session.")
    if not np.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise BacktestDataError("Cost bps must be finite in [0,10000).")
    if not isinstance(decisions, list) or not decisions:
        raise BacktestDataError("At least one scheduled decision is required.")
    allowed = {
        d["decision_date"]: d["execution_date"] for d in monthly_schedule(sessions, sessions[0], sessions[-1])
    }
    checked, previous_decision = {}, ""
    for decision in decisions:
        d, e = decision.get("decision_date"), decision.get("execution_date")
        if d not in allowed or allowed[d] != e or d <= previous_decision:
            raise BacktestDataError(
                "Decisions must be ordered completed month ends, executing next session close."
            )
        weights = decision.get("weights")
        if not isinstance(weights, dict) or not weights:
            raise BacktestDataError("Each decision needs a symbol-to-weight dictionary.")
        try:
            weights = {s: float(w) for s, w in weights.items()}
        except (TypeError, ValueError) as exc:
            raise BacktestDataError("Weights must be finite numbers.") from exc
        if any(not isinstance(s, str) or not np.isfinite(w) or w < 0 for s, w in weights.items()):
            raise BacktestDataError("Weights must be finite, long only and keyed by symbol.")
        if not np.isclose(sum(weights.values()), 1, atol=1e-10, rtol=0):
            raise BacktestDataError("Target weights must sum to one; no silent normalization.")
        weights = {s: w for s, w in weights.items() if w > 0}
        eligible = decision.get("eligible_symbols")
        if eligible is not None and (
            not isinstance(eligible, list) or not set(weights).issubset(set(eligible))
        ):
            raise BacktestDataError("Target holdings must belong to decision-date eligible symbols.")
        if mode == "strict_historical":
            evidence = (
                membership_evidence if membership_evidence is not None else manifest["membership_evidence"]
            )
            records = [r for r in evidence["records"] if r["effective_date"] <= d]
            historical = set(records[-1]["symbols"]) if records else set()
            if not set(weights).issubset(historical):
                raise BacktestDataError("Target holdings violate verified decision-date membership.")
            eligible = sorted(historical)
        checked[e] = dict(decision_date=d, weights=weights, eligible_symbols=eligible)
        previous_decision = d

    def quote(session, symbol):
        try:
            value = float(prices.loc[session, symbol])
        except (KeyError, TypeError, ValueError) as exc:
            raise BacktestDataError(
                f"Missing actual close for {symbol} on {session}; no price fabrication."
            ) from exc
        if not np.isfinite(value) or value <= 0:
            raise BacktestDataError(
                f"Missing/invalid actual close for {symbol} on {session}; no price fabrication."
            )
        return value

    equity, trades, holdings, cash = {}, [], {}, 1.0
    fee_rate = cost_bps / 10000
    for session in sessions[sessions.index(decisions[0]["decision_date"]) :]:
        # Holdings are adjusted units; valuation incorporates the provider's total-return adjustment convention.
        values = {s: units * quote(session, s) for s, units in holdings.items()}
        wealth = cash + sum(values.values())
        if session in checked:
            decision = checked[session]
            target = decision["weights"]
            for symbol in target:
                quote(session, symbol)
            symbols = set(values) | set(target)
            previous = {s: v / wealth for s, v in values.items()}
            turnover = 0.5 * sum(abs(target.get(s, 0) - previous.get(s, 0)) for s in symbols)

            def traded(fee):
                return sum(abs(target.get(s, 0) * (wealth - fee) - values.get(s, 0)) for s in symbols)

            # Solve self-financing costs exactly: fees depend on the *actual* post-fee trades.
            cost = (
                brentq(lambda fee: fee - fee_rate * traded(fee), 0.0, wealth, xtol=1e-14) if fee_rate else 0.0
            )
            after = wealth - cost
            notional = traded(cost)
            eligible = decision["eligible_symbols"]
            forced = {s: v for s, v in values.items() if eligible is not None and s not in eligible}
            trades.append(
                dict(
                    decision_date=decision["decision_date"],
                    execution_date=session,
                    previous_weights=previous,
                    target_weights=target,
                    turnover=float(turnover),
                    traded_notional=float(notional),
                    cost=float(cost),
                    cost_bps=float(cost_bps),
                    forced_sales=float(sum(forced.values())),
                    forced_sales_by_symbol=forced,
                    pre_trade_equity=float(wealth),
                    post_trade_equity=float(after),
                )
            )
            holdings = {s: w * after / quote(session, s) for s, w in target.items()}
            cash, wealth = 0.0, after
        equity[session] = float(wealth)
    values = list(equity.values())
    daily = [values[i] / values[i - 1] - 1 for i in range(1, len(values))]
    return dict(
        mode=mode,
        historical_index_claim_eligible=mode == "strict_historical",
        eligibility=eligibility,
        equity=equity,
        returns=dict(zip(list(equity)[1:], daily)),
        trades=trades,
        metrics=performance_metrics(values, turnovers=[t["turnover"] for t in trades]),
        total_cost=float(sum(t["cost"] for t in trades)),
        cost_bps=float(cost_bps),
        label=(
            "Fixed-universe research replay; current membership is not historical membership"
            if mode == "fixed_universe"
            else "Verified historical membership replay"
        ),
        execution_convention="decision after monthly final close; trade following session close; new returns thereafter",
        price_convention="provided actual adjusted closes; no missing-quote filling or fabricated liquidation prices",
    )
