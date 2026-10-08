# Q-Compass

**Quantum based portfolio optimization using QAOA under realistic investment constraints**

A working local research application using authentic NIFTY stock histories and
Qiskit Aer simulation. No trading, fabricated market observations or assumed
quantum advantage. Existing presentation and literature files are unchanged.

## Start here

### New Next.js interface

```sh
bash scripts/start-nextjs.sh
```

Open **http://127.0.0.1:3000**. The separate Next.js frontend routes through a
local Python API to the existing data, simulation engine and shared job queue.
See [frontend setup and routes](docs/nextjs-frontend.md).

### Original Streamlit interface (preserved)

From this project folder:

```sh
.venv/bin/python -m streamlit run app/dashboard.py
```

Open **http://127.0.0.1:8501**. The server binds only to this computer.

1. Open **Data audit** and inspect the frozen snapshot and exclusions.
2. Open **Experiment**, retain 8 candidates and 4 holdings, then click **Run experiment**.
3. When the worker finishes, refresh saved results. **Results** compares actual
   selections; **Controller** explains which configuration received more budget.
4. **Saved runs** replays results without recalculating. Export CSV or full JSON.

Python 3.12 and all dependencies are installed in this folder's isolated `.venv`.
System Python was not changed. Exact dependencies are in `uv.lock`.

## What works now

- Official 50-stock NSE membership CSV, original provider-returned price/action
  tables, Parquet records, audit failures and SHA-256 fingerprints.
- A frozen snapshot containing **92,859 validated daily rows across all 50 stocks**,
  January 2019–4 September 2026. Twelve invalid dated rows are quarantined,
  not filled; valid earlier histories remain available. The latest decision window
  has 38 eligible stocks after missing-session and unresolved-move exclusions.
- The available latest closes match the official NSE daily report for 38 stocks.
  This is a **single-session** cross-check, not certification of all past prices.
- Deterministic industry-spread candidate selection; 252-session past-only return
  estimation; shrinkage covariance; exactly-K and industry-count constraints.
- Exhaustive, greedy/local-swap and SCIP selection; common CVXPY allocation;
  continuous and joint classical allocation references; optional labelled repair.
- QUBO/Ising conversion with checked offsets/bit ordering. X/XY mixers, depths
  1–4, COBYLA/SPSA, mean/CVaR, optional simulated depolarizing noise, and a
  past-only JSON decision-tree/warm-start interface.
- Default fixed-depth and pilot-adaptive comparisons with **equal total quantum
  shot allowances**, including pilots and final sampling. Classical time is
  reported, not equated to one quantum evaluation.
- SQLite jobs, exclusive worker locking, cancellation between bounded operations,
  explicit interrupted-job restart, saved JSON/Parquet/CSV and replay checksums.
- Monthly execution accounting, drifting holdings, self-financing transaction
  costs, forced sales, and realized performance metrics for explicitly labelled
  fixed-universe studies. Missing liquidation quotes block a study.

## Important boundaries

**First milestone is implemented; the one-year research campaign is not finished.**

The current snapshot is not historical NIFTY membership. Strict historical runs
are blocked until full dated membership and corporate-action evidence are
verified. The strict replay core exists; the strategy bridge still needs a
verified point-in-time candidate constructor. Never toggle verification flags to
bypass that missing work.

The default dashboard uses **pilot-only adaptation**, not a secretly pretrained
market model. A model-training command and temporal guards exist, but a sound
2020–2022 training campaign, 2023 validation-selected fixed baseline, context
ablation and locked 2024–2025 evaluation remain research milestones. No speed-up,
better financial return, or publishable novelty is established by the small demo.

Stock selection uses an equal-weight risk–return proxy. A second classical stage
assigns continuous weights. This is **not an exact joint quantum solution**.
The joint classical reference is separately labelled.

## Reproduce

```sh
.venv/bin/qcompass datasets
.venv/bin/qcompass validate
.venv/bin/qcompass experiment --settings configs/demo.json
.venv/bin/qcompass replay RUN_ID
.venv/bin/qcompass reproduce RUN_ID
.venv/bin/qcompass experiment --settings configs/mixer-study.json
.venv/bin/qcompass batch configs/demo.json --seeds 11,42,73 --sizes 8
.venv/bin/qcompass resume-batch BATCH_ID
.venv/bin/qcompass report RUN_ID
.venv/bin/qcompass milestone --settings configs/objectives-1-2.json
.venv/bin/pytest -q
.venv/bin/ruff check src tests app
```

`reproduce` checks exact discrete selections, counts and shot/evaluation accounting.
Runtime will vary. Floating allocation output should be compared within the
documented 2e-5 feasibility tolerance. Every run stores code and package versions;
a changed code fingerprint is explicitly reported.

The pinned [Objectives 1 and 2 milestone guide](docs/objectives-1-2.md) explains
the two-run authentic-data evidence package, independent acceptance gates and
dashboard inspection checklist. The workflow being available is not itself a
completion claim: run the full pinned command and inspect its outputs first.

