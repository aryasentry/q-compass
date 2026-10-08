"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="notice danger" role="alert">
      <h1>This view could not load</h1>
      <p>Your saved experiments have not been deleted or restarted.</p>
      <button className="button secondary" onClick={reset}>
        Try again
      </button>
    </div>
  );
}
