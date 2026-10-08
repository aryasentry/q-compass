"use client";
import Link from "next/link";
import useSWR from "swr";
import { Plus, ArrowUpRight } from "lucide-react";
import { fetcher } from "@/lib/api";
import { dateLabel, isActive } from "@/lib/format";
import type { Job, RunSummary } from "@/lib/types";
import { Empty, Failure, Loading, PageHeading, Warnings } from "./ui";

export function Experiments() {
  const runs = useSWR<{ runs: RunSummary[]; warnings: string[] }>(
    "/api/runs?limit=50",
    fetcher,
  );
  const jobs = useSWR<{ jobs: Job[] }>("/api/jobs", fetcher, {
    refreshInterval: (d) =>
      d?.jobs.some((j) => isActive(j.status)) ? 2000 : 0,
  });
  return (
    <>
      <PageHeading
        title="Experiments"
        description="New comparisons and saved evidence, in one workspace."
        action={
          <Link className="button primary" href="/experiments/new">
            <Plus size={19} />
            New experiment
          </Link>
        }
      />
      {runs.error || jobs.error ? (
        <Failure
          error={runs.error || jobs.error}
          retry={() => {
            void runs.mutate();
            void jobs.mutate();
          }}
        />
      ) : null}
      {runs.isLoading || jobs.isLoading ? <Loading /> : null}
      <Warnings messages={runs.data?.warnings} />
      {jobs.data?.jobs.length ? (
        <section className="panel section-space">
          <div className="panel-heading">
            <h2>Job queue</h2>
            <span className="caption">Shared with Streamlit</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>Activity</th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.jobs.slice(0, 20).map((j) => (
                  <tr key={j.id}>
                    <td>
                      <span>
                        {j.config.kind === "download"
                          ? "Data collection"
                          : "Portfolio comparison"}
                      </span>
                      <code className="table-sub">{j.id.slice(0, 12)}</code>
                    </td>
                    <td>{dateLabel(j.created)}</td>
                    <td>
                      <span className={`status ${j.status}`}>{j.status}</span>
                    </td>
                    <td>
                      <Link className="text-link" href={`/jobs/${j.id}`}>
                        View log <ArrowUpRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      <section className="panel">
        <div className="panel-heading">
          <h2>Saved runs</h2>
          <span className="caption">Latest 50 verified records</span>
        </div>
        {runs.data?.runs.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Decision date</th>
                  <th>Universe</th>
                  <th>Methods</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {runs.data.runs.map((r) => (
                  <tr key={r.run_id}>
                    <td>
                      <strong>
                        {r.kind === "optimization_comparison"
                          ? "Portfolio comparison"
                          : r.kind.replaceAll("_", " ")}
                      </strong>
                      <code className="table-sub">
                        {r.run_id.slice(0, 12)} · seed {r.seed ?? "unavailable"}
                      </code>
                    </td>
                    <td>{dateLabel(r.as_of)}</td>
                    <td>{r.n && r.k ? `${r.n} → ${r.k}` : "Study"}</td>
                    <td>{r.methods.length}</td>
                    <td>
                      <Link
                        className="text-link"
                        href={`/experiments/${r.run_id}`}
                      >
                        {r.cancelled ? "Partial record" : "Open run"}
                        <ArrowUpRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : !runs.isLoading && !runs.error ? (
          <Empty title="No saved runs yet">
            A completed experiment will appear here.
          </Empty>
        ) : null}
      </section>
    </>
  );
}
