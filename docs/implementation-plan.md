# Q-Compass implementation

Approved specification: user's six-stage Q-Compass plan, 5 September 2026.
Global constraints: authentic NIFTY data only; local CPU Qiskit Aer; no trading;
preserve existing literature files; count all pilot and post-processing costs;
never disclose future returns or exact optima to the controller; block strict
backtests without verified historical membership. Defaults: 252 sessions, 8 assets,
K=4, current frozen universe, train 2020–22 / validation 2023 / test 2024–25.

## Task 1: Mathematical engine
Implement typed portfolio instances, constraints, exact/greedy/SCIP selection,
CVXPY allocation and joint SCIP reference; QUBO/Ising conversion; seeded QAOA,
X/XY mixers, depths 1–4, COBYLA/SPSA, mean/CVaR, reusable prior starts;
budgeted pilot selection and past-only decision-tree ranking. Test first.

## Task 2: Authentic data and integration
Download official NIFTY identifiers, real Yahoo prices/actions, preserve source
responses and checksums, validate without interpolation, expose genuine source
file import. Freeze and verify snapshots. Build an eight-stock instance using
past-only aligned observations and covariance shrinkage. SQLite single-worker
jobs, immutable results, cancellation, replay and command line.

## Task 3: Historical evaluation
Implement next-session-close monthly execution, drift and explicit costs,
membership coverage gate, fixed-universe label, metrics and real-data tests.
No complete historical backtest claim without coverage evidence.

## Task 4: Dashboard and documentation
Streamlit/Plotly data audit, experiment setup, results, adaptive choices, saved
run replay, exports, architecture explanation. No invented performance values.
Verify browser interactions, reload, desktop/mobile layouts and empty states.

## Acceptance
Frozen authentic data and a successful seeded eight-stock comparison are required
for first-milestone completion. Tests cover input corruption, leakage, encoding,
feasibility, XY cardinality, cost accounting, execution lag and saved-run integrity.
Report long research sweeps and external data gaps separately from software delivery.
