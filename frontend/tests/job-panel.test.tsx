import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { JobStatus } from "../src/components/job-panel";
import type { JobDetail } from "../src/lib/types";

// Queue metadata only. No fabricated financial observations or solver outputs.
const record: JobDetail = {
  job: {
    id: "queue-test",
    status: "running",
    created: "2026-09-05T00:00:00Z",
    updated: "2026-09-05T00:00:00Z",
    cancel_requested: 0,
    config: {},
  },
  events: [
    {
      id: 1,
      time: "2026-09-05T00:00:00Z",
      message: "Preparing validated data",
    },
  ],
};
it("only requests cancellation after a click and shows genuine log messages", () => {
  const cancel = vi.fn();
  render(<JobStatus detail={record} cancel={cancel} busy={false} />);
  expect(cancel).not.toHaveBeenCalled();
  expect(screen.getByText("Preparing validated data")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Cancel job" }));
  expect(cancel).toHaveBeenCalledOnce();
});
it("labels an interrupted job without inventing progress or results", () => {
  render(
    <JobStatus
      detail={{
        ...record,
        job: { ...record.job, status: "interrupted", error: "Worker exited" },
      }}
      cancel={vi.fn()}
      busy={false}
    />,
  );
  expect(
    screen.queryByRole("button", { name: "Cancel job" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Worker exited")).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Open saved result" }),
  ).not.toBeInTheDocument();
});
