# Q-Compass, without the jargon

## The basket idea

Imagine you can put four fruits in a basket. You want useful variety, not four
copies of the same fruit. In our project, fruits are **stocks**, the basket is a
**portfolio**, and rules limit how many similar businesses you can select.

We do not know future prices. We use previous prices to estimate what might
happen. Estimates can be wrong. A result that looks attractive in the training
window can lose money afterward.

## Follow one real run

1. **Check the ingredients.** Data audit shows official stock identifiers and
   downloaded Yahoo histories. Missing prices are not guessed. Open the failure
   table to see why some stocks cannot be used.
2. **Build a small question.** Eight candidate stocks, choose exactly four,
   no more than one from each of four industries. Stocks are picked into the
   candidate pool by a deterministic identity/industry rule—not because they
   were the historical winners.
3. **Ask ordinary algorithms.** Exhaustive search tries every allowed four-stock
   combination. It is a dependable answer key for this small example.
4. **Ask the simulated quantum algorithm.** QAOA creates a circuit, samples
   possible 0/1 choices, and an ordinary optimizer adjusts circuit angles.
   Sampling can produce invalid choices. We count those too.
5. **Try and adapt.** The controller briefly tries circuit depths 1 and 2. It
   compares valid answers and allocates the remaining trial budget. It never
   sees the exact answer key or future returns.
6. **Divide the money.** The same ordinary weighting solver assigns percentages
   to each method's selected stocks. If the percentages cannot satisfy the rules,
   the result is a failure—not quietly replaced by a different answer.
7. **Save the evidence.** Every number comes from a saved run. Replay shows that
   run; reproduce actually runs it again and checks the result.

## Words you will see

| Word | Plain meaning |
|---|---|
| Asset / stock | Something the portfolio can hold |
| Return | Percentage change in value |
| Risk / volatility | How strongly returns fluctuate |
| Covariance | Whether stocks tend to move together, including their fluctuation sizes |
| Correlation | A standardized measure of how stocks move together |
| Weight | Fraction of the money assigned to one stock |
| Long-only | No negative stock positions / short selling |
| Cardinality K | Exactly how many stocks must be selected |
| Sector / industry limit | A rule limiting concentration in similar businesses |
| Binary decision | 1 means select; 0 means leave out |
| QUBO | Quadratic Unconstrained Binary Optimization: a score written using 0/1 choices and pairwise interactions |
| Penalty | Extra numerical cost for breaking a selection rule; it is not a market loss |
| Ising operator | The circuit-compatible representation of the binary score |
| Qubit | A quantum bit, simulated here in laptop memory |
| QAOA | Quantum Approximate Optimization Algorithm: alternating cost and mixing circuit steps, with angles adjusted classically |
| Depth p | Number of repeated QAOA layers; deeper need not mean better |
| Shot | One measured sample from a circuit |
| Mixer | Circuit operations that move probability among possible answers |
| X mixer | Can change the number of selected stocks |
| XY mixer | Preserves the asset-register selection count in ideal simulation, but not automatically every other rule |
| COBYLA / SPSA | Ordinary algorithms that adjust quantum circuit angles |
| CVaR | Conditional Value at Risk: here, optimize a chosen best-energy portion of samples; not a promised portfolio tail-risk guarantee |
| Feasible | Obeys the stated rules |
| Objective gap | Difference between a method's selection score and a certified best score |
| Seed | Starting number used to reproduce randomized trials |
| Fingerprint | A hash that changes when stored data or metadata change |
| Backtest | Replay decisions on past data with realistic timing; useful only if information rules are respected |
| Leakage | Accidentally using information that would not yet have existed |
| Survivorship bias | Studying today's surviving/index stocks as if that list had always been available |
| Turnover | Half the total absolute change in security weights, including forced sales |
| Basis point | One hundredth of one percent; 10 bps = 0.1% |
| Sharpe ratio | Average excess return relative to fluctuations; our initial research risk-free assumption is zero |

## What to say to your guide

“We use real NIFTY stock histories and simulate QAOA in Qiskit Aer. Our first
experiment compares stock selection under the same rules and measured sampling
budget. The adaptive controller spends short pilots to choose a circuit setting.
We separately test whether the selection can be assigned valid investment
weights. We record invalid answers and failures. We are investigating when the
method is useful, not assuming quantum advantage.”

If asked what is new: the research hypothesis is whether **context plus pilot
feedback** can allocate a limited simulation budget more reliably across market
conditions and constraint difficulty. The individual ingredients already exist.
The present app provides the reproducible experiment machinery; comparative
evidence and a defensible novelty claim still require the research campaign.

If asked why quantum rather than ordinary methods: ordinary methods are strong
and may win. They remain our baselines and answer keys. Quantum is the algorithm
being studied—not a justification for declaring ordinary optimization obsolete.

## What a successful small demo does NOT establish

Finding the exact answer with eight stocks does not show scalability, faster
hardware execution, higher future profit or a new universal quantum algorithm.
Simulator runtime is ordinary-computer runtime. Identical results and negative
results belong in the report as much as improvements do.
