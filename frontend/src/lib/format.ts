export function number(value: unknown, digits = 0): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumFractionDigits: digits })
    : "Unavailable";
}
export function percent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "Unavailable";
}
export function allocationRows(
  symbols: string[],
  allocation: { feasible?: boolean; weights?: number[] },
) {
  if (
    !allocation.feasible ||
    !allocation.weights ||
    allocation.weights.length !== symbols.length ||
    allocation.weights.some(
      (w) => !Number.isFinite(w) || w < -0.00002 || w > 1.00002,
    )
  )
    return [];
  return symbols
    .map((symbol, i) => ({ symbol, weight: allocation.weights![i] }))
    .filter((r) => r.weight > 0.00001);
}
export function isActive(status: string) {
  return status === "queued" || status === "running";
}
const methods: Record<string, string> = {
  exact: "Exhaustive reference",
  greedy_swaps: "Greedy + swaps",
  scip_subset: "SCIP reference",
  "qaoa-x-p1": "QAOA · depth 1",
  "qaoa-x-p2": "QAOA · depth 2",
  adaptive: "Adaptive QAOA",
  "equal-budget-search": "Equal-budget search",
};
export function methodLabel(method: string) {
  return methods[method] || method;
}
export function dateLabel(value?: string) {
  if (!value) return "Unavailable";
  const date = new Date(value.slice(0, 10) + "T12:00:00Z");
  return Number.isNaN(date.getTime())
    ? "Unavailable"
    : date.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      });
}
