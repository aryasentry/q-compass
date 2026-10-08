"""Daily-session realized metrics, with zero risk-free return explicitly stated."""

import numpy as np


def performance_metrics(equity, returns=None, turnovers=None, periods_per_year=252):
    values = np.asarray(list(equity.values()) if isinstance(equity, dict) else equity, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("Equity must be a nonempty positive finite vector.")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive.")
    derived = values[1:] / values[:-1] - 1
    actual = derived if returns is None else np.asarray(returns, dtype=float)
    if actual.shape != derived.shape or not np.isfinite(actual).all():
        raise ValueError("Returns must align with consecutive equity observations.")
    if not np.allclose(actual, derived, atol=1e-10, rtol=1e-8):
        raise ValueError("Supplied returns disagree with the equity curve.")
    turnover_values = np.asarray([] if turnovers is None else turnovers, dtype=float)
    if turnover_values.ndim != 1 or not np.isfinite(turnover_values).all() or np.any(turnover_values < 0):
        raise ValueError("Turnover must be a nonnegative finite vector.")
    std = float(np.std(actual, ddof=1)) if len(actual) >= 2 else None
    sharpe = (
        float(actual.mean() / std * np.sqrt(periods_per_year)) if std is not None and std > 1e-15 else None
    )
    return dict(
        net_return=float(values[-1] / values[0] - 1),
        annualized_volatility=std * np.sqrt(periods_per_year) if std is not None else None,
        max_drawdown=float(np.min(values / np.maximum.accumulate(values) - 1)),
        sharpe_ratio=sharpe,
        risk_free_rate=0.0,
        total_turnover=float(turnover_values.sum()),
        mean_rebalance_turnover=float(turnover_values.mean()) if len(turnover_values) else 0.0,
        periods_per_year=periods_per_year,
        return_observations=len(actual),
        sharpe_convention="daily arithmetic mean / sample standard deviation; risk-free rate = 0",
    )
