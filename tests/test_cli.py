"""Queue/control tests use configuration records, never fabricated market outcomes."""

from typer.testing import CliRunner
from qcompass.cli import app
from qcompass.experiments.store import JobStore
from qcompass.experiments.runner import RunConfig
import pytest


def test_unknown_configuration_keys_fail_instead_of_silently_changing_study():
    with pytest.raises(ValueError):
        RunConfig(dataset_id="config-only", shotz=100)


def test_bounded_batch_and_resume_do_not_duplicate_completed_or_active_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("QCOMPASS_ROOT", str(tmp_path))
    monkeypatch.setattr("qcompass.experiments.worker.start_worker", lambda: None)
    settings = tmp_path / "settings.json"
    settings.write_text('{"batches":12,"shots":128,"n":8,"k":4}')
    cli = CliRunner()
    answer = cli.invoke(
        app,
        ["batch", str(settings), "--dataset", "queue-configuration-only", "--seeds", "11,42", "--sizes", "8"],
    )
    assert answer.exit_code == 0, answer.output
    store = JobStore(tmp_path)
    rows = store.list()
    assert len(rows) == 2
    batch_id = rows[0]["config"]["batch_id"]
    store.finish(rows[0]["id"], "completed")
    store.finish(rows[1]["id"], "interrupted")
    assert cli.invoke(app, ["resume-batch", batch_id]).exit_code == 0
    assert len(store.list()) == 3
    assert cli.invoke(app, ["resume-batch", batch_id]).exit_code == 0
    assert len(store.list()) == 3
