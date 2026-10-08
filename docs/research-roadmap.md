# From working application to one-year research project

## Keep the title; sharpen the question

**Question:** Under a fixed computational budget, when does context-aware and
pilot-adaptive QAOA improve feasible solution quality over fixed QAOA, pilot-only
tuning and equal-budget search on constrained portfolio-selection instances?

This is a hypothesis, not a novelty or advantage claim. Binary selection and
continuous weighting remain explicitly separate. Classical solvers can outperform
every quantum configuration; those results are publishable project evidence too.

| Approved stage | Present implementation | Remaining research / engineering |
|---|---|---|
| 1. Real data + complete small app | Working 8-stock comparison, adaptive explanation, 50 retained histories, dated quarantine, persistence and replay | Reconcile quarantined quotes and corporate actions; broaden cross-checks |
| 2. Mathematical foundation | Tested selection objectives, QUBO/Ising, exact/SCIP/greedy, CVXPY and joint reference | More instance sizes, constraint stress tests and conditioning diagnostics |
| 3. Quantum + adaptive | Mixers/depths/optimizers/CVaR/noise APIs, bounded pilots, temporal tree and reusable starts | Substantive training/validation campaign, context-ranking ablation, noise sweeps, validation-selected fixed baseline |
| 4. Validity + repair | Raw validity, common allocation, optional bounded repair with separate records/timing | Stateful prior holdings and turnover-limit integration in full historical strategy bridge |
| 5. Historical evaluation | Execution/fees/drift/metrics core, explicitly labelled fixed-universe bridge, strict blocker | Verified point-in-time membership/actions, point-in-time candidate construction, locked test campaign |
| 6. Reproducible application | Local worker, SQLite, small batch/resume commands, JSON/Parquet/CSV/HTML reports, source/package fingerprints, browser interface | Larger campaigns and publication packaging |

## Sequence for the next twelve months

| Months | Work |
|---|---|
| 1–2 | Learn the small demo; audit authentic data; hand-check objectives and constraints |
| 3–4 | Reproduce fixed QAOA/classical baselines; broaden encoding and feasibility tests |
| 5–6 | Run earlier-date training instances; train context tree; compare against pilot-only control |
| 7–8 | Validate allocation, turnover, optional repair, noise and constraint stress cases |
| 9–10 | Freeze settings on 2023 validation; execute locked 2024–2025 tests only after historical evidence is ready |
| 11–12 | Repeat seeds, uncertainty analysis, failure cases, reproducible report and final presentation |

Modules can be developed by team members concurrently, but changes must pass the
same tests before integration. Do not run concurrent simulations on this laptop
while collecting timing comparisons.

## Required comparisons

- Fixed standard QAOA and best fixed configuration selected only on validation data.
- Equal-total-shot configuration search, including all final sample batches.
- Pilot-only adaptive control.
- Context ranking without warm starts; then context ranking with warm starts.
- Raw output and separately labelled classical repair for every applicable method.
- Same allocation rules, certified selection reference where available, and
  separate joint classical allocation benchmark.

Charge tree preparation, parameter reuse preparation, pilot optimization, final
sampling, allocation and repair to their reported costs. Do not use penalized
quantum energies as financial scores across configurations.

## Data splits and research discipline

Use 2019 estimation history; 2020–2022 development/training; 2023 validation;
2024–2025 locked testing; later data as a separate extension. Freeze candidate
library, data fingerprints, costs, evaluation budgets and seed lists before
testing. Do not revise settings after inspecting locked test performance.

Use actual observations for market studies. Artificial device noise is allowed
only as explicitly labelled circuit-noise simulation, not invented financial data.
Small mathematical unit fixtures are not market datasets and are never shown as
financial performance in the dashboard.

## Stop conditions

- Missing quote, unexplained action or incomplete eligibility: affected experiment blocked.
- No valid portfolio: record failure, do not switch to the classical answer.
- Encoded-qubit/memory/time limit: report resource-limited status; do not hide failures.
- No measurable adaptive improvement: explain when and why it fails; retain negative findings.
