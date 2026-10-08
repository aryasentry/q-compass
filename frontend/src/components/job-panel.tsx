"use client";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { fetcher, post } from "@/lib/api";
import { isActive } from "@/lib/format";
import type { JobDetail } from "@/lib/types";
import { Failure, Loading, PageHeading } from "./ui";

export function JobStatus({
  detail,
  cancel,
  busy,
}: {
  detail: JobDetail;
  cancel: () => void;
  busy: boolean;
}) {
  const { job, events } = detail;
  return (
    <>
      <section className="panel job-status">
        <div className="panel-heading">
          <div>
            <span className={`status ${job.status}`}>{job.status}</span>
            <h2>
              {job.config.kind === "download"
                ? "Data collection"
                : "Portfolio comparison"}
            </h2>
          </div>
          {isActive(job.status) ? (
            <button
              className="button secondary"
              onClick={cancel}
              disabled={busy || !!job.cancel_requested}
            >
              {job.cancel_requested ? "Cancellation requested" : "Cancel job"}
            </button>
          ) : null}
        </div>
        <p className="muted">
          One local worker. Refreshing this page does not create another job.
        </p>
        {job.error ? (
          <p className="notice danger" role="alert">
            {job.error}
          </p>
        ) : null}
        {job.status === "interrupted" ? (
          <p className="notice">
            The worker stopped before completion. This job was not silently
            restarted. Submit a new experiment to try again.
          </p>
        ) : null}
        {job.result_id ? (
          <Link
            className="button primary"
            href={`/experiments/${job.result_id}`}
          >
            Open saved result
          </Link>
        ) : job.status === "completed" && job.config.kind === "download" ? (
          <Link className="button primary" href="/data">
            Inspect downloaded data
          </Link>
        ) : null}
        <h3>Activity log</h3>
        <ol className="event-log" aria-label="Job activity">
          {events.length ? (
            events.map((e) => (
              <li key={e.id}>
                <time dateTime={e.time}>{e.time.slice(11, 19)} UTC</time>
                <span>{e.message}</span>
              </li>
            ))
          ) : (
            <li>
              <span>Waiting for the worker to report its first event.</span>
            </li>
          )}
        </ol>
      </section>
      <details className="disclosure">
        <summary>Submitted settings</summary>
        <pre>{JSON.stringify(job.config, null, 2)}</pre>
      </details>
    </>
  );
}
export function JobPanel({ id }: { id: string }) {
  const { data, error, isLoading, mutate } = useSWR<JobDetail>(
    `/api/jobs/${id}`,
    fetcher,
    { refreshInterval: (d) => (d && isActive(d.job.status) ? 1500 : 0) },
  );
  const [busy, setBusy] = useState(false),
    [failure, setFailure] = useState<unknown>(null);
  async function cancel() {
    setBusy(true);
    setFailure(null);
    try {
      await post(`jobs/${id}/cancel`);
      await mutate();
    } catch (err) {
      setFailure(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        title="Experiment activity"
        description={`Job ${id}`}
        action={
          <Link className="button secondary" href="/experiments">
            All experiments
          </Link>
        }
      />
      {error ? <Failure error={error} retry={() => void mutate()} /> : null}
      {failure ? (
        <Failure
          error={failure}
          title="Cancellation could not be confirmed"
          retryLabel="Retry cancellation"
          retry={cancel}
        />
      ) : null}
      {isLoading ? <Loading /> : null}
      {data ? <JobStatus detail={data} cancel={cancel} busy={busy} /> : null}
    </>
  );
}
