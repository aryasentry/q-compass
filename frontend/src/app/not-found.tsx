import Link from "next/link";
export default function NotFound() {
  return (
    <div className="empty">
      <h1>Page not found</h1>
      <p>This address does not identify a workspace page.</p>
      <Link className="button primary" href="/">
        Back to overview
      </Link>
    </div>
  );
}
