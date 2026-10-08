"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Download, ShieldCheck } from "lucide-react";
import { fetcher, post } from "@/lib/api";
import { dateLabel, number } from "@/lib/format";
import type { Audit, Dataset } from "@/lib/types";
import { Empty, Failure, Loading, PageHeading, Warnings } from "./ui";

export function DataAudit() {
  const router = useRouter();
  const [selection, setSelection] = useState("");
  const [busy, setBusy] = useState("");
  const [failure, setFailure] = useState<unknown>(null);
  const [failedAction, setFailedAction] = useState<"download" | "verify">(
    "download",
  );
  const [verified, setVerified] = useState("");
  const token = useRef<string | null>(null);
  const listing = useSWR<{ datasets: Dataset[]; warnings: string[] }>(
    "/api/datasets",
    fetcher,
  );
  const id = selection || listing.data?.datasets[0]?.dataset_id;
  const detail = useSWR<Audit>(id ? `/api/datasets/${id}` : null, fetcher);
  const summary = listing.data?.datasets.find((d) => d.dataset_id === id);
  const audit = detail.data;
  async function collect() {
    setBusy("download");
    setFailure(null);
    token.current ||= crypto.randomUUID();
    try {
      const data = await post<{ job_id: string }>("downloads", {
        token: token.current,
      });
      token.current = null;
      router.push(`/jobs/${data.job_id}`);
    } catch (err) {
      setFailure(err);
      setFailedAction("download");
    } finally {
      setBusy("");
    }
  }
  async function verify() {
    setBusy("verify");
    setFailure(null);
    try {
      await post(`datasets/${id}/verify`);
      setVerified(id || "");
    } catch (err) {
      setFailure(err);
      setFailedAction("verify");
      setVerified("");
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageHeading
        title="Data sources"
        description="Know exactly which observations your experiment uses."
        action={
          <button
            className="button primary"
            disabled={!!busy}
            onClick={collect}
          >
            <Download size={18} />
            {busy === "download" ? "Queueing…" : "Collect new snapshot"}
          </button>
        }
      />
      <p className="notice">
        Constituents: official NSE records. Historical prices: Yahoo Finance, a
        secondary source. Collection may fail or quarantine records; missing
        prices are never invented or interpolated.
      </p>
      {listing.error || detail.error ? (
        <Failure
          error={listing.error || detail.error}
          retry={() => {
            setVerified("");
            void listing.mutate();
            void detail.mutate();
          }}
        />
      ) : null}
      {failure ? (
        <Failure
          error={failure}
          title={
            failedAction === "verify"
              ? "Source verification failed"
              : "Download could not be queued"
          }
          retryLabel={
            failedAction === "verify" ? "Retry verification" : "Retry download"
          }
          retry={failedAction === "verify" ? verify : collect}
        />
      ) : null}
      {listing.isLoading || detail.isLoading ? <Loading /> : null}
      <Warnings messages={listing.data?.warnings} />
      {listing.data?.datasets.length ? (
        <div className="snapshot-select">
          <label htmlFor="snapshot">Frozen dataset</label>
          <select
            id="snapshot"
            value={id}
            onChange={(e) => setSelection(e.target.value)}
          >
            {listing.data.datasets.map((d) => (
              <option key={d.dataset_id} value={d.dataset_id}>
                {dateLabel(d.last_date)} · {d.stock_count} histories ·{" "}
                {d.dataset_id}
              </option>
            ))}
          </select>
        </div>
      ) : !listing.isLoading && !listing.error ? (
        <Empty title="No validated snapshots">
          Collect a new snapshot, or use the documented genuine-file import
          workflow.
        </Empty>
      ) : null}
      {summary && audit && !listing.error && !detail.error && !failure ? (
        <>
          <div className="stats small">
            <div>
              <strong>{summary.stock_count} / 50</strong>
              <span>Stock histories</span>
            </div>
            <div>
              <strong>{number(summary.row_count)}</strong>
              <span>Validated records</span>
            </div>
            <div>
              <strong>{number(summary.quarantined_count)}</strong>
              <span>Quarantined records</span>
            </div>
          </div>
          <section className="panel audit-record">
            <div className="panel-heading">
              <h2>Source and integrity</h2>
              <button
                className="button secondary"
                disabled={!!busy}
                onClick={verify}
              >
                <ShieldCheck size={17} />
                {busy === "verify" ? "Verifying…" : "Verify files"}
              </button>
            </div>
            {verified === id ? (
              <p className="notice success" role="status">
                Source files and processed data match their recorded
                fingerprints.
              </p>
            ) : null}
            <dl className="record-list">
              <dt>Price coverage</dt>
              <dd>
                {dateLabel(summary.first_date)} → {dateLabel(summary.last_date)}
              </dd>
              <dt>Retrieved</dt>
              <dd>{dateLabel(summary.retrieved_at)}</dd>
              <dt>Adjustment convention</dt>
              <dd>
                {String(audit.manifest.adjustment_convention || "Unavailable")}
              </dd>
              <dt>Official cross-check</dt>
              <dd>
                {summary.crosscheck?.status || "Unavailable"}
                {summary.crosscheck?.date
                  ? ` · ${dateLabel(summary.crosscheck.date)}`
                  : ""}
                {Array.isArray(summary.crosscheck?.matches)
                  ? ` · ${summary.crosscheck.matches.length} matching closes`
                  : ""}
                . A one-session check does not verify all historical prices.
              </dd>
              <dt>Dataset fingerprint</dt>
              <dd className="mono wrap">{summary.fingerprint}</dd>
            </dl>
          </section>
          <section className="panel section-space">
            <div className="panel-heading">
              <h2>Current constituents</h2>
              <span className="caption">Membership is a current snapshot</span>
            </div>
            <div className="table-scroll constituent-table">
              <table>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Industry</th>
                    <th>ISIN</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.constituents.map((c) => (
                    <tr key={c.symbol}>
                      <td className="mono">{c.symbol}</td>
                      <td>{c.company || c.name || "Unavailable"}</td>
                      <td>{c.sector}</td>
                      <td className="mono">{c.isin}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <details className="disclosure">
            <summary>
              Quarantined records (first 100) and full source manifest
            </summary>
            <pre>
              {JSON.stringify(
                { quarantine: audit.quarantine, manifest: audit.manifest },
                null,
                2,
              )}
            </pre>
          </details>
          <p className="notice">
            Historical backtests need verified membership at each decision date
            and reliable corporate-action coverage. This current-universe
            snapshot does not satisfy that requirement by itself.
          </p>
        </>
      ) : null}
    </>
  );
}
