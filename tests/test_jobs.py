from qcompass.experiments.store import JobStore


def test_submission_is_idempotent_and_claim_is_single_owner(tmp_path):
    store = JobStore(tmp_path)
    first = store.submit({"kind": "experiment"}, token="button-click")
    second = store.submit({"kind": "experiment"}, token="button-click")
    assert first == second
    assert len(store.list()) == 1
    assert store.claim()["id"] == first
    assert store.claim() is None
    store.cancel(first)
    assert store.cancelled(first)
    store.finish(first, "cancelled")
    assert store.get(first)["status"] == "cancelled"


def test_queued_cancellation_and_crash_recovery_are_explicit(tmp_path):
    store = JobStore(tmp_path)
    job = store.submit({"kind": "experiment"})
    store.cancel(job)
    assert store.claim() is None
    job2 = store.submit({"kind": "experiment"})
    store.claim()
    store.recover_interrupted()
    assert store.get(job2)["status"] == "interrupted"
    assert store.claim() is None
