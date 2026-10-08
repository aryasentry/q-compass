import { describe, expect, it } from "vitest";
import {
  number,
  percent,
  allocationRows,
  isActive,
  methodLabel,
} from "../src/lib/format";

describe("honest result presentation", () => {
  it("does not turn missing or nonfinite results into zero", () => {
    expect(number(null)).toBe("Unavailable");
    expect(number(undefined)).toBe("Unavailable");
    expect(number(NaN)).toBe("Unavailable");
    expect(number(0)).toBe("0");
    expect(percent(0.05)).toBe("5.0%");
  });
  it("matches allocation slots to identifiers and rejects unavailable allocations", () => {
    expect(
      allocationRows(["A", "B"], { feasible: true, weights: [0.25, 0.75] }),
    ).toEqual([
      { symbol: "A", weight: 0.25 },
      { symbol: "B", weight: 0.75 },
    ]);
    expect(allocationRows(["A"], { feasible: false, weights: [1] })).toEqual(
      [],
    );
    expect(
      allocationRows(["A", "B"], { feasible: true, weights: [1] }),
    ).toEqual([]);
  });
  it("only polls unfinished jobs and preserves unknown method names", () => {
    expect(isActive("queued")).toBe(true);
    expect(isActive("running")).toBe(true);
    expect(isActive("failed")).toBe(false);
    expect(isActive("cancelled")).toBe(false);
    expect(methodLabel("qaoa-x-p2")).toBe("QAOA · depth 2");
    expect(methodLabel("custom-xy")).toBe("custom-xy");
  });
});