Verified demonstration: run `1bb5086703ca4ababcfca63356072d21` reproduced as
`053c1f3df7904b768383028532e16fbb` with identical discrete outputs. Its offline
report is in `artifacts/runs/1bb5086703ca4ababcfca63356072d21/report.html`.
All seven selection methods found the same best binary selection in this small
example. This does not establish a quantum advantage. Following the additive
Next.js upgrade, 70 Python tests and 20 frontend tests pass. Both desktop and
mobile Next.js workflows were inspected; Streamlit's source/config hashes remain
unchanged. Two upstream TestClient deprecation warnings remain in the Python
test output, without test failures.

For a fresh environment with `uv` available:

```sh
UV_PYTHON_INSTALL_DIR="$PWD/.tools/python" uv sync --frozen --python 3.12
```

This installation also includes project-local uv at `.bootstrap/bin/uv`.

## Data commands

```sh
.venv/bin/qcompass fetch --start 2019-01-01
.venv/bin/qcompass import-data /absolute/path/to/genuine-export-bundle
```

Downloads are new snapshots; old records are never overwritten. Yahoo Finance
is a secondary source, not an official NSE feed. Snapshot metadata and all file
hashes are bound together; modification blocks loading. Initial development
schema-1 metadata was preserved and sealed into a new schema-2 snapshot, with
integrity explicitly starting at seal time. Older result files remain readable;
new experiments require schema 2.

Raw vendor datasets are ignored by Git and are for local research. Do not
redistribute them without checking source rights. See [data provenance](docs/data-provenance.md).

## Historical study and controller development

```sh
# Strict mode: currently stops with an eligibility error, by design.
.venv/bin/qcompass backtest 2024-01-01 2025-12-31

# Explicitly different question: a current-universe study, NOT a bias-free index backtest.
.venv/bin/qcompass backtest 2022-01-01 2022-03-05 --fixed-universe

# A past-date optimization run is still current-universe research, not membership reconstruction.
.venv/bin/qcompass experiment --as-of 2022-06-30 --queue
.venv/bin/qcompass train-ranker --target-date 2023-01-01
```

The tree command uses only saved 2020–2022 quantum observations strictly before
the target date; labels are measured configuration outcomes, not exact-solver
answers. It refuses to invent training records. To use a trained JSON model,
set `ranker_path` in an experiment settings file. A learned recommendation's
benefit must be measured against pilot-only adaptation.

The fixed-universe study bridge reports turnover but does not enforce a turnover
limit. The allocation API supports previous holdings and a turnover limit; these
must be wired into a stateful historical decision loop before claiming that
particular constraint in a full strategy study. Cost scenarios replay identical
gross decisions at 0, 10 and 25 bps; they are not cost-retuned strategies.

## Project map

```text
app/dashboard.py          Streamlit interface, no optimizer calculations in widgets
frontend/                 Separate Next.js dashboard and same-origin API proxy
src/qcompass/api/          Loopback FastAPI adapter over existing data/jobs/results
scripts/start-nextjs.sh   Starts only Next.js and FastAPI; preserves Streamlit
src/qcompass/data/        Acquisition, import, validation, snapshots, past-only preparation
src/qcompass/portfolio/   Binary problem and investment constraints
src/qcompass/classical/   Reference selection, allocation and bounded repair
src/qcompass/quantum/     QUBO conversion, explicit circuits, Aer simulation
src/qcompass/adaptive/    Pilot allocation and past-only context ranker
src/qcompass/evaluation/  Strict eligibility, execution accounting, metrics and study bridge
src/qcompass/experiments/ SQLite worker and reproducible run records
src/qcompass/cli.py       Reproducible commands
configs/                 Small opt-in experiment profiles and historical split
data/raw/                Original source responses (not committed)
data/processed/          Validated Parquet (not committed)
data/manifests/          Source metadata and fingerprints (not committed)
artifacts/               Jobs, runs, model files and exports (not committed)
tests/                   Algebra, genuine-data, leakage, job and interface checks
docs/                    Beginner guide, provenance, implementation and research roadmap
```

## Laptop limits

One application/CLI simulation worker, four Aer threads, a 4096 MiB Aer memory
cap and a 20-**encoded**-qubit safeguard. Extra constraint variables count.
Timeouts/cancellation are cooperative between Aer jobs and network requests;
they are not an operating-system hard memory/time sandbox. A request for 20
assets can exceed the encoding cap and be rejected. Do not run quantum tests
simultaneously with a research job when measuring performance.

Next: [beginner walkthrough](docs/beginner-guide.md) ·
[remaining research plan](docs/research-roadmap.md) ·
[Objectives 1 and 2 milestone](docs/objectives-1-2.md) ·
[mathematics](docs/engine-report.md) · [historical accounting](docs/evaluation-report.md).
