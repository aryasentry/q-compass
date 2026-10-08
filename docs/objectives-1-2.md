# Objectives 1 and 2: reproducible baseline milestone

This milestone answers two bounded questions:

1. Can Q-Compass turn a checksum-verified NIFTY 50 snapshot into a reproducible,
   past-only portfolio-selection instance without inventing or filling prices?
2. Can exact, greedy and standard alternating QAOA baselines be run twice with
   fixed settings and pass independent integrity, feasibility and budget checks?

It is a current-membership optimization study, not a historical NIFTY backtest.
It does not test quantum advantage, realized returns, or the adaptive research
controller. Objectives 1 and 2 should be called complete only after the full
command below passes and its saved evidence and dashboard runs are inspected.

In plain English: pick 4 stocks from 8. Exact search checks every allowed
combination, greedy search takes sensible shortcuts, and QAOA samples a simulated
quantum circuit. After any method picks the stocks, the same classical allocation
step decides how much money to assign to each one.

## Verified completion: 5 September 2026

The configured eight-stock/four-holding milestone passed **128 acceptance checks**
on two distinct runs of the final reviewed code. Both runs reproduced the selected
stocks, quantum counts and evaluation budgets exactly; objective and weight
comparisons passed their documented tolerances. All five reported methods returned
valid selections and allocations. The four required baselines passed the independent
checks against the verified dataset and requested problem.

