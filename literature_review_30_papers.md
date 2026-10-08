# Literature Review Study Package

## Project title

**Quantum-Based Portfolio Optimization Using QAOA Under Realistic Investment Constraints**

## Recommended internal problem statement

To design and simulate an adaptive, constraint-aware QAOA framework for discrete portfolio selection under cardinality, sector-diversification, budget and turnover constraints, and to determine how constraint tightness affects feasibility, solution quality and computational cost relative to exact and heuristic classical solvers.

The public title can remain unchanged. In the report and presentation, describe the work as a **simulation-based, constraint-regime benchmark with adaptive QAOA configuration**. Do not claim hardware execution or quantum advantage.

## Literature-selection rule

- Papers 1-25 were published or first made public from January 2025 onward.
- Papers 26-30 are the five influential exceptions from 2021-2024.
- **Peer-reviewed** means a journal, indexed conference or Springer proceedings paper.
- **Preprint** means the work is useful and recent but has not been verified here as peer-reviewed. Never present a preprint as an IEEE, Springer or journal publication.
- Dates, titles, venues and identifiers were checked against publisher, DOI or arXiv records on 19 August 2026.

## How to read the notes

For each paper, learn four sentences first: the plain-language explanation, what it changed, its strongest result, and what it failed to cover. The longer bullets provide the problem, workflow, data, limitation and connection required by the department.

---

## 1. Improved Quantum Approximate Optimization Algorithm Based on Conditional Value-at-Risk for Portfolio Optimization

