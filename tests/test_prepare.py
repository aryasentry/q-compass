import pandas as pd
import pytest
from qcompass.data.prepare import aligned_window
from qcompass.data.validation import DataQualityError


def test_empty_market_records_cannot_become_an_experiment():
    with pytest.raises(DataQualityError):
        aligned_window(pd.DataFrame(), ["RELIANCE"], [], "2026-09-04")


def test_noncanonical_date_cannot_include_later_months():
    from qcompass.experiments.runner import RunConfig

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        RunConfig(dataset_id="configuration-only", as_of="2025-1-01")
    with pytest.raises(DataQualityError, match="YYYY-MM-DD"):
        aligned_window(pd.DataFrame(), ["RELIANCE"], ["2025-01-31"], "2025-1-01")


@pytest.mark.realdata
def test_future_observations_do_not_change_past_estimates():
    from qcompass.data.snapshots import list_snapshots, load_snapshot

    snapshots = list_snapshots()
    if not snapshots:
        pytest.skip("Authentic frozen snapshot not downloaded")
    _, _, prices = load_snapshot(snapshots[0]["dataset_id"])
    single = prices[prices.symbol.eq("RELIANCE")].copy()
    dates = sorted(single.date.unique())
    cutoff = dates[-30]
    before = aligned_window(single, ["RELIANCE"], dates, cutoff)
    single.loc[single.date > cutoff, "adj_close"] *= 2  # corruption probe, never a market dataset
    after = aligned_window(single, ["RELIANCE"], dates, cutoff)
    pd.testing.assert_frame_equal(before, after)
    # Removing an in-window real quote must raise, not forward-fill.
    missing = single[single.date != dates[-60]]
    with pytest.raises(DataQualityError):
        aligned_window(missing, ["RELIANCE"], dates, cutoff)
