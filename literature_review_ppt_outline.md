# Literature Review PPT Outline

Use the first 25 slides for the review narrative. Slides 26-31 are a compact paper appendix; the detailed viva notes remain in `literature_review_30_papers.md`.

1. **Title** — Quantum-Based Portfolio Optimization Using QAOA under Realistic Investment Constraints.
2. **Review mandate** — 30 papers: 25 from 2025-2026 plus five influential foundations from 2021-2024; indexed sources prioritized.
3. **Why the problem becomes difficult** — continuous Markowitz is manageable; discrete cardinality, sector and turnover rules create a combinatorial problem.
4. **Why study QAOA** — structured hybrid optimizer for QUBO/constraint-aware mixers; study competitiveness, not presumed quantum advantage.
5. **Selection and quality protocol** — search window, relevance, peer-review status, datasets, methods, findings and limitations; 26 peer-reviewed and four clearly labelled preprints.
6. **Map of the 30 papers** — objective, mixers/initialization, constraint conversion, resource reduction, end-to-end finance, benchmarking.
7. **Better objectives** — CVaR and higher-order moments add robustness but also sampling/circuit cost.
8. **Constraint-preserving search** — Dicke/XY/quantum-walk mixers improve feasibility; topology and initialization must align.
9. **Constraint conversion** — penalty/slack methods are flexible but cost qubits and require careful coefficient scaling.
10. **Resource reduction** — decomposition, hot starts and compressed encodings extend scale but transfer difficulty to preprocessing/decoding.
11. **End-to-end finance** — financial validity needs weights, rebalancing, transaction cost and out-of-sample evaluation.
12. **Benchmark reality check** — strong MIP/heuristics and noisy simulation prevent unsupported advantage claims.
13. **Repeated limitations** — small universes, synthetic/short data, isolated constraints, weak baselines, best-run reporting.
14. **Research gap** — limited controlled evidence across progressively tighter realistic constraints; configurations are rarely adapted from measured feasibility/convergence.
15. **Proposed contribution** — simulation-based Adaptive Constraint-Aware QAOA framework and reproducible constraint-regime benchmark.
16. **System workflow** — data -> QUBO -> pilot configurations -> diagnostic controller -> QAOA selection -> classical weights -> backtest.
17. **QUBO formulation** — risk-return, cardinality/sector penalties and turnover term.
18. **Constraint implementation** — mixers for exact rules; penalties/slack for inequalities; classical second stage for weights.
19. **Adaptive controller** — feasible-sample rate, objective gap and stagnation drive the next configuration.
20. **Dataset and platform** — frozen NIFTY 50, rolling windows, Qiskit Aer statevector/shot/noise simulations; no hardware claim.
21. **Experimental protocol** — exact/heuristic classical baselines, QAOA ablations, repeated seeds and identical instances.
22. **Evaluation metrics** — feasibility/optimality/resource measures plus return, volatility, Sharpe, drawdown, turnover and costs.
23. **One-year roadmap** — foundations and baselines -> constraints -> controller -> backtest -> robustness/reporting.
24. **Safe pivot ladder** — full adaptive framework; controlled benchmark; focused mixer/penalty study; decomposition/encoding extension.
25. **Conclusion and claim boundary** — determine which configuration works under which constraints in simulation; do not assume advantage.
26. **Papers 1-5** — CVaR, linear-depth VQE, real-world annealing, decomposition, PSO/XY QAOA.
27. **Papers 6-10** — discrete weights, higher-order QAOA, expert evaluation, sampling VQA, extensive benchmark.
28. **Papers 11-15** — slack constraints, end-to-end annealing, multi-constraint architecture, hot-start, Q-PORT.
29. **Papers 16-20** — direct indexing XY-QAOA, counterdiabatic QAOA, two-step QAOA, quantum walks, photonics.
30. **Papers 21-25** — noisy simulations, Pauli encoding portfolio/foundation, multiclass Dicke VQE, XY mixer algebra.
31. **Influential papers 26-30** — warm start, quantum-walk portfolio, QAOA benchmark, state/mixer alignment, knapsack QAOA.

## Presenter rule

For each literature slide, say: **what the cluster solved -> what it still misses -> how that changes our design**. Do not read the paper appendix row by row unless questioned.