- **Year/status/source:** 2025, peer-reviewed, *IEICE Transactions on Information and Systems*, E108.D(7), 727-733.
- **DOI and access:** [10.1587/transinf.2024EDP7254](https://doi.org/10.1587/transinf.2024EDP7254); [free publisher page](https://www.jstage.jst.go.jp/article/transinf/E108.D/7/E108.D_2024EDP7254/_article).
- **Problem/gap:** Ordinary QAOA averages the energy of all sampled portfolios. Poor samples can dominate that average and slow convergence.
- **Objective:** Improve QAOA convergence by emphasizing the best tail of measured solutions through Conditional Value-at-Risk (CVaR) and a modified ansatz.
- **Method/workflow:** Historical returns and covariance -> portfolio QUBO -> enhanced QAOA circuit -> CVaR aggregation -> classical parameter optimization -> select the lowest-cost portfolio.
- **Data:** Historical Nasdaq stock data; experiments with 10, 12, 14 and 16 stocks.
- **Key finding:** The improved CVaR-QAOA converged within 100 iterations in the reported cases, while standard QAOA required 450 or more.
- **Limitation/future:** Small universes, limited constraint variety and simulation-oriented evaluation; it does not study sector limits or constraint-tightness regimes.
- **In simple language:** Instead of judging a QAOA run by every answer it produces, judge it mainly by its best answers.
- **Use in our project:** Compare expectation-value and CVaR objectives, but measure whether CVaR also improves feasible-solution probability under tighter constraints.

## 2. Variational Quantum Eigensolver with Linear Depth Problem-Inspired Ansatz for Solving Portfolio Optimization in Finance

- **Year/status/source:** 2025, peer-reviewed, *Science China Information Sciences*, 68.
- **DOI and access:** [10.1007/s11432-024-4185-1](https://doi.org/10.1007/s11432-024-4185-1); [arXiv copy](https://arxiv.org/abs/2403.04296).
- **Problem/gap:** Hardware-efficient variational circuits can become too deep or too expressive to train reliably as portfolio size grows.
- **Objective:** Build shallow, problem-inspired Dicke-state ansatzes that respect fixed-cardinality structure and can be distributed across smaller quantum fragments.
- **Method/workflow:** Portfolio Hamiltonian -> Dicke-state ansatz -> CVaR-VQE -> simultaneous sampling, error mitigation and fragment reuse -> hybrid distributed computation.
- **Data:** Portfolio instances derived from financial return/covariance inputs; simulations plus reported experiments up to 55 qubits on the Wu Kong superconducting system.
- **Key finding:** Restricted expressibility and linear-depth structure improved trainability and enabled larger demonstrations than a conventional monolithic circuit.
- **Limitation/future:** It focuses on VQE and hardware-resource engineering, not a matched comparison of realistic portfolio constraints or out-of-sample investment performance.
- **In simple language:** A circuit designed around the portfolio's fixed-number-of-assets rule can be easier to train than a generic circuit.
- **Use in our project:** Supports Dicke-state initialization and warns that “more expressive” is not automatically better.

## 3. A Real-World Test of Portfolio Optimization with Quantum Annealing

- **Year/status/source:** 2025, peer-reviewed, *Quantum Machine Intelligence*, 7, article 43.
- **DOI and access:** [10.1007/s42484-025-00268-2](https://doi.org/10.1007/s42484-025-00268-2).
- **Problem/gap:** Many quantum-finance demonstrations use toy data and easy constraints rather than an optimization problem used by a financial institution.
- **Objective:** Test a QUBO formulation and automatic penalty tuning on a real bank portfolio problem.
- **Method/workflow:** Production portfolio constraints -> QUBO including a variance-threshold constraint -> D-Wave hybrid solvers and classical solver -> compare with the exact classical optimum -> tune QUBO coefficients automatically.
- **Data:** A Raiffeisen Bank International production-style portfolio with equity, fixed-income and money-market classes; typical instances contain 9-11 assets. Confidential financial details are not fully public.
- **Key finding:** Hybrid annealing produced satisfactory solutions consistent with the classical optimum, but parameter tuning was decisive.
- **Limitation/future:** Quantum annealing is not gate-model QAOA; the instance is small and partially proprietary, limiting reproducibility.
- **In simple language:** On a genuine bank-shaped problem, the mathematical encoding and penalties mattered as much as the solver.
- **Use in our project:** Justifies adaptive penalty tuning and transparent public datasets rather than proprietary inputs.

## 4. Decomposition Pipeline for Large-Scale Portfolio Optimization with Applications to Near-Term Quantum Computing

- **Year/status/source:** 2025, peer-reviewed, *Physical Review Research*, 7, 023142.
- **DOI and access:** [10.1103/PhysRevResearch.7.023142](https://doi.org/10.1103/PhysRevResearch.7.023142); [free PDF](https://journals.aps.org/prresearch/pdf/10.1103/PhysRevResearch.7.023142).
- **Problem/gap:** Real portfolios can contain hundreds or thousands of variables, while quantum and exact classical solvers struggle with a single large constrained model.
- **Objective:** Divide a large portfolio problem into smaller, structurally meaningful subproblems without destroying most of its financial information.
- **Method/workflow:** Clean the correlation matrix using random-matrix theory -> modified spectral clustering -> solve independent constrained subproblems -> risk rebalance and aggregate -> feasibility check.
- **Data:** S&P 500 market data, Russell 3000-derived data and randomly generated covariance instances; experiments include problems up to roughly 1,500 variables.
- **Key finding:** Subproblem sizes were reduced by about 80% and the largest tested classical cases obtained at least a threefold time improvement.
- **Limitation/future:** It is a preprocessing/decomposition study; it does not establish that QAOA solves the resulting subproblems better.
- **In simple language:** Group highly related assets first, optimize smaller groups, and then combine them.
- **Use in our project:** A safe year-two-style pivot if full-universe simulation becomes impossible, without changing the project title.

## 5. Quantum Alternating Operator Ansatz with PSO Optimizer for Portfolio Optimization Problem

- **Year/status/source:** 2025, peer-reviewed, *Applied Soft Computing*, 181, 113419.
- **DOI and access:** [10.1016/j.asoc.2025.113419](https://doi.org/10.1016/j.asoc.2025.113419); [publisher page](https://www.sciencedirect.com/science/article/pii/S1568494625007306); [code](https://github.com/wqs1999/QAOA-Portfolio).
- **Problem/gap:** Mean-variance is not the only portfolio model; risk-parity objectives create higher-order interactions and are harder to encode and optimize.
- **Objective:** Construct a QAOAz solution for risk-parity portfolios and improve parameter search using particle swarm optimization (PSO).
- **Method/workflow:** Risk-parity or mean-variance objective -> higher-order problem Hamiltonian with parity-check construction -> ring XY mixer -> PSO tunes circuit angles -> compare with quantum and classical heuristics.
- **Data:** Eight portfolios from Chinese, US and European financial markets; data and code are linked by the authors.
- **Key finding:** The reported PSO-QAOAz risk-parity method outperformed ABC-LP, grey-wolf optimization, a genetic algorithm and ordinary QAOAz; for mean-variance it improved the reported approximation ratio over QAOA and QAOAz.
- **Limitation/future:** Broad markets but still modest encoded instances; comparison with exact MIQP and realistic trading constraints is limited.
- **In simple language:** A population-based classical optimizer can tune QAOA angles better than a default local optimizer on some portfolio landscapes.
- **Use in our project:** Include optimizer choice as an ablation, but do not let PSO multiply the experimental scope until the baseline works.

## 6. Solving Multiple Discretization Portfolio Optimization Problem with Quantum-Classical Hybrid Algorithms

- **Year/status/source:** First online 2025, peer-reviewed, *Computational Economics*; volume 68(1), 227-256 (2026 issue).
- **DOI and access:** [10.1007/s10614-025-11061-5](https://doi.org/10.1007/s10614-025-11061-5); [publisher page](https://link.springer.com/article/10.1007/s10614-025-11061-5).
- **Problem/gap:** Real portfolios can mix continuously divisible assets, discrete assets and non-fungible assets; a single binary inclusion variable is too simplistic.
- **Objective:** Formulate multiple asset discretizations, budget and number-of-assets constraints in a common QUBO/hybrid framework.
- **Method/workflow:** Convert asset quantities into binary variables at appropriate resolutions -> add budget/cardinality slack penalties -> solve with VQE/QAOA-inspired hybrid methods and classical algorithms -> backtest.
- **Data:** Dataset 1 contains 10 Shanghai/Shenzhen stocks from 1 September to 31 December 2021. Dataset 2 contains 15 stocks, public funds and private funds from 19 January to 9 April 2024, sourced from WIND and exchanges.
- **Key finding:** The framework represents heterogeneous investment units and produced competitive results against the tested classical methods.
- **Limitation/future:** Binary discretization and slack variables require many qubits; the market windows are short and private-fund data reduces easy reproducibility.
- **In simple language:** Some assets can be bought in tiny fractions and others only in large chunks; the encoding must represent both.
- **Use in our project:** Keep the first implementation binary-selection based, but cite this as the route to integer quantities later.

## 7. Higher-Order Portfolio Optimization with Quantum Approximate Optimization Algorithm

- **Year/status/source:** 2025, peer-reviewed conference paper, IEEE Quantum Week/QCE 2025.
- **DOI and access:** [10.1109/QCE65121.2025.00244](https://doi.org/10.1109/QCE65121.2025.00244); [author PDF](https://amor.cms.hu-berlin.de/~zhaobo/QCE25-HUBO-QAOA.pdf).
- **Problem/gap:** Mean and variance miss skewness and fat tails, while realistic capital budgets involve integer quantities and higher-order objective terms.
- **Objective:** Formulate skewness and kurtosis portfolio objectives as a higher-order unconstrained binary optimization (HUBO) and solve them directly with higher-order QAOA circuits.
- **Method/workflow:** Compute mean, covariance, co-skewness and co-kurtosis -> encode integer quantities and a capital budget -> map HUBO Pauli terms -> QAOA simulation -> compare with continuous classical allocation.
- **Data:** Ten years of market data from 1 January 2015 to 1 January 2025; worked examples include Disney and Travelers, with experiments extending to roughly 15 qubits.
- **Key finding:** It demonstrates a direct quantum formulation for third- and fourth-moment portfolio objectives and exposes the cost of realistic capital encoding.
- **Limitation/future:** Small simulated instances, difficult penalty selection and rapidly increasing gate/term counts; higher moments are statistically noisy to estimate.
- **In simple language:** It models asymmetric and extreme returns, not just average return and variance, but pays for realism with a much harder circuit.
- **Use in our project:** Treat skewness/kurtosis as optional future work, not part of the minimum viable thesis.

## 8. Quantum Portfolio Optimization with Expert Analysis Evaluation

- **Year/status/source:** 2025, peer-reviewed conference paper, IEEE Quantum Week/QCE 2025, pp. 326-331.
- **DOI and access:** [10.1109/QCE65121.2025.10344](https://doi.org/10.1109/QCE65121.2025.10344); [arXiv copy](https://arxiv.org/abs/2507.20532).
- **Problem/gap:** A low QUBO energy does not guarantee a diversified, financially reasonable or forward-performing portfolio.
- **Objective:** Benchmark VQE/QAOA configurations and add an expert-finance evaluation after mathematical optimization.
- **Method/workflow:** Yahoo Finance data -> four- and ten-asset portfolio QUBOs -> test ansatz types and depths -> examine selected portfolios using diversification, risk and a following-period return check.
- **Data:** Historical Yahoo Finance prices for selected large US stocks over a six-month 2025 window, followed by a June 2025 evaluation.
- **Key finding:** Deeper circuits sometimes improved portfolio choices, but numerical convergence alone often produced economically weak portfolios.
- **Limitation/future:** Very short horizon, tiny universes and subjective expert assessment; it is not a controlled out-of-sample backtest.
- **In simple language:** A mathematically “best” answer can still be a bad investment.
- **Use in our project:** Report Sharpe ratio, drawdown, diversification and turnover in addition to QUBO energy and optimality gap.

## 9. Portfolio Construction Using a Sampling-Based Variational Quantum Scheme

- **Year/status/source:** 2025, **preprint**, IBM/Vanguard collaboration, arXiv:2508.13557.
- **Access:** [arXiv](https://arxiv.org/abs/2508.13557); [IBM research explanation](https://www.ibm.com/quantum/blog/vanguard-portfolio-optimization).
- **Problem/gap:** Practical ETF construction contains complex inequality and compliance constraints that introduce costly slack variables in standard QUBOs.
- **Objective:** Use a sampling-based CVaR variational algorithm whose cost and constraint violations are evaluated classically, followed by local search.
- **Method/workflow:** Binary ETF proposal -> variational circuit samples -> classically compute arbitrary constrained cost -> CVaR optimization -> one-bit local-search polishing -> compare with CPLEX.
- **Data:** A simplified but realistic bond-ETF design instance supplied through the IBM/Vanguard study; 31-qubit matrix-product-state simulation and reported hardware experiments up to 109 qubits.
- **Key finding:** The best reported quantum-plus-local-search result was within 0.49% of the CPLEX optimum, and trained samples improved local search over starting local search alone.
- **Limitation/future:** Preprint, proprietary/simplified financial instance and hardware-centered resource requirements; it does not prove quantum advantage.
- **In simple language:** Let the quantum circuit propose candidates, then let classical code check complicated rules and improve nearby answers.
- **Use in our project:** Strong support for hybrid post-processing and for keeping all constraint checking explicit and auditable.

## 10. Quantum Portfolio Optimization: An Extensive Benchmark

- **Year/status/source:** 2025, **preprint**, arXiv:2509.17876 (revised 2026).
- **Access:** [arXiv](https://arxiv.org/abs/2509.17876).
- **Problem/gap:** Earlier work lacked a large, common benchmark against strong exact and problem-specific classical algorithms.
- **Objective:** Test whether quantum annealing or QAOA leaves meaningful room for advantage on difficult real-data portfolio instances.
- **Method/workflow:** Build three portfolio model families -> generate 250 real-data instances -> compare MIP, simulated annealing, steepest descent, tabu search, a tailored heuristic, quantum annealing and QAOA -> measure quality and time.
- **Data:** Nasdaq stock data from 2020-2023; 250 instances containing up to 1,000 assets. Quantum methods were restricted to at most 30 assets.
- **Key finding:** MIP proved all tested optima in seconds and the tailored heuristic consistently beat the tested quantum methods at fixed runtime.
- **Limitation/future:** Preprint; its QAOA scale is far below the full benchmark and it does not isolate gradual sector/cardinality tightness under one controlled protocol.
- **In simple language:** Strong classical solvers are much harder to beat than most quantum demonstrations admit.
- **Use in our project:** This paper requires an honest classical baseline and changes our goal from “prove advantage” to “map performance boundaries.”

## 11. A Quantum Model for Constrained Markowitz Modern Portfolio Using Slack Variables to Process Mixed-Binary Optimization under QAOA

- **Year/status/source:** 2025, peer-reviewed, *Quantum Machine Intelligence*. DOI: `10.1007/s42484-025-00330-z`. A later author manuscript is arXiv:2601.03278.
- **Access:** [Springer](https://doi.org/10.1007/s42484-025-00330-z); [free manuscript](https://arxiv.org/abs/2601.03278).
- **Problem/gap:** Budget and bound inequalities do not naturally fit an unconstrained QUBO.
- **Objective:** Convert a mixed-binary Markowitz model into a QAOA-compatible model using binary slack variables.
- **Method/workflow:** Express inequalities as equalities with slack bits -> add penalty terms -> construct the cost Hamiltonian -> run QAOA on synthetic instances.
- **Data:** Synthetic return and covariance inputs for small portfolios.
- **Key finding:** The slack-variable construction found the reference optimum on tested cases where a simpler penalty-QAOA formulation failed.
- **Limitation/future:** Slack variables consume extra qubits, penalty scaling is delicate, and only tiny simulated cases were studied.
- **In simple language:** Extra binary variables act like a receipt showing how much of each limit remains unused.
- **Use in our project:** Use slack variables only for inequalities that cannot be enforced by a mixer, and report their qubit cost.

## 12. End-to-End Portfolio Optimization with Hybrid Quantum Annealing

- **Year/status/source:** 2026, peer-reviewed, *Advanced Quantum Technologies*. DOI: `10.1002/qute.202500753`; first preprint in 2025.
- **Access:** [Wiley](https://doi.org/10.1002/qute.202500753); [free manuscript](https://arxiv.org/abs/2504.08843).
- **Problem/gap:** Many quantum papers stop at asset selection and never test portfolio construction and rebalancing end to end.
- **Objective:** Combine quantum-annealing selection with classical weight optimization and repeated rebalancing.
- **Method/workflow:** Rank/select assets with annealing -> optimize continuous weights classically -> rebalance quarterly -> compare financial outcomes.
- **Data:** Indian equity-market style/NIFTY data, with additional synthetic analysis and a fund-manager comparison described by the authors.
- **Key finding:** A hybrid workflow can be evaluated as an investment process, not merely as a single QUBO solve.
- **Limitation/future:** It uses annealing rather than QAOA; results depend on data-period and benchmark choices and do not establish quantum advantage.
- **In simple language:** Choosing stocks is only half the job; the system must also decide weights and when to rebalance.
- **Use in our project:** Adopt the same end-to-end discipline: QAOA for selection, classical optimization for weights, and an out-of-sample backtest.

## 13. Efficient QAOA Architecture for Solving Multi-Constrained Optimization Problems

- **Year/status/source:** 2025, peer-reviewed, *IEEE International Conference on Quantum Computing and Engineering (QCE)*. DOI: `10.1109/QCE65121.2025.00048`.
- **Access:** [IEEE](https://doi.org/10.1109/QCE65121.2025.00048); [free manuscript](https://arxiv.org/abs/2506.03115).
- **Problem/gap:** Standard penalty QAOA wastes probability on infeasible states when several equality and inequality constraints interact.
- **Objective:** Build a QAOA architecture that preserves one-hot equalities with XY mixers and detects inequalities with an oracle-like indicator.
- **Method/workflow:** Feasible initialization -> constraint-specific XY mixing -> inequality indicator circuit -> QAOA -> time-to-solution evaluation.
- **Data:** Synthetic multidimensional-knapsack and energy/prosumer allocation instances rather than financial data.
- **Key finding:** The proposed architecture reported more than an order-of-magnitude improvement in time to solution on selected instances.
- **Limitation/future:** Indicator circuits and controlled operations add depth; evidence is not portfolio-specific and remains small-scale.
- **In simple language:** Some rules are built into how the algorithm moves, so it does not keep proposing illegal answers.
- **Use in our project:** Motivates a hybrid design: mixers for exact selection rules, penalties/slack for the remaining inequalities.

## 14. Hot-Starting Quantum Portfolio Optimization

- **Year/status/source:** QUEST-IS 2025 proceedings, published online in 2026, Springer CCIS 2744. DOI: `10.1007/978-3-032-13855-2_3`.
- **Access:** [Springer](https://doi.org/10.1007/978-3-032-13855-2_3); [free manuscript](https://arxiv.org/abs/2510.11153).
- **Problem/gap:** Fine-grained discrete portfolio weights require too many qubits and create a large search space.
- **Objective:** Use the solution of a continuous portfolio relaxation to restrict each asset's allowed integer weights before QAOA.
- **Method/workflow:** Solve continuous Markowitz model -> build lower/upper bounds around its weights -> encode only that reduced interval -> warm/hot-start QAOA.
- **Data:** S&P 500/Refinitiv data from August 2003 to July 2023, demonstrated on small asset subsets.
- **Key finding:** In a four-asset illustration, interval restriction reduced an encoding described as 40 qubits to 6 qubits.
- **Limitation/future:** The continuous solution may exclude the best discrete solution; demonstrations are tiny and include hardware-specific discussion.
- **In simple language:** First ask a classical solver where the good neighbourhood is, then let QAOA search only there.
- **Use in our project:** A useful later pivot if binary asset selection is replaced by discrete weights; not required for the first prototype.

## 15. Q-PORT: Quantum Portfolio Optimization with Resource-Efficient Encoding and Scalability Analysis

- **Year/status/source:** QUEST-IS 2025 proceedings, published online in 2026, Springer CCIS 2743. DOI: `10.1007/978-3-032-13852-1_34`.
- **Access:** [Springer](https://link.springer.com/chapter/10.1007/978-3-032-13852-1_34).
- **Problem/gap:** Conventional encodings normally need at least one qubit per stock and therefore scale poorly.
- **Objective:** Explore encodings in which one qubit represents multiple stocks and quantify precision-versus-resource trade-offs.
- **Method/workflow:** Compare multi-stock-per-qubit and multi-qubit-per-stock encodings -> simulate portfolio instances -> analyse accuracy and qubit count.
- **Data:** Small portfolio simulations used for encoding and scalability analysis.
- **Key finding:** Packing multiple stocks into each qubit saved resources, while allocating more qubits per stock provided only small precision gains in the reported tests.
- **Limitation/future:** Compressed encodings require nontrivial decoding and can restrict which constraints or interactions are easy to express.
- **In simple language:** It tries to make every simulated qubit carry more information.
- **Use in our project:** Cite as a scaling direction, but keep one binary variable per asset initially so constraint logic remains explainable.

## 16. Constrained Portfolio Optimization via QAOA with XY-Mixers and Trotterized Initialization: A Hybrid Approach for Direct Indexing

- **Year/status/source:** 2026, **preprint**, arXiv:2602.14827.
- **Access:** [arXiv](https://arxiv.org/abs/2602.14827).
- **Problem/gap:** Direct-index portfolios must hold exactly a chosen number of stocks, but penalty-based QAOA frequently samples the wrong cardinality.
- **Objective:** Enforce exact cardinality using feasible initialization and an XY mixer, then compare with classical portfolio methods.
- **Method/workflow:** Build a ten-stock direct-index instance -> initialize a fixed-Hamming-weight state using a Trotterized procedure -> run XY-QAOA -> walk-forward backtest.
- **Data:** Yahoo Finance prices for 10 stocks, selecting `K=5`, with a 2025 walk-forward evaluation.
- **Key finding:** The paper reports 30.09% return and Sharpe 1.81, above its simulated-annealing and hierarchical-risk-parity comparisons.
- **Limitation/future:** One small universe and one test period; reported turnover was 76.8%, which could erase gains after realistic costs; preprint evidence needs replication.
- **In simple language:** It always swaps one selected stock for another, so the portfolio never holds the wrong number.
- **Use in our project:** This is the closest baseline for our cardinality implementation and shows why turnover must be a first-class metric.

## 17. Constrained Counterdiabatic QAOA for Portfolio Optimization

- **Year/status/source:** 2026, **preprint**, arXiv:2605.06858.
- **Access:** [arXiv](https://arxiv.org/abs/2605.06858).
- **Problem/gap:** Shallow, constraint-preserving QAOA can converge slowly or become trapped in poor parts of the feasible subspace.
- **Objective:** Add counterdiabatic terms intended to speed movement toward good feasible portfolios at low depth.
- **Method/workflow:** Dicke-state initialization -> XY constraint mixer -> counterdiabatic operators -> compare approximation ratio and feasibility against constrained QAOA.
- **Data:** Random portfolio instances generated with Qiskit Finance, chiefly `N=12`, budget/cardinality `B=4`.
- **Key finding:** The authors report better shallow-depth approximation ratios on their simulations.
- **Limitation/future:** Three-body terms increase circuit depth and runtime and can leak outside the feasible subspace; only synthetic, small, preprint results exist.
- **In simple language:** It adds a shortcut term to help a shallow circuit move faster, but the shortcut itself is costly.
- **Use in our project:** Treat counterdiabatic QAOA as a late optional ablation, not the core promise.

## 18. A Two-Step QAOA for Portfolio Optimization and Risk Assessment

- **Year/status/source:** 2026, peer-reviewed, *Quantum Reports* 8(2), 45. DOI: `10.3390/quantum8020045`.
- **Access:** [open-access article](https://www.mdpi.com/2624-960X/8/2/45).
- **Problem/gap:** A single objective value says little about how confidently a quantum procedure prefers one candidate portfolio over another.
- **Objective:** First optimize portfolio selection, then use a second quantum step to construct an energy-based risk/preference indicator.
- **Method/workflow:** QUBO selection -> warm-start/counterdiabatic variants -> second QAOA-style assessment -> compare simulated solutions.
- **Data:** Small simulated portfolio cases constructed from return/covariance inputs.
- **Key finding:** The two-step method supplies both a selected portfolio and an additional relative indicator.
- **Limitation/future:** The indicator is not a standard financial risk measure such as volatility, VaR or drawdown and lacks large out-of-sample validation.
- **In simple language:** It chooses a portfolio and then assigns an extra quantum score to that choice.
- **Use in our project:** We should prefer recognized finance and optimization metrics, while optionally studying sample confidence.

## 19. Quantum Stochastic Walks for Portfolio Optimization: Theory and Implementation on Financial Networks

- **Year/status/source:** 2026, peer-reviewed, *npj Unconventional Computing*. DOI: `10.1038/s44335-025-00050-4`.
- **Access:** [Nature](https://doi.org/10.1038/s44335-025-00050-4).
- **Problem/gap:** Mean-variance optimization can be unstable and often ignores the network structure of asset correlations.
- **Objective:** Use quantum stochastic walks on a financial network to derive portfolio weights.
- **Method/workflow:** Convert correlations to a graph -> evolve an open quantum walk -> use stationary probabilities as weights -> backtest against benchmarks.
- **Data:** Top 100 S&P 500 stocks from 2018-2024 plus 30 historical trials spanning 1990-2024.
- **Key finding:** Network-based quantum-inspired weights were competitive with simple diversification baselines in the authors' tests.
- **Limitation/future:** It is not QAOA and does not solve our discrete constrained selection model; sensitivity to graph construction remains.
- **In simple language:** Stocks become nodes in a network, and a simulated quantum walk decides their importance.
- **Use in our project:** Shows that a credible paper needs repeated historical tests, not one hand-picked period.

## 20. Solving the Portfolio Optimization Problem on a Photonic Quantum Computer

- **Year/status/source:** 2026, peer-reviewed, *Entropy* 28(7), 717. DOI: `10.3390/e28070717`.
- **Access:** [open-access article](https://doi.org/10.3390/e28070717).
- **Problem/gap:** Photonic boson-sampling methods have rarely been benchmarked systematically on portfolio QUBOs.
- **Objective:** Compare binary boson sampling with simulated annealing in simulation and on a small photonic device.
- **Method/workflow:** Generate 500 portfolio instances -> run boson-sampling and annealing solvers -> compare global-optimum frequency and objective gap -> demonstrate small hardware cases.
- **Data:** 500 constructed portfolio-optimization instances across increasing problem sizes.
- **Key finding:** The authors report a 74% global-optimum rate on tested instances and an average gap near 2% at size 25 for their photonic approach.
- **Limitation/future:** Mostly simulation, not QAOA, and instance-generation assumptions control difficulty; hardware scale is small.
- **In simple language:** This is a different type of quantum solver and is useful mainly as a benchmarking comparison.
- **Use in our project:** Reinforces reporting distributions across many instances instead of one best run.

## 21. Benchmarking Quantum Solvers in Noisy Digital Simulations for Financial Portfolio Optimization

- **Year/status/source:** 2026, peer-reviewed, *Entropy* 28(8), 916. DOI: `10.3390/e28080916`; first preprint in 2025.
- **Access:** [open-access article](https://doi.org/10.3390/e28080916); [free manuscript](https://arxiv.org/abs/2508.21123).
- **Problem/gap:** Noiseless simulations can make variational quantum methods appear more reliable than they would under imperfect operations.
- **Objective:** Compare QAOA and quantum imaginary-time evolution under controlled digital noise.
- **Method/workflow:** Form portfolio QUBOs -> simulate both solvers noiselessly -> inject noise models -> compare objective accuracy, robustness and classical overhead.
- **Data:** Small instances derived from synthetic/historical-style financial price inputs.
- **Key finding:** QAOA performed strongly without noise but degraded rapidly under noise, whereas QITE was more robust at the cost of greater classical computation.
- **Limitation/future:** Noise models are approximations rather than hardware results; instances remain small and do not include our full constraint set.
- **In simple language:** The algorithm can look excellent in a perfect simulator and become fragile once realistic errors are added.
- **Use in our project:** Run correctness experiments first, then add controlled Aer noise as a sensitivity study—never present it as real hardware evidence.

## 22. Large-Scale Portfolio Optimization Using Pauli Correlation Encoding

- **Year/status/source:** 2026, peer-reviewed, *Scientific Reports*. DOI: `10.1038/s41598-026-54244-2`.
- **Access:** [Nature](https://doi.org/10.1038/s41598-026-54244-2); [free manuscript](https://arxiv.org/abs/2511.21305).
- **Problem/gap:** One-qubit-per-variable encodings make large portfolio universes inaccessible to classical simulation and near-term devices.
- **Objective:** Encode many classical portfolio variables into expectation values and correlations of fewer qubits.
- **Method/workflow:** Partition the interaction graph -> optimize Pauli-correlation encodings for each part -> decode and repair candidates classically -> combine partitions.
- **Data:** Five years of Kaggle S&P 500 data, with experiments up to 250 portfolio variables.
- **Key finding:** The method demonstrated much larger encoded portfolio models than direct one-variable-per-qubit approaches.
- **Limitation/future:** Decoding, partitioning and post-processing can hide solution-quality losses; it is not standard QAOA and direct comparisons are difficult.
- **In simple language:** It compresses many stock decisions into correlations measured from a smaller simulated quantum system.
- **Use in our project:** Keep it as the year-end scaling pivot if direct simulation stalls beyond roughly 20-25 binary variables.

## 23. Multiclass Portfolio Optimization via VQE with Dicke State Ansatz

- **Year/status/source:** 2026, peer-reviewed, *Scientific Reports*. DOI: `10.1038/s41598-026-36333-4`.
- **Access:** [open-access article](https://www.nature.com/articles/s41598-026-36333-4).
- **Problem/gap:** Portfolios may require exact quotas for several asset classes, not merely one total-cardinality rule.
- **Objective:** Enforce class-wise cardinalities through a structured Dicke-state ansatz and optimize it with VQE.
- **Method/workflow:** Divide assets by class -> prepare fixed-weight Dicke states per class -> variational optimization with CMA-ES -> compare small simulations.
- **Data:** Simulated multiclass portfolio instances with specified allocation counts.
- **Key finding:** The ansatz restricts search to portfolios that satisfy every class quota by construction.
- **Limitation/future:** VQE rather than QAOA; preparing and mixing multiple Dicke subspaces becomes costly, and financial backtesting is limited.
- **In simple language:** Each sector gets its own exact number of seats, and the quantum state never breaks that rule.
- **Use in our project:** This directly motivates sector-wise XY mixers when sector requirements are exact counts.

## 24. Towards Large-Scale Quantum Optimization Solvers with Few Qubits

- **Year/status/source:** 2025, peer-reviewed, *Nature Communications* 16. DOI: `10.1038/s41467-024-55346-z`.
- **Access:** [open-access article](https://www.nature.com/articles/s41467-024-55346-z).
- **Problem/gap:** Direct binary encodings cannot represent industrial-scale optimization with the qubit counts available today.
- **Objective:** Introduce Pauli correlation encoding (PCE), which represents many decision variables using measurements from few qubits.
- **Method/workflow:** Encode variables into Pauli expectations/correlations -> variationally optimize -> decode classical bits -> evaluate Max-Cut benchmarks.
- **Data:** Large Max-Cut graphs, including demonstrations with thousands of vertices; not financial datasets.
- **Key finding:** The work established the resource-efficient encoding later adapted to portfolio optimization.
- **Limitation/future:** Compression transfers difficulty to measurement, decoding and classical optimization and does not imply a speed advantage.
- **In simple language:** It is the foundational “many variables with few qubits” paper, but the saved qubits are not free.
- **Use in our project:** One of the 25 recent papers because it explains the architecture behind Paper 22; cite it only in the scalability section.

## 25. The Lie Algebra of XY-Mixer Topologies and Warm Starting QAOA for Constrained Optimization

- **Year/status/source:** 2026, peer-reviewed, *npj Quantum Information*. DOI: `10.1038/s41534-026-01192-4`.
- **Access:** [open-access article](https://doi.org/10.1038/s41534-026-01192-4); [free manuscript](https://arxiv.org/abs/2505.18396).
- **Problem/gap:** Constraint-preserving XY mixers can still be difficult to train; mixer connectivity changes expressibility and parameter behavior.
- **Objective:** Characterize the Lie algebra of XY mixer topologies and pretrain a restricted circuit before expanding to full QAOA.
- **Method/workflow:** Analyse ring/complete mixer algebras -> optimize a tractable restricted-polynomial circuit -> transfer parameters into the full constrained ansatz -> benchmark several problems.
- **Data:** Portfolio selection, sparsest `k`-subgraph and graph-partition simulation instances.
- **Key finding:** Structure-aware pretraining improved optimization reliability on tested constrained problems.
- **Limitation/future:** Algebraic analysis is advanced, benefits depend on topology/problem, and experiments remain simulation-scale.
- **In simple language:** The pattern of allowed swaps changes what the algorithm can learn, so even two “XY-QAOA” implementations may behave differently.
- **Use in our project:** Compare at least ring and complete/sector-wise XY topology, but avoid promising full Lie-algebra theory as a deliverable.

# Five influential foundations from 2021-2024

These five are deliberately outside the January-2025 cutoff. They are retained because later papers repeatedly build on their initialization, mixer and benchmarking ideas. None is older than 2021.

## 26. Warm-Starting Quantum Optimization

- **Year/status/source:** 2021, peer-reviewed, *Quantum* 5, 479. DOI: `10.22331/q-2021-06-17-479`.
- **Access:** [open-access article](https://quantum-journal.org/papers/q-2021-06-17-479/).
- **Problem/gap:** QAOA normally begins from an uninformed uniform state, wasting evaluations far from promising classical solutions.
- **Objective:** Map a classical continuous relaxation into both the QAOA initial state and a compatible mixer.
- **Method/workflow:** Solve a relaxation -> convert relaxed values into qubit rotation angles -> use a warm-start mixer -> variationally optimize.
- **Data:** Standard combinatorial benchmark problems, including Max-Cut; not a financial dataset.
- **Key finding:** Warm-starting improved low-depth solution quality on several tested cases and became a foundation for later portfolio work.
- **Limitation/future:** A poor or overconfident classical relaxation can bias the search, and benefits are instance-dependent.
- **In simple language:** Give QAOA a good classical hint instead of making it start blind.
- **Use in our project:** Compare random/uniform initialization against a relaxation-based warm start.

## 27. Quantum Walk-Based Portfolio Optimisation

- **Year/status/source:** 2021, peer-reviewed, *Quantum* 5, 513. DOI: `10.22331/q-2021-07-28-513`.
- **Access:** [open-access article](https://quantum-journal.org/papers/q-2021-07-28-513/).
- **Problem/gap:** Standard QAOA mixers do not naturally exploit fixed-budget or fixed-cardinality portfolio structure.
- **Objective:** Use continuous-time quantum walks over the feasible portfolio graph as the mixing mechanism.
- **Method/workflow:** Construct a graph of feasible holdings -> initialize a feasible state -> alternate cost evolution and graph-walk mixing -> compare with conventional QAOA.
- **Data:** Historical Yahoo Finance data for Australian-listed stocks in small portfolio examples.
- **Key finding:** Quantum-walk mixing outperformed the authors' standard-QAOA baseline on the tested small simulations.
- **Limitation/future:** Small instances, simulator evidence and graph/mixer construction complexity; performance does not establish advantage over modern classical solvers.
- **In simple language:** Instead of jumping anywhere, the algorithm walks only between legal portfolios.
- **Use in our project:** The conceptual basis for our XY/constraint-preserving mixer.

## 28. Benchmarking the Performance of Portfolio Optimization with QAOA

- **Year/status/source:** 2023, peer-reviewed, *Quantum Information Processing* 22. DOI: `10.1007/s11128-022-03766-5`.
- **Access:** [Springer](https://doi.org/10.1007/s11128-022-03766-5); [free manuscript](https://arxiv.org/abs/2207.10555).
- **Problem/gap:** Early portfolio-QAOA claims rarely isolated the effects of mixer, optimizer, depth and noise.
- **Objective:** Provide a controlled portfolio-specific comparison of these QAOA design choices.
- **Method/workflow:** Form DAX portfolio QUBOs -> compare mixers and classical optimizers -> vary depth and shot/noise settings -> evaluate approximation quality.
- **Data:** DAX 30 historical returns from 2016-2020, evaluated on small subsets feasible for simulation.
- **Key finding:** Performance depended strongly on mixer/optimizer choice and deteriorated under noise; more depth was not automatically better.
- **Limitation/future:** Small subsets and earlier Qiskit stack; realistic sector, turnover and transaction-cost constraints were not jointly studied.
- **In simple language:** QAOA is not one fixed algorithm—its settings can change the answer dramatically.
- **Use in our project:** This is the methodological ancestor of our configuration benchmark.

## 29. Alignment Between Initial State and Mixer Improves QAOA Performance for Constrained Optimization

- **Year/status/source:** 2023, peer-reviewed, *npj Quantum Information* 9. DOI: `10.1038/s41534-023-00787-5`.
- **Access:** [open-access article](https://doi.org/10.1038/s41534-023-00787-5); [free manuscript](https://arxiv.org/abs/2305.03857).
- **Problem/gap:** Feasible initialization and constraint-preserving mixers are often chosen independently even though their geometry interacts.
- **Objective:** Test whether matching the initial state's symmetry and support to the mixer improves constrained QAOA.
- **Method/workflow:** Compare aligned and misaligned initial-state/mixer pairs -> simulate constrained portfolio cases -> run selected experiments on hardware.
- **Data:** Small portfolio-style problems, prominently `N=6`, `K=3`, plus experiments reaching 32 qubits.
- **Key finding:** Alignment produced small but consistent improvements in ideal tests, though noise reduced the benefit.
- **Limitation/future:** Effect sizes were modest, problems small and hardware noise substantial.
- **In simple language:** A legal starting point is not enough; it should also fit the way the mixer is allowed to move.
- **Use in our project:** Justifies treating initialization and mixer as a paired configuration rather than separate toggles.

## 30. Enhancing Knapsack-Based Financial Portfolio Optimization Using QAOA

- **Year/status/source:** 2024, peer-reviewed, *IEEE Access* 12. DOI: `10.1109/ACCESS.2024.3506981`.
- **Access:** [IEEE](https://doi.org/10.1109/ACCESS.2024.3506981); [free manuscript](https://arxiv.org/abs/2402.07123).
- **Problem/gap:** Portfolio selection with a capital limit resembles knapsack, but a generic mixer spends samples outside the budget-feasible region.
- **Objective:** Apply QAOA with quantum-walk-style constrained mixing to a knapsack portfolio model.
- **Method/workflow:** Estimate asset values/costs from financial data -> encode knapsack -> feasible quantum-walk mixer -> run depth variations -> compare with classical solutions.
- **Data:** Small Yahoo Finance stock sets.
- **Key finding:** At depths around `p>=3`, the tested QAOA configurations approached the classical reference on small instances.
- **Limitation/future:** Very small asset sets, limited investment constraints, and no evidence of scaling or advantage.
- **In simple language:** QAOA searches only combinations that fit within the available capital.
- **Use in our project:** Confirms that feasible-space mixing matters, while reminding us to compare fairly at each depth.

# Cross-paper critical analysis

## What has already been done

The corpus can be grouped into six research directions:

1. **Better QAOA objectives:** CVaR and higher moments try to improve robustness or financial realism (Papers 1 and 7).
2. **Better initial states and mixers:** warm starts, Dicke states, XY/quantum-walk mixers and counterdiabatic terms try to improve feasibility or trainability (Papers 13, 16, 17, 23, 25-30).
3. **Constraint conversion:** penalties, slack variables and oracle-style checks convert constrained problems into a quantum-compatible form (Papers 11 and 13).
4. **Reduced resource use:** decomposition, interval restriction and compressed encodings reduce qubit or search-space demands (Papers 4, 14, 15, 22 and 24).
5. **End-to-end financial evaluation:** a smaller group adds rebalancing, expert validation, turnover or out-of-sample metrics (Papers 8, 12, 16 and 19).
6. **Honest benchmarking:** stronger recent work shows that classical exact and tailored heuristic solvers remain formidable and that noise can erase simulator gains (Papers 3, 9, 10, 20, 21 and 28).

## Limitations repeated across the literature

- Most QAOA experiments use fewer than about 30 assets; many use 4-12.
- Many studies use synthetic inputs, one market period or one hand-picked universe.
- A low QUBO energy is often reported without out-of-sample Sharpe ratio, drawdown, turnover or transaction cost.
- Sector rules, exact cardinality, budget/position limits and turnover are rarely tightened together under the same experimental protocol.
- Papers usually propose one fixed configuration. Penalty, mixer, initialization and depth are seldom changed automatically from measured feasibility and convergence behaviour.
- Classical comparisons are sometimes weak. Paper 10 shows that a modern exact solver or tailored heuristic can dominate the tested quantum methods.
- Noiseless simulation is sometimes discussed as if it represented hardware. Paper 21 shows why these claims must remain separate.

## The precise gap we can safely claim

> **Gap in the reviewed 30-paper corpus:** Existing work typically improves penalty handling, mixer design, initialization, encoding or scalability separately. There is limited controlled evidence showing how identical QAOA configurations behave as realistic portfolio constraints become progressively tighter, and whether a lightweight performance-guided controller can select or tune the configuration using feasibility and convergence diagnostics while preserving fair classical comparisons.

This wording is deliberately bounded to the reviewed corpus. Do **not** say “nobody has ever done this” unless a formal systematic search later proves it.

# Recommended project direction

## Keep the official title

**Quantum-Based Portfolio Optimization Using QAOA under Realistic Investment Constraints**

## Strong internal problem statement

> To design and simulate an adaptive, constraint-aware QAOA framework for discrete portfolio selection under cardinality, sector-diversification, budget and turnover constraints, and to determine how constraint tightness affects feasibility, solution quality and computational cost relative to exact and heuristic classical solvers.

## Proposed contribution

**Adaptive Constraint-Aware QAOA (simulation study):** a reproducible system that (1) formulates the same financial instance under progressively tighter constraints, (2) runs short pilot configurations, (3) measures feasible-sample probability, solution quality and convergence, and (4) selects or tunes the next QAOA configuration.

The controller is a **performance-guided QAOA configuration controller**. Do not call it “changing the routing logic.” In quantum computing, routing normally means mapping logical qubits and gates to the connections of a physical device. Because this project uses simulators, hardware routing would be both confusing and outside the actual work.

## What the controller may change

| Diagnostic/result | Sensible response |
|---|---|
| Exact total cardinality, no sector inequality | Dicke feasible initialization + XY mixer |
| Exact per-sector counts | Sector-wise Dicke states + sector-wise XY mixers |
| Flexible sector min/max bounds | Penalty or binary slack encoding; record extra variables |
| Feasible-sample probability is low | Increase/normalize constraint penalty or switch to preserving mixer where supported |
| Feasibility is high but objective stagnates | Change initialization/optimizer, then increase depth cautiously |
| Good continuous relaxation is available | Warm-start initial state |
| Expectation objective is unstable/outlier-sensitive | Compare CVaR aggregation |
| Simulation becomes too large | Decompose asset universe or use compressed encoding as a documented pivot |

This is not a new “QAOA algorithm” unless the controller itself is specified, implemented and experimentally shown to outperform fixed configuration rules. Until then, call it a **framework and benchmark**.

# Mathematical formulation for the first implementation

## Stage 1: QAOA selects assets

For `n` assets, let `x_i = 1` when asset `i` is selected and `0` otherwise. With equal provisional weights among `K` selected assets, a practical minimization objective is:

```text
minimize_x
    q x^T Sigma x                         portfolio risk
  - (1-q) mu^T x                         expected return
  + A_K (sum_i x_i - K)^2                cardinality penalty, if not mixer-enforced
  + sum_s A_s C_s(x)^2                   sector constraints after equality/slack conversion
  + lambda_T sum_i (x_i - x_i_previous)^2 turnover penalty
```

Here `mu` is expected return, `Sigma` is the covariance matrix, `q` controls risk preference, and the `A` terms are penalties. Because the previous holdings are fixed data, the turnover expression is QUBO-compatible. All coefficients must be normalized so one term does not numerically overwhelm every other term.

Recommended realistic constraints, introduced in stages:

1. **Exact cardinality:** `sum_i x_i = K`.
2. **Sector diversification:** lower/upper asset counts or later lower/upper sector weights.
3. **Long-only and full investment:** handled in classical weight optimization.
4. **Position bounds:** `w_min x_i <= w_i <= w_max x_i`.
5. **Turnover and transaction cost:** penalize changes from the previous rebalance.
6. **Optional only after the core works:** liquidity or ESG screens.

## Stage 2: classical solver chooses weights

After QAOA selects the set `S`, solve a convex or mixed-integer classical problem for continuous weights:

```text
minimize_w  q w^T Sigma w - (1-q) mu^T w
subject to  sum_i w_i = 1
            w_i = 0 for i not in S
            w_min <= w_i <= w_max for i in S
            sector and turnover limits
```

This two-stage design is easier to simulate, easier to explain, and more financially realistic than encoding many weight bits per asset in the first prototype.

# Dataset and platform decision

## Primary dataset

- **Universe:** NIFTY 50, with survivorship limitations stated clearly.
- **Prices:** adjusted daily close, initially January 2019-December 2025, saved as a timestamped local snapshot so experiments are reproducible.
- **Metadata:** sector labels from NSE or another documented source.
- **Protocol:** rolling 252- or 504-trading-day estimation window; monthly rebalancing; keep 2024-2025 primarily for out-of-sample evaluation.
- **Scales:** begin with deterministic subsets of 8, 10, 12, 16 and 20 assets; add random/sector-balanced subsets and seeds to avoid cherry-picking.
- **Secondary validation:** S&P 100 or a second NIFTY period only after the core study is stable.

Yahoo Finance/yfinance is convenient, but downloaded values can change after corrections. Freeze the CSV files, download date, ticker list, missing-value rules and corporate-action handling.

## Simulation platform

- Python, Qiskit Optimization/Algorithms and **Qiskit Aer** only.
- Statevector simulation for small correctness tests.
- Shot-based simulation at fixed shot counts such as 1,024 and 4,096.
- Aer noise models as an optional sensitivity experiment; clearly label them simulated noise.
- Matrix-product-state simulation only after checking that the circuit entanglement and method settings make it suitable.
- No IBM hardware execution is required and no result should be called a hardware result.

# Fair experimental design

## Classical baselines

- Brute-force enumeration for very small instances so the true optimum is known.
- Exact MIQP/MIP solver for all tractable cases: SCIP, Gurobi if institutionally available, or another documented solver.
- Simulated annealing and/or tabu search.
- Continuous Markowitz optimization using CVXPY.
- Equal-weight portfolio as a financial baseline.

## QAOA ablations

- Depth `p = 1, 2, 3, 4, 5` where simulation permits.
- X mixer versus XY/constraint-preserving mixer.
- Uniform/random versus warm-start initialization.
- COBYLA versus SPSA or another documented optimizer.
- Expectation value versus CVaR objective aggregation.
- Fixed versus adaptive penalty/configuration policy.
- At least 20-30 independent seeds per small setting; report median and dispersion, not only the best run.

## Required metrics

**Optimization metrics:** feasible-sample probability, best feasible objective, probability of the exact optimum, approximation/optimality gap, number of objective evaluations, wall-clock time, peak memory and simulated qubit count.

**Financial metrics:** out-of-sample annualized return, volatility, Sharpe ratio, maximum drawdown, sector exposure, turnover and return after a stated transaction-cost model.

Never compare QAOA wall-clock time on a classical simulator with native classical-solver time as evidence of quantum speedup. Simulator time is a project resource and reproducibility metric, not quantum runtime.

# One-year execution roadmap

| Months | Deliverable |
|---|---|
| 1-2 | Quantum/QAOA basics, reproduce one small Qiskit portfolio example, freeze literature matrix |
| 3 | Download/freeze NIFTY data; implement continuous Markowitz, equal-weight and exact small baselines |
| 4 | Derive/test basic QUBO against brute force for 6-12 assets |
| 5 | Baseline QAOA on Aer; depth, optimizer and seed experiments |
| 6 | Exact-cardinality Dicke/XY implementation and validation |
| 7 | Sector and turnover constraint regimes; penalty/slack experiments |
| 8 | Implement performance-guided configuration controller |
| 9 | Rolling out-of-sample backtest and transaction costs |
| 10 | Shot sensitivity and optional simulated-noise study |
| 11 | Ablations, statistics, robustness on a second universe/period |
| 12 | Final report, reproducible repository, presentation and demo |

# Safe pivot ladder without changing the title

1. **Plan A — full contribution:** adaptive controller chooses mixer/initialization/penalty/depth policy by constraint regime.
2. **Plan B — strong benchmark:** controlled study of constraint tightness with fixed candidate configurations; identify empirical decision rules even if automatic selection is unreliable.
3. **Plan C — focused contribution:** exact-cardinality and sector-aware mixer plus systematic penalty tuning and end-to-end backtest.
4. **Plan D — scaling direction:** add asset-universe decomposition or resource-efficient encoding if direct QAOA simulation becomes the central limitation.

All four still satisfy the existing title. The title describes the domain and method, not an unchangeable implementation promise.

# Short answers for the next review

## Why quantum computing, and why QAOA instead of only traditional optimization?

Portfolio selection with discrete constraints is combinatorial. QAOA gives a structured hybrid framework in which constraints can be represented by the cost Hamiltonian or preserved by the mixer. We are **not claiming it already beats classical solvers**. We are studying when its configurations remain feasible and competitive on simulation, using exact and heuristic classical methods as controls.

## What are your realistic constraints?

Exact number of selected assets, sector-diversification limits, long-only/full-investment weights, minimum/maximum position size, and turnover/transaction costs. Liquidity/ESG filters are optional later work.

## How will you formulate it for QAOA?

Binary variables select assets. Return and covariance form a QUBO cost. Exact cardinality is enforced either by a penalty or, preferably, a Dicke initial state with XY mixer. Sector inequalities use penalties or slack variables. A classical second stage assigns continuous weights.

## Which dataset and quantum platform?

Frozen NIFTY 50 adjusted-price data, with sector labels and rolling out-of-sample tests; Qiskit Aer statevector and shot-based simulations. No quantum hardware is claimed or required.

## How will you tune accuracy and performance while maintaining optimization quality?

Run a shallow pilot, monitor feasible-sample probability, objective gap and convergence, then adapt penalty strength, mixer/initialization, optimizer and only then depth. Validate every small instance against brute force or an exact solver and report repeated-seed distributions.

## What exactly is new?

The new work is not merely running QAOA on another stock list. It is the controlled constraint-regime benchmark and, if validated, a performance-guided controller that changes QAOA configuration from measured feasibility and convergence while retaining identical financial instances and strong classical baselines.

# Final claim boundary

Use this sentence in the presentation:

> **We aim to determine which constraint-aware QAOA configuration works best under different levels of realistic portfolio complexity in simulation; we do not assume or claim quantum advantage.**

Avoid these unsupported phrases: “faster than classical,” “works for large portfolios,” “runs on real quantum hardware,” “guarantees higher returns,” or “completely changes the original QAOA algorithm.”