- [Open the measured comparison](http://127.0.0.1:3000/experiments/e2d86619fd3f4a9c9c98b247ebede87f)
- [Read the completion evidence](../artifacts/milestones/objectives-1-2-20260905T143236Z-f07bb92007/report.md)
- [Inspect the machine-readable checks](../artifacts/milestones/objectives-1-2-20260905T143236Z-f07bb92007/evidence.json)

Run A: `e2d86619fd3f4a9c9c98b247ebede87f`.
Run B: `39d6ba7c0a75418ebd16c14fa40e1991`.
Both are saved optimization comparisons, not fabricated charts or backtests.
Each quantum baseline used 24,576 shots, including final sampling. QAOA reached
the exact selection score on this small instance, while classical methods ran
faster. Only 7.42% and 5.27% of final samples were feasible at depths one and two,
respectively; selecting a valid final portfolio does not mean every sampled answer
obeyed the rules.

Verification: 91 Python tests and 23 frontend tests passed, with two pre-existing
upstream Python deprecation warnings. Python/TypeScript lint and TypeScript checks
passed, as did the production build. Browser checks covered both saved runs,
allocation switching, controller disclosure, CSV export, reload and desktop/mobile
layouts without browser errors. The Streamlit source files retained their original
fingerprints. No presentation or source-market-data files were changed.

Completion applies to these two objectives at the documented prototype scope.
The later adaptive-controller and historical-performance research objectives remain
separate work.

## What the command does

The supplied settings pin dataset
`nifty50-20260905T080605-28fd98-sealed-0d14f0-reprocessed-641edf`, decision date
2026-09-04, eight candidates, four holdings, and a maximum of one selected stock
per represented sector. They run depth-1 and depth-2 standard X-mixer QAOA with
the mean objective (`alpha = 1`), COBYLA, 48 sampling batches of 512 shots,
seed 42 and a 180-second per-method ceiling. Repair and adaptation are disabled.

Run from the project folder:

```sh
.venv/bin/qcompass milestone --settings configs/objectives-1-2.json
```

The CLI first acquires the same exclusive worker lock used by ordinary
experiments. Inside that lock, the workflow verifies every manifest-bound file
hash, structurally validates the retained market table, reconstructs the
deterministic eligible eight-stock instance, and exports the exact aligned
253-price/252-return window. Missing or corrupt inputs stop before a solver starts.
It then runs the comparison twice, sequentially. Both normal run records remain
under `artifacts/runs/` and therefore remain visible to the existing dashboard.

Every invocation creates a new `artifacts/milestones/objectives-1-2-*` directory;
it never overwrites an older package. The package contains:

- `evidence.json`: machine-readable provenance, independent gates and pass/fail;
- `comparison.csv`: side-by-side measured results for the two runs;
- `report.md`: readable links, methods, checks, exclusions and limitations;
- selected adjusted prices, daily returns, annualized expected returns and the
  covariance matrix, all labelled as derived from verified authentic observations;
- `constraints.json`: the selection and later allocation responsibilities.

A failed acceptance gate still writes failed evidence and the command returns a
nonzero status.

## Mathematics and responsibilities

For a binary selection vector \(x\), exactly \(K\) selected stocks and annualized
expected returns \(\mu\) and covariance \(\Sigma\), the selection score is

\[
f(x)=\lambda\frac{x^T\Sigma x}{K^2}-\frac{\mu^T x}{K}.
\]

Lower is better. This score treats selected stocks as equal-weighted and is only
a **selection proxy**. The selection layer is responsible for binary values,
\(\sum_i x_i=K\), and sector-count limits. Exhaustive enumeration provides a
certified exact minimum; greedy with local swaps is a heuristic; depth-1 and
depth-2 QAOA are sampled simulator baselines. No quantum method is required to
equal or improve on the exact answer, but none may report a score below the
certified exact minimum beyond the documented numerical tolerance.

After each selection, a separate classical convex allocation chooses weights
\(w\). That stage is responsible for

\[
\sum_i w_i=1,\qquad w_i=0\text{ when }x_i=0,
\qquad w_{\min}x_i\le w_i\le w_{\max}x_i,
\]

plus each sector's weight cap. The evidence code recomputes cardinality, sector
counts, the original binary objective, full investment, position bounds and
sector weights from the stored bits and weights. It does not trust the stored
feasibility booleans by themselves.

Reproducibility requires identical method, status, bits, sampled counts,
evaluation counts and shots used; identical dataset and source-code fingerprints;
objectives within absolute tolerance `1e-10`; and weights within absolute
tolerance `2e-5`. Wall-clock time is recorded but deliberately not compared.
Sample dictionaries are also checked for valid binary register strings,
nonnegative integer counts and the expected final shot total.

## Inspect in the current dashboard

1. Start the Next.js interface with `bash scripts/start-nextjs.sh` and open
   `http://127.0.0.1:3000`.
2. Open **Experiments** and locate both run IDs printed by the milestone command
   or linked from its `report.md`.
3. Open each run. Under **Results**, confirm the exact, greedy, QAOA depth-1 and
   QAOA depth-2 rows, statuses, scores, selections, weights and shot counts.
4. Change **Inspect allocation from** and confirm its method label and weight bars
   agree. A failed method must show its own failure, not another solver's weights.
5. Open **Controller**. For this baseline-only run it must say that the adaptive
   controller was not run.
6. Open **Run record** to inspect the pinned dataset fingerprint, estimation
   window, eligible count, settings and source fingerprint.
7. In **Data sources**, compare the snapshot's coverage, quarantine and latest
   session cross-check with the milestone report.

The original Streamlit source is preserved and can be started separately with
`.venv/bin/streamlit run app/dashboard.py`; its saved-run view reads the same
normal run records at `http://127.0.0.1:8501` while that process is running.

## Limitations

- The membership list is the current constituent snapshot. It does not prove
  which stocks belonged to NIFTY 50 on older dates, so this is not a bias-free
  historical backtest.
- The retained data has 50 symbol histories, but the milestone does **not** claim
  every history is complete. Eligibility is recomputed at the pinned decision
  date and exclusions are reported.
- Twelve invalid dated source rows are quarantined. They are not repaired,
  interpolated or replaced.
- The available latest closes have an official NSE single-session cross-check;
  that is not certification of every historical observation.
- Adjusted prices use provider adjustments. Corporate actions across every stock
  and date have not been independently certified.
- QAOA runs only on Qiskit Aer under the laptop limits. Results are simulator
  samples, not execution on quantum hardware.
- Exact, heuristic and QAOA comparisons concern the binary equal-weight proxy.
  Final weights come from the later classical allocation stage.
- Passing proves this pinned workflow is reproducible and constraint-valid. It
  does not prove better returns, speed-up, novelty or quantum advantage.

## Guide demo checklist

- [ ] Run the exact pinned command and confirm it prints `PASS`.
- [ ] Open `evidence.json`; confirm `passed: true` and two distinct run IDs.
- [ ] Open `report.md`; review provenance, exclusions and every explicit check.
- [ ] Confirm the exact row is certified and every required method is successful.
- [ ] Confirm selection and allocation feasibility are separate PASS results.
- [ ] Compare depth-1/depth-2 evaluations, shots and sampled counts across runs.
- [ ] Open both saved runs in the dashboard and exercise the allocation selector.
- [ ] Show that the Controller tab states adaptation was not run.
- [ ] Explain equal-weight selection versus later classical weighting.
- [ ] State the current-membership, provider-adjustment and simulator limitations.
