from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_has_real_source_labels_and_no_startup_exception():
    app = AppTest.from_file(str(Path("app/dashboard.py").resolve()), default_timeout=30).run()
    assert not app.exception
    assert any("Portfolio experiment" in title.value for title in app.title)
    app.sidebar.radio[0].set_value("Data audit").run()
    assert not app.exception
    assert any("Data audit" in title.value for title in app.title)


def test_empty_state_never_invents_performance(tmp_path, monkeypatch):
    monkeypatch.setenv("QCOMPASS_ROOT", str(tmp_path))
    app = AppTest.from_file(str(Path("app/dashboard.py").resolve()), default_timeout=30).run()
    assert not app.exception
    assert not app.metric
    assert any("No dataset" in item.value for item in app.info)


def test_truncated_saved_run_cannot_crash_experiment_page(tmp_path, monkeypatch):
    monkeypatch.setenv("QCOMPASS_ROOT", str(tmp_path))
    folder = tmp_path / "artifacts/runs/broken-local-test"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text('{"kind":')
    app = AppTest.from_file(str(Path("app/dashboard.py").resolve()), default_timeout=30).run()
    assert not app.exception
    assert any("Unreadable saved run" in item.value for item in app.warning)
