import React from "react";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RunDetail } from "../src/components/run-detail";
import type { Run } from "../src/lib/types";

function runWithMethods(
  runId: string,
  methods: Run["results"],
  includeAdaptive = true,
): Run {
  return {
    run_id: runId,
    kind: "optimization_comparison",
    created_at: "2026-09-05T00:00:00Z",
    dataset_fingerprint: "f".repeat(64),
    cancelled: false,
    config: { include_adaptive: includeAdaptive },
    results: methods,
    instance: {
      symbols: ["A", "B"],
      sectors: ["one", "two"],
      k: 1,
      as_of: "2026-09-04",
      dataset_id: "sealed",
      features: {},
    },
    budget: {},
    preparation: {
      eligible_count: 2,
      return_observations: 252,
      estimation_start: "2025-08-28",
      estimation_end: "2026-09-04",
      excluded: [],
    },
    software: {},
    limitations: [],
  };
}

function method(methodName: string, weights?: number[]) {
  return {
    method: methodName,
    status: weights ? "completed" : "failed",
    selection_feasible: Boolean(weights),
    allocation_feasible: Boolean(weights),
    allocation: weights ? { status: "optimal", weights } : undefined,
  };
}

describe("allocation method selection", () => {
  it("uses the first actual method without adaptive and resets consistently for a changed run", () => {
    const first = runWithMethods(
      "baseline-one",
      [method("exact", [1, 0]), method("qaoa-x-p1", [0, 1])],
      false,
    );
    const { rerender } = render(<RunDetail run={first} />);
    let select = screen.getByLabelText("Inspect allocation from") as HTMLSelectElement;
    let allocation = screen
      .getByRole("heading", { name: "Investment allocation" })
      .closest("section")!;
    expect(select.value).toBe("exact");
    expect(within(allocation).getByText("Exhaustive reference")).toBeInTheDocument();
    expect(within(allocation).getByText("A")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Controller" }));
    expect(screen.getByText(/adaptive controller was not run/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Results" }));

    const changed = runWithMethods(
      "baseline-two",
      [method("greedy_swaps", [0, 1]), method("exact", [1, 0])],
      false,
    );
    rerender(<RunDetail run={changed} />);
    select = screen.getByLabelText("Inspect allocation from") as HTMLSelectElement;
    allocation = screen
      .getByRole("heading", { name: "Investment allocation" })
      .closest("section")!;
    expect(select.value).toBe("greedy_swaps");
    expect(within(allocation).getByText("Greedy + swaps")).toBeInTheDocument();
    expect(within(allocation).getByText("B")).toBeInTheDocument();
  });

  it("keeps an explicitly selected failed method instead of substituting adaptive", () => {
    const run = runWithMethods("with-adaptive", [
      method("exact", [1, 0]),
      method("qaoa-x-p1"),
      method("adaptive", [0, 1]),
    ]);
    render(<RunDetail run={run} />);
    const select = screen.getByLabelText("Inspect allocation from") as HTMLSelectElement;
    expect(select.value).toBe("adaptive");
    fireEvent.change(select, { target: { value: "qaoa-x-p1" } });
    expect(select.value).toBe("qaoa-x-p1");
    expect(
      screen.getByText(/No feasible allocation was found by this method/),
    ).toBeInTheDocument();
  });

  it("shows a requested controller failure instead of calling the run baseline-only", () => {
    const run = runWithMethods("failed-controller", [
      method("exact", [1, 0]),
      {
        method: "Adaptive pilots",
        status: "failed",
        error: "RuntimeError: controller crashed",
      },
    ]);
    render(<RunDetail run={run} initialTab="controller" />);
    expect(screen.getByText("RuntimeError: controller crashed")).toBeInTheDocument();
    expect(screen.queryByText(/baseline-only comparison/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/controller was not run/i)).not.toBeInTheDocument();
  });
});

const fixture = path.resolve(
  import.meta.dirname,
  "../../artifacts/runs/1bb5086703ca4ababcfca63356072d21/result.json",
);
describe.skipIf(!existsSync(fixture))(
  "real saved experiment presentation",
  () => {
    it("renders measured methods and exposes pilot evidence on request", () => {
      const run = JSON.parse(readFileSync(fixture, "utf8")) as Run;
      render(<RunDetail run={run} />);
      expect(
        screen.getByRole("heading", { name: "Solver comparison" }),
      ).toBeInTheDocument();
      expect(screen.getAllByText("-0.11576").length).toBeGreaterThan(0);
      expect(screen.getByText("EICHERMOT")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("tab", { name: "Controller" }));
      expect(
        screen.getByText(/Penalized energies were not compared/),
      ).toBeInTheDocument();
      expect(screen.getByText("24,576")).toBeInTheDocument();
    });
    it("supports keyboard tab navigation and faithfully scales measured sample fractions", () => {
      const run = JSON.parse(readFileSync(fixture, "utf8")) as Run;
      const { container } = render(<RunDetail run={run} />);
      const results = screen.getByRole("tab", { name: "Results" });
      results.focus();
      fireEvent.keyDown(results, { key: "ArrowRight" });
      expect(screen.getByRole("tab", { name: "Controller" })).toHaveFocus();
      const trace = run.results.find((r) => r.method === "adaptive")!.trace!;
      const bars = container.querySelectorAll<HTMLElement>(".trace-bars>div");
      expect(bars.length).toBe(trace.length);
      bars.forEach((bar, i) =>
        expect(parseFloat(bar.style.height)).toBeCloseTo(
          trace[i].feasible_fraction * 100,
          8,
        ),
      );
    });
  },
);
