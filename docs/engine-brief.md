# Mathematical engine task brief

Implement only src/qcompass/portfolio, classical, quantum, adaptive and related
tests/test_engine*.py. Other agent owns data, experiments, CLI, app, pyproject.
No child agents. Use apply_patch. Do not commit other agents' files. Test first.
Environment will be installed into .venv with Python 3.12. Use .venv/bin/python.

## Contract (required)
Define in qcompass.portfolio.models:
PortfolioInstance dataclass fields: symbols: list[str], sectors: list[str],
mu: np.ndarray (annual), covariance: np.ndarray (annual), k: int,
sector_min: dict[str,int], sector_max: dict[str,int], risk_aversion: float=1.0,
as_of: str='', dataset_id: str='', features: dict[str,float] default empty.
Properties n; methods objective(bits) = risk_aversion*bits.T@covariance@bits/k**2
- mu@bits/k; violations(bits)->list[str]; feasible(bits)->bool;
to_dict()/from_dict() JSON safe. Validate dimensions, finite numbers, symmetric PSD
covariance and impossible constraints, explicit InfeasibleProblem(ValueError).

qcompass.classical.solvers: exact_select(instance), greedy_select(instance),
scip_select(instance,time_limit=30) -> dict with method,status,bits(list[int] or null),
objective(float or null),seconds,certified(bool),gap(optional). Exact enumeration
over choose(n,k) limited to manageable budget. SCIP epigraph for quadratic objective.
greedy/local swaps count method costs. No fake result on infeasibility.

qcompass.classical.weights: allocate(instance,bits, min_weight=0.05,max_weight=0.5,
sector_caps=None,previous_weights=None,turnover_limit=None,cost_bps=10)
-> dict status,weights(list aligned symbols or null),objective,seconds,violations.
Full investment long only, K-support only, bounds, sector-weight caps, previous
holdings INCLUDING assets outside new universe and turnover. Also continuous_mvo
and joint_select_weights SCIP references. Preserve constraint distinctions.
Optional repair_selection(instance,bits,max_candidates=200) bounded search, returns
raw and repaired separately; count time and do not silently relax constraints.

qcompass.quantum.model: build_qubo(instance,penalty_multiplier=1.0) returns an object
with operator SparsePauliOp, offset float, num_qubits, asset_indices, evaluate(bits),
decode(bitstring). Use QuadraticProgramToQubo correct constraints/slack bookkeeping.
Verify all binary energies for small instances against matrix and Ising energies.

qcompass.quantum.solver: QuantumConfig dataclass name,depth=1,mixer='x',optimizer='cobyla',
alpha=1.0,penalty_multiplier=1.0,initial_point=None,noise=0.0.
solve_qaoa(instance,config,evaluations=40,shots=1024,seed=42,initial_point=None,
progress=None,cancel=None,max_seconds=300) -> dict with method,status,bits,objective,
seconds,feasible_fraction,shots_used,evaluations,num_qubits,depth,parameters,
trace(list),counts(dict),config(JSON),metadata; extra fields okay.
Budget is objective evaluations (explicit wrapper, including rejected optimizer
requests), final sampling measured separately. Seeds stable. Aer CPU four threads,
memory cap4096MB, refuse >20 encoded qubits by default. Progress callback takes dict;
cancel callable returns bool. Use Qiskit Optimization 0.7 current namespaces or
explicit Qiskit circuits, not obsolete qiskit.algorithms APIs.
X mixer standard uniform start. XY asset register preserves exactly K and uses
deterministic feasible computational start (not exponential generic state prep),
independent X mixers on slack bits; report sector constraints not guaranteed by XY.
CVaR aggregation and SPSA supported, isolated noise studies real financial input.

qcompass.adaptive.controller: adaptive_solve(instance,configs=None,evaluations=60,
pilot_evaluations=10,shots=1024,seed=42,progress=None,cancel=None,max_seconds=300,
ranker=None) -> solver-result dict plus pilots and decision text, total costs.
Default depth1 and depth2 X configurations. Pilot both then continue chosen
parameters with remaining total evaluations. Compare original feasible objectives,
not penalized energies across configs; no exact oracle. Include ALL pilot final
sampling and continuation costs. Expose config library depth1–4 X/XY/COBYLA/SPSA/CVaR.
Ranker class fits shallow decision tree on earlier records; reject records not
strictly before target as_of or from test split, serialize JSON safe (no arbitrary
pickle). Warm starts only from prior training dates and dimension-compatible configs.

## Tests and evidence
Write tests first and run red before implementation. Pure numerical algebra tests
are permitted, but NEVER create mock market price data. Real market tests can use
the dataset provided by parent (message when available). Test encoding offsets and
endian, feasibility, exact vs SCIP, weights including forced sales, seeded simulator,
XY preservation, adaptation budget/cancel and no future data in ranker.
Report to docs/engine-report.md with exact test commands/outcomes and public API.
