import json
import pytest
from qcompass.experiments.runner import RunConfig, read_result, save_result


def test_run_settings_bound_laptop_workload():
    with pytest.raises(ValueError):
        RunConfig(dataset_id="real", n=50)
    with pytest.raises(ValueError):
        RunConfig(dataset_id="real", k=7, max_weight=0.1)


def test_saved_run_integrity_and_nonfinite_rejection(tmp_path):
    result = {"run_id": "test-record", "results": [], "dataset_fingerprint": "fixture-not-market-data"}
    path = save_result(result, tmp_path)
    assert read_result(path) == result
    changed = json.loads(path.read_text())
    changed["results"] = ["tampered"]
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        read_result(path)
    with pytest.raises(ValueError):
        save_result({"run_id": "bad", "value": float("nan")}, tmp_path)
