"use client";
import Link from "next/link";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Run } from "@/lib/types";
import { RunDetail } from "./run-detail";
import { Failure, Loading, PageHeading } from "./ui";
export function RunLoader({ id, tab }: { id: string; tab: string }) {
  const { data, error, isLoading, mutate } = useSWR<Run>(
    `/api/runs/${id}`,
    fetcher,
  );
  return (
    <>
      <PageHeading
        title={
          data?.kind === "optimization_comparison"
            ? "Portfolio comparison"
            : "Saved experiment"
        }
        description={`Run ${id.slice(0, 12)} · replaying a stored result`}
        action={
          <Link className="button secondary" href="/experiments">
            All experiments
          </Link>
        }
      />
      {error ? <Failure error={error} retry={() => void mutate()} /> : null}
      {isLoading ? <Loading /> : null}
      {data && !error ? (
        <>
          {data.cancelled ? (
            <p className="notice">
              This run was cancelled. Results below are partial, not a completed
              comparison.
            </p>
          ) : null}
          {data.kind === "optimization_comparison" ? (
            <RunDetail run={data} initialTab={tab} />
          ) : (
            <section className="panel study-record">
              <h2>{data.kind.replaceAll("_", " ")}</h2>
              <p>
                This is a saved study, not a single portfolio comparison. Its
                original record is available below.
              </p>
              <a
                href={`/api/runs/${id}/export?format=json`}
                className="button secondary"
              >
                Download JSON
              </a>
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </section>
          )}
        </>
      ) : null}
    </>
  );
}
