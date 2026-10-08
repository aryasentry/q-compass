# Q-Compass mathematical engine implementation evidence

Implemented in `src/qcompass/{portfolio,classical,quantum,adaptive}`. Tests are
hand-checkable mathematical vectors/covariances, not generated financial prices.
No claims of market performance or quantum advantage follow from these tests.

## Public API

- `portfolio.models.PortfolioInstance` and `InfeasibleProblem`: brief-compatible
  dataclass, validated dimensions, finite moments, symmetric PSD covariance,
  feasible partition-sector count bounds, original equal-weight objective,
  selection violations and JSON-safe serialization.
- `classical.solvers.exact_select(instance, max_combinations=1_000_000)`,
  `greedy_select(instance)`, `scip_select(instance, time_limit=30)`. Exact enumerates
  feasible K-subsets within the explicit combination cap. Greedy satisfies sector
  minima first and performs improving feasible swaps; evaluation costs are counted.
  SCIP uses a quadratic epigraph and reports actual solver status/gap/certificate.
- `classical.weights.allocate(...)`, `continuous_mvo(...)`,
  `joint_select_weights(..., time_limit=30)`, `repair_selection(...)`.
  Conditional allocation uses CVXPY/CLARABEL, exact support and weight/sector caps.
  Continuous MVO explicitly omits K and sector-count constraints. Joint SCIP
  includes selection/count constraints and bounded positive selected weights.
  Bounded repair returns raw and repaired outcomes separately, plus total cost.
- `quantum.model.build_qubo(...)`: Qiskit Optimization `QuadraticProgramToQubo`,
  explicit penalty, SparsePauliOp + offset, asset/slack mapping, binary energy and
  MSB-left count-string decoding. Multiplier >=1 uses a penalty exceeding the
  full objective range; smaller multipliers intentionally lack that guarantee.
- `quantum.solver.QuantumConfig`, `solve_qaoa(...)`, `build_circuit(...)`.
  Explicit Qiskit 2 circuits; Aer CPU statevector simulation, 4 threads, 4096 MB,
  default encoded-qubit cap 20. X uniform start, or deterministic feasible basis
  state with asset-register XX+YY mixers and independent X slack mixers. XY
  preserves cardinality in noiseless simulation; it does not enforce sectors.
  COBYLA and SPSA, CVaR, seeded depolarizing noise, trace/progress and cancellation.
- `adaptive.controller.adaptive_solve(...)`, `configuration_library()` and
  `TemporalRanker`: pilot all allowed configurations, rank by original feasible
  objective and feasible fraction, continue chosen parameters. Default p1/p2 X;
  library has p1-p4 X/XY, COBYLA/SPSA, mean/CVaR combinations. Ranker is a shallow
  sklearn classification tree exported/imported as JSON arrays, never pickle.

## Important accounting and constraint conventions

Turnover is half L1 change across the union of prior and current assets, including
outside-universe forced sales. Fees apply to total traded notional (2 * turnover).
Previous holdings must be fully invested, finite and long only; use a symbol
dictionary to preserve names outside the current universe. No previous holdings
means initial construction, with no estimated rebalance fee or turnover. A
turnover limit without previous holdings is an input error.

`evaluations` counts completed shot-based objective calls. The objective wrapper
enforces the cap even when COBYLA requests its own larger minimum. All requests,
including rejected budget/time/cancel requests, are additionally counted in
`metadata.optimizer_requests`. `shots_used` includes optimization shots and final
sampling. Standalone final samples/timing are in `metadata.final_sampling_shots`
and `final_sampling_seconds`; adaptive totals also expose `total_*` fields and
include every pilot and continuation. Adaptive returned counts, parameters and
objective belong to the winning sampled run; continuation parameters are separately
recorded in metadata. No exact solution is consulted by the adaptive controller.

Ranker records require `as_of`, `split='train'`, `features`, `best_config`. Every
training date must strictly precede the target date, both at fit and inference.
Warm starts additionally require matching `n`, `num_qubits`, configuration depth,
mixer, CVaR alpha and penalty multiplier, with two finite angles per layer.

## Test evidence

Initial RED command:
`.venv/bin/python -m pytest tests/test_engine.py -q`

Observed **7 failed** because the seven engine entry points had not yet been
implemented. Then implemented production code and reran tests.

Additional RED checks exposed fractional binary-vector truncation and missing
encoded-dimension checks for warm starts; both fixed. A seeded adaptive test also
exposed a mismatch between winning pilot samples and continuation parameters;
the result now retains parameters corresponding to its actual returned samples.

Final command:
`.venv/bin/python -m pytest tests/test_engine.py -q`

Observed **10 passed in 1.59 seconds**, no warnings. Coverage:
objective and JSON roundtrip; impossible constraints/non-PSD rejection;
exact/SCIP optimum equivalence; greedy feasibility; conditional/continuous/joint
allocation and forced sales; exhaustive Ising/QUBO diagonal and endian checks,
including a slack-register inequality instance; seeded XY cardinality and cost
accounting; CVaR tail aggregation; actual noisy Aer execution; qubit cap;
adaptive total budget/cancel and sample-to-parameter correspondence; ranker
chronology, JSON roundtrip and compatible warm-start selection.

`.venv/bin/ruff check src/qcompass/portfolio src/qcompass/classical src/qcompass/quantum src/qcompass/adaptive tests/test_engine.py`

Observed **All checks passed** after standard Ruff formatting.

## Authentic market-data integration

Executed the actual snapshot `nifty50-20260905T080605-28fd98` via
`qcompass.data.prepare.build_instance(dataset_id, n=8, k=4)`, dated 2026-09-04,
using 252 return observations. Symbols: HDFCBANK, INFY, MAXHEALTH, EICHERMOT,
SBIN, WIPRO, SUNPHARMA, MARUTI. No missing prices were synthesized.

`solve_qaoa(instance, QuantumConfig('real-xy-p1', mixer='xy', optimizer='spsa'),
evaluations=6, shots=128, seed=42)` completed on 8 encoded qubits with 896 total
shots, feasible fraction 0.46875, and objective -0.1157606354764529 in approximately
0.054 seconds. It selected INFY, EICHERMOT, SBIN, SUNPHARMA. Exact enumeration
(16 feasible subsets) and SCIP independently found the same objective; SCIP
reported optimal status and zero gap. This single sample outcome does not
establish algorithmic advantage or general convergence.

Conditional allocation was optimal with no violations: approximately 5% INFY,
32.38% EICHERMOT, 50% SBIN, 12.62% SUNPHARMA. Its optimized-weight objective
-0.21106482223654693 is a different problem from equal-weight subset selection.

Repeatable integration test:
`.venv/bin/python -m pytest tests/test_engine.py tests/test_engine_realdata.py -q`

Observed **11 passed in 2.20 seconds**. Ruff over all owned modules and both engine
test files also passed.

## Limits and integration checks remaining

- The authentic integration uses a current membership snapshot. It is an
  optimization demonstration, not a survivorship-bias-free historical backtest.
- Time limits/cancellation are checked between simulator jobs, not by killing a
  running Aer call. A single job/transpilation may exceed the requested wall time.
- Noisy statevector trajectories can cost substantially more than noiseless
  sampling. The default 20-qubit cap applies to assets plus encoded slack bits.
- Selection is the equal-weight objective; optimized continuous allocation and
  its costs are a separate problem and must not share optimality-gap claims.
- Shallow ranker execution is implemented; useful out-of-sample predictions or
  adaptive advantage require actual chronology-respecting training/evaluation.
