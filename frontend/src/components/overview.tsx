"use client";
import Link from "next/link";
import useSWR from "swr";
import { Plus } from "lucide-react";
import { fetcher } from "@/lib/api";
import { dateLabel, number } from "@/lib/format";
import type { Dataset, Run, RunSummary } from "@/lib/types";
import { Comparison, Allocation, AdaptiveSummary, NoRuns } from "./comparison";
import { Failure, Loading, PageHeading, ResearchNote, Warnings } from "./ui";
export function Overview() {
  const datasets = useSWR<{ datasets: Dataset[]; warnings: string[] }>(
    "/api/datasets",
    fetcher,
  );
  const runs = useSWR<{ runs: RunSummary[]; warnings: string[] }>(
    "/api/runs?limit=50",
    fetcher,
  );
  const latest = runs.data?.runs.find(
    (r) => r.kind === "optimization_comparison",
  );
  const result = useSWR<Run>(
    latest ? `/api/runs/${latest.run_id}` : null,
    fetcher,
  );
  const error = datasets.error || runs.error || result.error;
  const run = error ? undefined : result.data;
  const dataset = error
    ? undefined
    : run
      ? datasets.data?.datasets.find(
          (d) => d.dataset_id === run.instance.dataset_id,
        )
      : datasets.data?.datasets[0];
  return (
    <>
      <PageHeading
        title="Experiment overview"
        description="Real market data. Reproducible quantum experiments."
        action={
          <Link className="button primary" href="/experiments/new">
            <Plus size={20} />
            New experiment
          </Link>
        }
      />
      {error ? (
        <Failure
          error={error}
          retry={() => {
            void datasets.mutate();
            void runs.mutate();
            void result.mutate();
          }}
        />
      ) : null}
      {datasets.isLoading || runs.isLoading || result.isLoading ? (
        <Loading />
      ) : null}
      {run?.cancelled ? (
        <p className="notice">
          This run was cancelled. Results below are partial, not a completed
          comparison.
        </p>
      ) : null}
      {dataset ? (
        <>
          <div className="source-line">
            <span>NIFTY 50 · {dateLabel(dataset.last_date)}</span>
            <span>
              {run
                ? `Saved run · seed ${run.config.seed}`
                : "Frozen data snapshot"}
            </span>
          </div>
          <div className="stats">
            <div>
              <strong>{dataset.stock_count} / 50</strong>
              <span>Stock histories</span>
            </div>
            <div>
              <strong>{number(dataset.row_count)}</strong>
              <span>Validated daily records</span>
            </div>
            <div>
              <strong>
                {run
                  ? `${run.instance.symbols.length} → ${run.instance.k}`
                  : "—"}
              </strong>
              <span>Candidates → holdings</span>
            </div>
          </div>
        </>
      ) : null}
      {run ? (
        <div className="overview-grid">
          <Comparison run={run} />
          <div className="stack">
            <Allocation run={run} />
            <AdaptiveSummary run={run} />
          </div>
        </div>
      ) : !runs.isLoading && !error && !result.isLoading ? (
        <NoRuns />
      ) : null}
      <ResearchNote />
      <Warnings
        messages={[
          ...(datasets.data?.warnings || []),
          ...(runs.data?.warnings || []),
        ]}
      />
    </>
  );
}
