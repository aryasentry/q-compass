"""One local worker, protected across processes by a filesystem lock."""

import os
import subprocess
import sys
import time

from filelock import FileLock, Timeout

from qcompass.experiments.store import JobStore
from qcompass.paths import project_root


def start_worker(root=None):
    root = root or project_root()
    folder = root / "artifacts"
    folder.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "QCOMPASS_ROOT": str(root),
            "OMP_NUM_THREADS": "4",
            "OPENBLAS_NUM_THREADS": "4",
            "MKL_NUM_THREADS": "4",
            "NUMEXPR_NUM_THREADS": "4",
        }
    )
    with (folder / "worker.log").open("a") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "qcompass.experiments.worker"],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process.pid


def work(root=None, once=False):
    root = root or project_root()
    store = JobStore(root)
    lock = FileLock(root / "artifacts/worker.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout:
        return
    try:
        store.recover_interrupted()
        idle_since = time.monotonic()
        while True:
            job = store.claim()
            if job is None:
                if once or time.monotonic() - idle_since > 30:
                    break
                time.sleep(0.5)
                continue
            idle_since = time.monotonic()
            job_id = job["id"]

            def progress(message):
                store.event(job_id, message)

            try:
                kind = job["config"].get("kind", "experiment")
                if kind == "download":
                    from qcompass.data.sources import fetch_snapshot

                    result = fetch_snapshot(
                        root=root, progress=progress, cancel=lambda: store.cancelled(job_id)
                    )
                    store.finish(
                        job_id,
                        "cancelled" if store.cancelled(job_id) else "completed",
                        result=result["dataset_id"],
                    )
                elif kind == "experiment":
                    from qcompass.experiments.runner import run_experiment

                    config = {k: v for k, v in job["config"].items() if k != "kind"}
                    result, path = run_experiment(
                        config, root, job_id, progress, lambda: store.cancelled(job_id)
                    )
                    successful = any(r.get("allocation_feasible") for r in result["results"])
                    status = "cancelled" if result["cancelled"] else "completed" if successful else "failed"
                    store.finish(job_id, status, str(path))
                else:
                    raise ValueError(f"Unsupported job kind {kind}")
            except Exception as exc:
                progress(f"Failed: {type(exc).__name__}: {exc}")
                store.finish(job_id, "cancelled" if store.cancelled(job_id) else "failed", error=str(exc))
            if once:
                break
    finally:
        lock.release()


if __name__ == "__main__":
    work()
