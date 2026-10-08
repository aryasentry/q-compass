"""Historical eligibility, self-financing replay, and realized portfolio metrics."""

from .backtest import fixed_universe_backtest, monthly_schedule, run_backtest, strict_historical_backtest
from .gates import HistoricalEligibilityError, strict_backtest_gate
from .metrics import performance_metrics

__all__ = [
    "fixed_universe_backtest",
    "monthly_schedule",
    "run_backtest",
    "strict_historical_backtest",
    "HistoricalEligibilityError",
    "strict_backtest_gate",
    "performance_metrics",
]
