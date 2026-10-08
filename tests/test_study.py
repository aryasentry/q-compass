import pytest
from qcompass.data.snapshots import list_snapshots
from qcompass.evaluation.study import run_study


def test_study_rejects_dates_beyond_snapshot():
    snapshots = list_snapshots()
    if not snapshots:
        pytest.skip("Authentic data required")
    with pytest.raises(ValueError, match="coverage"):
        run_study(snapshots[0]["dataset_id"], "2026-01-01", "2030-01-01", mode="fixed_universe")


def test_weight_roundoff_is_explicit_and_large_changes_rejected():
    from qcompass.evaluation.study import balance_roundoff

    # Arithmetic weight fixture only, not market observations.
    values, adjustment = balance_roundoff({"a": 0.5, "b": 0.499999999})
    assert sum(values.values()) == pytest.approx(1, abs=1e-12)
    assert adjustment["delta"] == pytest.approx(1e-9, abs=1e-12)
    with pytest.raises(ValueError):
        balance_roundoff({"a": 0.2, "b": 0.2})


def test_study_configuration_rejects_impossible_or_unbudgeted_work():
    from qcompass.evaluation.study import validate_study_config

    with pytest.raises(ValueError):
        validate_study_config("real", n=8, k=1, batches=24, shots=256, seed=42)
    with pytest.raises(ValueError):
        validate_study_config("real", n=8, k=4, batches=3, shots=256, seed=42)
