"use client";
import { useRef, useState } from "react";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { post } from "@/lib/api";
import { dateLabel } from "@/lib/format";

type Payload = { config: Record<string, unknown>; token: string };
type Props = {
  datasets: { dataset_id: string; last_date: string; stock_count: number }[];
  submit?: (payload: Payload) => Promise<{ job_id: string }>;
  onSubmitted: (id: string) => void;
};
const send = (payload: Payload) => post<{ job_id: string }>("jobs", payload);
export function ExperimentForm({
  datasets,
  submit = send,
  onSubmitted,
}: Props) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const attempt = useRef<{ key: string; token: string } | null>(null);
  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    const val = (key: string) => Number(data.get(key));
    const n = val("n"),
      k = val("k"),
      min = val("min_weight"),
      max = val("max_weight");
    if (k > n || min > max || k * max < 1 || k * min > 1) {
      setError(
        "These holding and weight limits cannot invest 100% of the portfolio.",
      );
      return;
    }
    const config: Record<string, unknown> = {
      dataset_id: data.get("dataset_id"),
      n,
      k,
      min_weight: min,
      max_weight: max,
      risk_aversion: val("risk_aversion"),
      sector_limit: val("sector_limit"),
      sector_weight_cap: val("sector_weight_cap"),
      batches: val("batches"),
      shots: val("shots"),
      max_seconds: val("max_seconds"),
      seed: val("seed"),
      repair: data.has("repair"),
      extra_baselines: true,
    };
    if (data.get("as_of")) config.as_of = data.get("as_of");
    const key = JSON.stringify(config);
    if (attempt.current?.key !== key)
      attempt.current = { key, token: crypto.randomUUID() };
    setBusy(true);
    setError("");
    try {
      const result = await submit({ config, token: attempt.current.token });
      onSubmitted(result.job_id);
      attempt.current = null;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to submit the experiment",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="experiment-form" onSubmit={onSubmit}>
      <fieldset disabled={busy || !datasets.length}>
        <section className="form-section">
          <div className="section-number">01</div>
          <div className="form-content">
            <h2>Market universe</h2>
            <p className="muted">
              Use a frozen snapshot. The same data goes to every solver.
            </p>
            <label htmlFor="dataset">Dataset snapshot</label>
            <select
              id="dataset"
              name="dataset_id"
              required
              defaultValue={datasets[0]?.dataset_id}
            >
              {datasets.map((d) => (
                <option key={d.dataset_id} value={d.dataset_id}>
                  NIFTY 50 · {dateLabel(d.last_date)} · {d.stock_count}{" "}
                  histories · {d.dataset_id.slice(-6)}
                </option>
              ))}
            </select>
            <div className="form-grid">
              <Field label="Candidate stocks" id="n">
                <select id="n" name="n" defaultValue="8">
                  <option>8</option>
                  <option>10</option>
                  <option>12</option>
                </select>
              </Field>
              <Field label="Holdings to select" id="k">
                <input
                  id="k"
                  name="k"
                  type="number"
                  min="1"
                  max="12"
                  defaultValue="4"
                  required
                />
              </Field>
            </div>
            <p className="caption">
              Candidates are selected deterministically across industries, not
              by historical performance.
            </p>
          </div>
        </section>
        <section className="form-section">
          <div className="section-number">02</div>
          <div className="form-content">
            <h2>Investment rules</h2>
            <p className="muted">
              Exactly K holdings, long-only weights and full investment.
            </p>
            <div className="form-grid">
              <Numeric
                label="Risk aversion"
                name="risk_aversion"
                value={1}
                min={0}
                max={100}
                step={0.25}
              />
              <Numeric
                label="Maximum holdings per industry"
                name="sector_limit"
                value={1}
                min={1}
                max={12}
              />
              <Numeric
                label="Minimum weight per holding"
                name="min_weight"
                value={0.05}
                min={0.01}
                max={1}
                step={0.01}
              />
              <Numeric
                label="Maximum weight per holding"
                name="max_weight"
                value={0.5}
                min={0.05}
                max={1}
                step={0.05}
              />
              <Numeric
                label="Maximum weight per industry"
                name="sector_weight_cap"
                value={0.5}
                min={0.05}
                max={1}
                step={0.05}
              />
              <Numeric
                label="Random seed"
                name="seed"
                value={42}
                min={0}
                max={2147483647}
              />
            </div>
          </div>
        </section>
        <section className="form-section">
          <div className="section-number">03</div>
          <div className="form-content">
            <h2>Simulation budget</h2>
            <p className="muted">
              Depths 1 and 2, pilot-adaptive QAOA and equal-budget search.
            </p>
            <div className="form-grid">
              <Numeric
                label="Sample batches per method"
                name="batches"
                value={48}
                min={12}
                max={256}
              />
              <Field label="Shots per batch" id="shots">
                <select name="shots" id="shots" defaultValue="512">
                  {[128, 256, 512, 1024, 2048].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </Field>
              <Numeric
                label="Seconds per quantum method"
                name="max_seconds"
                value={180}
                min={5}
                max={600}
              />
              <Field label="Decision date (optional)" id="as_of">
                <input id="as_of" type="date" name="as_of" />
              </Field>
            </div>
            <label className="check">
              <input type="checkbox" name="repair" /> Also record bounded
              classical repair
            </label>
            <p className="caption">
              Pilot runs and final sampling count toward the budget. Past dates
              still use today’s membership; this is not a bias-free historical
              backtest.
            </p>
          </div>
        </section>
      </fieldset>
      {error ? (
        <div className="notice danger" role="alert">
          {error}
        </div>
      ) : null}
      {!datasets.length ? (
        <p className="notice">
          No validated dataset is available. Collect or import genuine data
          first.
        </p>
      ) : null}
      <div className="form-footer">
        <span className="caption">
          Local simulation only. No trades are placed.
        </span>
        <button
          className="button primary"
          type="submit"
          disabled={busy || !datasets.length}
        >
          {busy ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <ArrowRight size={17} />
          )}{" "}
          {busy ? "Submitting…" : "Run experiment"}
        </button>
      </div>
    </form>
  );
}
function Field({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id}>{label}</label>
      {children}
    </div>
  );
}
function Numeric({
  label,
  name,
  value,
  min,
  max,
  step = 1,
}: {
  label: string;
  name: string;
  value: number;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <Field label={label} id={name}>
      <input
        name={name}
        id={name}
        type="number"
        defaultValue={value}
        min={min}
        max={max}
        step={step}
        required
      />
    </Field>
  );
}
