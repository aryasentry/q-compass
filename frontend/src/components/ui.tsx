import Link from "next/link";
import {
  ArrowUpRight,
  FileText,
  AlertCircle,
  LoaderCircle,
} from "lucide-react";
export function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <FileText size={28} strokeWidth={1.4} />
      <h2>{title}</h2>
      <div className="muted">{children}</div>
    </div>
  );
}
export function Loading({
  label = "Reading verified local records…",
}: {
  label?: string;
}) {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={20} className="spin" />
      {label}
    </div>
  );
}
export function Failure({
  error,
  retry,
  title = "Unable to load these records",
  retryLabel = "Try again",
}: {
  error: unknown;
  retry?: () => void;
  title?: string;
  retryLabel?: string;
}) {
  return (
    <div className="notice danger" role="alert">
      <AlertCircle size={20} />
      <div>
        <strong>{title}</strong>
        <p>{error instanceof Error ? error.message : String(error)}</p>
        {retry ? (
          <button className="text-button" onClick={retry}>
            {retryLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}
export function Warnings({ messages }: { messages?: string[] }) {
  return messages?.length ? (
    <details className="notice">
      <summary>
        {messages.length} record warning{messages.length === 1 ? "" : "s"}
      </summary>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m}</li>
        ))}
      </ul>
    </details>
  ) : null;
}
export function ResearchNote() {
  return (
    <div className="research-note">
      <FileText size={24} strokeWidth={1.5} />
      <div>
        <strong>Research, not a quantum-advantage claim.</strong>
        <p>
          Current constituent snapshot. Historical membership still requires
          verification.
        </p>
      </div>
    </div>
  );
}
export function Valid({ value }: { value?: boolean }) {
  return (
    <span
      className={
        value === true ? "valid" : value === false ? "invalid" : "muted"
      }
    >
      {value === true ? "Yes" : value === false ? "No" : "Unavailable"}
    </span>
  );
}
export function DetailLink({ id }: { id: string }) {
  return (
    <Link className="text-link" href={`/experiments/${id}`}>
      Open run <ArrowUpRight size={15} />
    </Link>
  );
}
