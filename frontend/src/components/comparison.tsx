"use client";
import Link from "next/link";
import { Download } from "lucide-react";
import { allocationRows, methodLabel, number, percent } from "@/lib/format";
import type { Method, Run } from "@/lib/types";
import { Empty, Valid } from "./ui";

export function Comparison({
  run,
  detailed = false,
}: {
  run: Run;
  detailed?: boolean;
}) {
  return (
    <section className="panel comparison">
      <div className="panel-heading">
        <h2>Solver comparison</h2>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Method</th>
              <th className="numeric">Selection score</th>
              <th className="numeric">Gap</th>
              <th>Selection</th>
              <th>Weights</th>
              {detailed ? (
                <>
                  <th className="numeric">Time (s)</th>
                  <th className="numeric">Shots</th>
                  <th>Status</th>
                </>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {run.results.map((row, i) => (
              <tr
                key={`${row.method}-${i}`}
                className={row.method === "adaptive" ? "highlight" : ""}
              >
                <td>{methodLabel(row.method)}</td>
                <td className="numeric mono">{number(row.objective, 5)}</td>
                <td className="numeric mono">{number(row.objective_gap, 6)}</td>
                <td>
                  <Valid value={row.selection_feasible} />
                </td>
                <td>
                  <Valid value={row.allocation_feasible} />
                </td>
                {detailed ? (
                  <>
                    <td className="numeric mono">
                      {number(row.total_seconds, 3)}
                    </td>
                    <td className="numeric mono">{number(row.shots_used)}</td>
                    <td>{row.status}</td>
                  </>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="table-caption">
        Lower score is better. Not realized investment returns.
      </p>
      <div className="panel-footer">
        <a
          className="text-link"
          href={`/api/runs/${run.run_id}/export?format=csv`}
        >
          <Download size={18} />
          Download CSV
        </a>
        {!detailed ? (
          <Link className="text-link" href={`/experiments/${run.run_id}`}>
            All metrics
          </Link>
        ) : null}
      </div>
    </section>
  );
}
export function Allocation({ run, method }: { run: Run; method?: Method }) {
  const selected =
    method ||
    run.results.find((r) => r.method === "adaptive") ||
    run.results[0];
  const rows = allocationRows(run.instance.symbols, {
    feasible: selected?.allocation_feasible,
    weights: selected?.allocation?.weights,
  });
  return (
    <section className="panel allocation">
      <h2>Investment allocation</h2>
      <p className="allocation-method">
        Method:{" "}
        <strong>
          {selected ? methodLabel(selected.method) : "Unavailable"}
        </strong>
      </p>
      {rows.length ? (
        <div className="weight-bars">
          {rows.map((row) => (
            <div key={row.symbol} className="weight-row">
              <span>{row.symbol}</span>
              <div className="weight-track">
                <div style={{ width: `${row.weight * 100}%` }} />
              </div>
              <strong className="mono">{percent(row.weight)}</strong>
            </div>
          ))}
        </div>
      ) : (
        <p className="notice">
          No feasible allocation was found by this method. It has not been
          replaced by another solver’s answer.
        </p>
      )}
    </section>
  );
}
export function AdaptiveSummary({ run }: { run: Run }) {
  const adaptive = run.results.find((r) => r.method === "adaptive");
  return (
    <section className="panel adaptive-summary">
      <h2>The adaptive decision</h2>
      {adaptive?.metadata?.chosen_config ? (
        <p>
          <strong>{methodLabel(adaptive.metadata.chosen_config)}</strong> was
          selected from {adaptive.pilots?.length ?? "the recorded"} pilot runs.
          Open the evidence for sampling costs and continuation details.
        </p>
      ) : (
        <p>
          {adaptive?.error || "No adaptive decision is available for this run."}
        </p>
      )}
      <Link
        className="text-link underline"
        href={`/experiments/${run.run_id}?tab=controller`}
      >
        View evidence
      </Link>
    </section>
  );
}
export function NoRuns() {
  return (
    <Empty title="Your first experiment starts here">
      <p>
        No saved optimization result is available. Run a comparison using a
        validated NIFTY snapshot.
      </p>
      <Link href="/experiments/new" className="button primary">
        New experiment
      </Link>
    </Empty>
  );
}
