"use client";
import { useState } from "react";
import type { Run } from "@/lib/types";
import { number, percent, methodLabel } from "@/lib/format";
import { Allocation, Comparison } from "./comparison";
import { ResearchNote } from "./ui";

export function RunDetail({
  run,
  initialTab = "results",
}: {
  run: Run;
  initialTab?: string;
}) {
  const [tab, setTab] = useState(initialTab);
  const preferredMethod =
    run.results.find((row) => row.method === "adaptive")?.method ||
    run.results[0]?.method ||
    "";
  const runSignature = `${run.run_id}\u0000${run.results.map((row) => row.method).join("\u0000")}`;
  const [selection, setSelection] = useState(() => ({
    runSignature,
    method: preferredMethod,
  }));
  const method =
    selection.runSignature === runSignature &&
    run.results.some((row) => row.method === selection.method)
      ? selection.method
      : preferredMethod;
  const adaptive = run.results.find((r) => r.method === "adaptive");
  const adaptiveFailure = run.results.find(
    (r) => r.method === "Adaptive pilots",
  );
  const controllerRecord = adaptive || adaptiveFailure;
  const baselineOnly = run.config.include_adaptive === false;
  const selected = run.results.find((r) => r.method === method);
  const tabs = ["results", "controller", "record"];
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Run details">
        {tabs.map((t, i) => (
          <button
            role="tab"
            id={`tab-${t}`}
            aria-controls={`panel-${t}`}
            aria-selected={tab === t}
            tabIndex={tab === t ? 0 : -1}
            key={t}
            onClick={() => setTab(t)}
            onKeyDown={(event) => {
              const next =
                event.key === "ArrowRight"
                  ? (i + 1) % tabs.length
                  : event.key === "ArrowLeft"
                    ? (i + tabs.length - 1) % tabs.length
                    : event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? tabs.length - 1
                        : null;
              if (next === null) return;
              event.preventDefault();
              setTab(tabs[next]);
              event.currentTarget.parentElement
                ?.querySelectorAll<HTMLButtonElement>("button")
                [next]?.focus();
            }}
          >
            {t === "record" ? "Run record" : t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "results" ? (
          <>
            <Comparison run={run} detailed />
            <div className="section-space">
              <label htmlFor="allocation-method">Inspect allocation from</label>
              <select
                id="allocation-method"
                value={method}
                onChange={(e) =>
                  setSelection({ runSignature, method: e.target.value })
                }
                className="compact-select"
              >
                {run.results.map((r) => (
                  <option key={r.method} value={r.method}>
                    {methodLabel(r.method)}
                  </option>
                ))}
              </select>
            </div>
            <Allocation run={run} method={selected} />
            <details className="disclosure">
              <summary>Failures, constraints and classical references</summary>
              <pre>
                {JSON.stringify(
                  {
                    methods: run.results.map((r) => ({
                      method: r.method,
                      status: r.status,
                      error: r.error,
                      selection_violations: r.selection_violations,
                      allocation: r.allocation,
                      repair: r.repair,
                    })),
                    references: run.allocation_references,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </>
        ) : null}
        {tab === "controller" ? (
          <div className="controller-view">
            <h2>Why this configuration?</h2>
            <p>
              {adaptive
                ? adaptive.decision ||
                  adaptive.error ||
                  "No controller decision was recorded."
                : baselineOnly
                  ? "The adaptive controller was not run for this baseline-only comparison."
                  : adaptiveFailure?.error ||
                    "The adaptive controller result is unavailable for this run."}
            </p>
            <div className="stats small">
              <div>
                <strong>{number(controllerRecord?.evaluations)}</strong>
                <span>Objective evaluations</span>
              </div>
              <div>
                <strong>{number(controllerRecord?.shots_used)}</strong>
                <span>Shots, including pilots</span>
              </div>
              <div>
                <strong>{number(controllerRecord?.num_qubits)}</strong>
                <span>Encoded qubits</span>
              </div>
            </div>
            <div className="panel table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Pilot configuration</th>
                    <th>Selection score</th>
                    <th>Valid samples</th>
                    <th>Evaluations</th>
                    <th>Shots</th>
                  </tr>
                </thead>
                <tbody>
                  {adaptive?.pilots?.map((p, i) => (
                    <tr key={i}>
                      <td>{methodLabel(p.method)}</td>
                      <td className="mono">{number(p.objective, 6)}</td>
                      <td>{percent(p.feasible_fraction)}</td>
                      <td>{number(p.evaluations)}</td>
                      <td>{number(p.shots_used)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="notice">
              {baselineOnly
                ? "The adaptive controller and context ranker were not used in this run."
                : run.context_ranker
                  ? "A saved context ranker was supplied. Inspect its training dates and model record below."
                  : adaptive
                    ? "Pilot-only adaptation is active. A market-context model has not been trained for this run."
                    : adaptiveFailure
                      ? "The adaptive controller was requested but did not complete."
                      : "No adaptive controller record is available for this run."}{" "}
              The exact classical optimum is used only for evaluation, not as a
              controller input.
            </p>
            {adaptive?.trace?.length ? (
              <section className="panel trace">
                <h3>Feasible samples across evaluations</h3>
                <div
                  className="trace-bars"
                  role="img"
                  aria-label="Each vertical bar shows the fraction of valid samples for one real circuit evaluation"
                >
                  {adaptive.trace.map((p, i) => (
                    <div
                      key={i}
                      title={`Evaluation ${i + 1} · ${p.config || p.method || "Circuit sample"} · ${percent(p.feasible_fraction)}`}
                      style={{
                        height: `${p.feasible_fraction * 100}%`,
                      }}
                    />
                  ))}
                </div>
                <p className="caption">
                  Vertical scale: 0–100%. Bar height is the measured
                  valid-sample fraction, not return.
                </p>
              </section>
            ) : null}
            <details className="disclosure">
              <summary>Controller evidence and budget accounting</summary>
              <pre>
                {JSON.stringify(
                  {
                    budget: run.budget,
                    metadata: controllerRecord?.metadata,
                    context_ranker: run.context_ranker,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </div>
        ) : null}
        {tab === "record" ? (
          <>
            <div className="record-banner">
              <span>
                Immutable run <code>{run.run_id}</code>
              </span>
              <a
                className="button secondary"
                href={`/api/runs/${run.run_id}/export?format=json`}
              >
                Download JSON
              </a>
            </div>
            <dl className="record-list">
              <dt>Dataset fingerprint</dt>
              <dd className="mono wrap">{run.dataset_fingerprint}</dd>
              <dt>Estimation window</dt>
              <dd>
                {run.preparation.estimation_start} →{" "}
                {run.preparation.estimation_end}
              </dd>
              <dt>Return observations</dt>
              <dd>{run.preparation.return_observations}</dd>
              <dt>Eligible stocks at decision</dt>
              <dd>{run.preparation.eligible_count}</dd>
            </dl>
            <details className="disclosure">
              <summary>
                Settings, source code, package versions and full record
              </summary>
              <pre>{JSON.stringify(run, null, 2)}</pre>
            </details>
          </>
        ) : null}
      </div>
      <ResearchNote />
    </>
  );
}
