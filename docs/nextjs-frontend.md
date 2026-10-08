# The new Next.js interface

The new application is additive. `app/dashboard.py` and `.streamlit/` remain
unchanged. Both interfaces use the same frozen datasets, saved results, SQLite
job database and exclusive simulation worker.

```text
Browser :3000 → Next.js same-origin /api routes → FastAPI :8000
                                                     ↓
Streamlit :8501 ─────────────────────────→ Python research engine
                                                     ↓
                                    Frozen data + SQLite + run artifacts
```

## Start

From the Major Project directory:

```sh
bash scripts/start-nextjs.sh
```

This checks ports, installs frontend dependencies if absent, builds Next.js and
starts the two loopback services. It never kills an existing service to free a
port. Open `http://127.0.0.1:3000`. For frontend development with hot reload:

```sh
bash scripts/start-nextjs.sh --dev
```

Stop this launcher with Ctrl+C. Only its own API and frontend processes stop;
Streamlit is independent. A submitted simulation worker runs independently so
closing a tab or web server does not discard work. Use the activity screen to
request cancellation; the worker checks it between bounded operations.

To run services separately, use two terminals:

```sh
# Terminal 1, from Major Project
.venv/bin/python -m uvicorn qcompass.api.app:app --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend
npm ci
npm run build
npm run start
```

Streamlit is still available using its original command:

```sh
.venv/bin/python -m streamlit run app/dashboard.py
```

Python dependencies are frozen in `uv.lock`; frontend dependencies are frozen
separately in `frontend/package-lock.json`. The local font is bundled: rendering
does not request Google Fonts. A fresh environment needs Node.js/npm and the
project's Python dependencies (`.bootstrap/bin/uv sync --frozen`).

## Screens

- **Overview:** the latest saved optimization result; selection score, separate
  stock/weight feasibility, actual allocations and adaptive-choice evidence.
- **Experiments:** the shared queue, immutable saved runs, and new-run form.
- **Activity:** saved worker events, status, cancellation and result link.
- **Run details:** all method metrics, allocation per method, pilot evidence,
  sample counts, configuration record, CSV and JSON export.
- **Data sources:** verified snapshot coverage, official membership, secondary
  price source labels, quarantine records, fingerprints and source-file checks.
- **Methodology:** beginner explanations and the current research limitations.

Submitting a form creates a job only after the user clicks Run experiment. A
retry of the same request in the mounted form retains its idempotency token.
Refreshing a job/result page only reads existing records. A new form submission
after leaving/reloading the form is a new experiment; inspect the queue first
if a previous request had an uncertain network outcome.

The data screen can explicitly queue a new authentic-source download. It never
overwrites older snapshots. Failed downloads remain failed, not filled with
sample data. A legacy unsupported manifest may appear as a record warning;
the original file is preserved rather than deleted to hide that warning.

## Research boundaries

The UI migration does not expand the financial claims. The default controller
is **pilot-only adaptive tuning**, not a trained market-aware ranking model.
Selection scores are not realized returns. Matching an exact selection result
does not prove quantum speedup or investment outperformance.

Current constituent snapshots are not point-in-time historical membership.
The strict historical backtest remains blocked until the required evidence is
available. Larger studies, controller training and validated historical-return
evaluation remain separate stages of the one-year project.

## Local API and safety

FastAPI binds only to loopback and rejects non-loopback Host headers. Browser
mutations require an explicit application header and a permitted local Origin.
Next.js exposes only an allowlist of same-origin routes; it limits JSON request
bodies to 64 KiB. The API never accepts arbitrary filesystem paths, remote
upstream URLs or browser-provided model paths.

This is a local research tool, not an authenticated multi-user service. Do not
bind these servers to all network interfaces, expose a tunnel or deploy publicly
without a separate authentication and security design. `Local engine` identifies
the execution mode, not a promise that the backend is currently reachable;
unavailable services display explicit errors and a retry action.

Run exports are generated from checksum-verified JSON, not an unverified stale
CSV file. Missing or modified records fail explicitly. Raw vendor price bundles
are not served through download endpoints and are not intended for redistribution.

## Checks

```sh
.venv/bin/pytest -q
.venv/bin/ruff check src tests app
.bootstrap/bin/uv lock --check
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

Frontend transport tests use queue/configuration metadata only. The result-view
test reads an authentic frozen run when present, and explicitly skips when that
private dataset fixture is unavailable. It does not invent financial output.
