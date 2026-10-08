import React from "react";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Overview } from "../src/components/overview";
import { RunLoader } from "../src/components/run-loader";
import { DataAudit } from "../src/components/data-audit";
import { AdaptiveSummary } from "../src/components/comparison";
import type { Run } from "../src/lib/types";

const cache = vi.hoisted(
  () => new Map<string, { data: unknown; error?: Error; mutate: () => void }>(),
);
vi.mock("swr", () => ({
  default: (key: string) =>
    cache.get(key) || { data: undefined, isLoading: false, mutate: () => {} },
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("../src/lib/api", () => ({
  fetcher: vi.fn(),
  post: vi.fn().mockResolvedValue({ valid: true }),
}));
const root = path.resolve(import.meta.dirname, "../..");
const file = path.join(
  root,
  "artifacts/runs/1bb5086703ca4ababcfca63356072d21/result.json",
);
describe("empty local workspace",()=>{
  beforeEach(()=>cache.clear());
  it("does not invent metrics when there are no records",()=>{
    cache.set("/api/datasets",{data:{datasets:[],warnings:[]},mutate:vi.fn()});
    cache.set("/api/runs?limit=50",{data:{runs:[],warnings:[]},mutate:vi.fn()});
    render(<Overview/>);
    expect(screen.getByText("Your first experiment starts here")).toBeInTheDocument();
    expect(screen.queryByText("92,859")).not.toBeInTheDocument();
  });
  it("makes absent data explicit in the data source screen",()=>{
    cache.set("/api/datasets",{data:{datasets:[],warnings:[]},mutate:vi.fn()});
    render(<DataAudit/>);
    expect(screen.getByText("No validated snapshots")).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"Verify files"})).not.toBeInTheDocument();
  });
});
describe.skipIf(!existsSync(file))("truthful cached real records", () => {
  let run: Run;
  beforeEach(() => {
    cache.clear();
    run = JSON.parse(readFileSync(file, "utf8"));
    cache.set(`/api/runs/${run.run_id}`, { data: run, mutate: vi.fn() });
    cache.set("/api/runs?limit=50", {
      data: { runs: [{ run_id: run.run_id, kind: run.kind }], warnings: [] },
      mutate: vi.fn(),
    });
    const manifest = JSON.parse(
      readFileSync(
        path.join(root, `data/manifests/${run.instance.dataset_id}.json`),
        "utf8",
      ),
    );
    cache.set("/api/datasets", {
      data: {
        datasets: [
          { ...manifest, quarantined_count: manifest.quarantined_row_count },
        ],
        warnings: [],
      },
      mutate: vi.fn(),
    });
    cache.set(`/api/datasets/${manifest.dataset_id}`, {
      data: { manifest, constituents: [], quarantine: [] },
      mutate: vi.fn(),
    });
  });
  it("labels a cancelled overview as partial", () => {
    run.cancelled = true;
    render(<Overview />);
    expect(screen.getByText(/Results below are partial/)).toBeInTheDocument();
  });
  it("hides cached result metrics after failed integrity revalidation", () => {
    const { rerender } = render(<RunLoader id={run.run_id} tab="results" />);
    expect(
      screen.getByRole("heading", { name: "Solver comparison" }),
    ).toBeInTheDocument();
    cache.get(`/api/runs/${run.run_id}`)!.error = new Error(
      "Checksum mismatch",
    );
    rerender(<RunLoader id={run.run_id} tab="results" />);
    expect(
      screen.queryByRole("heading", { name: "Solver comparison" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Checksum mismatch");
  });
  it("hides cached overview metrics after failed integrity revalidation", () => {
    cache.get(`/api/runs/${run.run_id}`)!.error = new Error(
      "Checksum mismatch",
    );
    render(<Overview />);
    expect(
      screen.queryByRole("heading", { name: "Solver comparison" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("92,859")).not.toBeInTheDocument();
  });
  it("hides an earlier audit verification after a subsequent read fails", async () => {
    const { rerender } = render(<DataAudit />);
    fireEvent.click(screen.getByRole("button", { name: "Verify files" }));
    await screen.findByText(/Source files and processed data match/);
    cache.get(`/api/datasets/${run.instance.dataset_id}`)!.error = new Error(
      "Source checksum mismatch",
    );
    rerender(<DataAudit />);
    expect(
      screen.queryByText(/Source files and processed data match/),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Source and integrity" }),
    ).not.toBeInTheDocument();
  });
  it("does not infer continuation from a chosen configuration alone", () => {
    render(<AdaptiveSummary run={run} />);
    expect(
      screen.queryByText(/received the remaining budget/),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/selected from/)).toBeInTheDocument();
  });
});
