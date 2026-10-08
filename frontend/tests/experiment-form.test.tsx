import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExperimentForm } from "../src/components/experiment-form";

describe("explicit experiment submission", () => {
  // Configuration identifiers only: not substitute market observations.
  const datasets = [
    { dataset_id: "config-fixture", last_date: "2026-09-04", stock_count: 50 },
  ];
  it("does not submit on mount and reuses its token on a network retry", async () => {
    const submit = vi
      .fn()
      .mockRejectedValueOnce(new Error("Connection lost"))
      .mockResolvedValue({ job_id: "real-job-response" });
    const completed = vi.fn();
    render(
      <ExperimentForm
        datasets={datasets}
        submit={submit}
        onSubmitted={completed}
      />,
    );
    expect(submit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Run experiment" }));
    await screen.findByText("Connection lost");
    fireEvent.click(screen.getByRole("button", { name: "Run experiment" }));
    await waitFor(() =>
      expect(completed).toHaveBeenCalledWith("real-job-response"),
    );
    expect(submit.mock.calls[0][0].token).toEqual(
      submit.mock.calls[1][0].token,
    );
    expect(submit.mock.calls[1][0].config).toMatchObject({
      dataset_id: "config-fixture",
      n: 8,
      k: 4,
      seed: 42,
    });
  });
  it("rejects impossible weighting before creating a job", async () => {
    const submit = vi.fn();
    render(
      <ExperimentForm
        datasets={datasets}
        submit={submit}
        onSubmitted={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText("Holdings to select"), {
      target: { value: "1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run experiment" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "cannot invest 100%",
    );
    expect(submit).not.toHaveBeenCalled();
  });
});
