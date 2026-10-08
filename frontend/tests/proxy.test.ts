// @vitest-environment node
import { describe, expect, it } from "vitest";
import { allowedRoute, safeOrigin, boundedBody } from "../src/lib/proxy";
describe("local API boundary", () => {
  it("only forwards scoped read and mutation routes", () => {
    expect(allowedRoute("GET", ["runs", "abc123", "export"])).toBe(true);
    expect(allowedRoute("POST", ["jobs", "abc123", "cancel"])).toBe(true);
    expect(allowedRoute("POST", ["jobs"])).toBe(true);
    expect(allowedRoute("GET", ["jobs", "abc123", "cancel"])).toBe(false);
    expect(allowedRoute("GET", ["..", "secrets"])).toBe(false);
    expect(allowedRoute("GET", ["runs", "a/b"])).toBe(false);
    expect(allowedRoute("DELETE", ["runs", "abc123"])).toBe(false);
  });
  it("rejects cross-site and opaque-origin mutations", () => {
    expect(
      safeOrigin(
        new Request("http://127.0.0.1:3000/api/jobs", {
          headers: { Origin: "https://evil.example" },
        }),
      ),
    ).toBe(false);
    expect(
      safeOrigin(
        new Request("http://127.0.0.1:3000/api/jobs", {
          headers: { Origin: "null" },
        }),
      ),
    ).toBe(false);
    expect(
      safeOrigin(
        new Request("http://127.0.0.1:3000/api/jobs", {
          headers: { Origin: "http://127.0.0.1:3000" },
        }),
      ),
    ).toBe(true);
  });
  it("bounds request bodies even without a content-length header", async () => {
    const small = new Request("http://localhost/api/jobs", {
      method: "POST",
      body: "{}",
    });
    expect(await boundedBody(small)).toBe("{}");
    const huge = new Request("http://localhost/api/jobs", {
      method: "POST",
      body: "x".repeat(65537),
    });
    await expect(boundedBody(huge)).rejects.toThrow("64 KiB");
  });
  it("uses the validated request Host when Next normalizes its internal URL", () => {
    const headers = { Host: "127.0.0.1:3000", Origin: "http://127.0.0.1:3000" };
    expect(
      safeOrigin(new Request("http://localhost:3000/api/jobs", { headers })),
    ).toBe(true);
    expect(
      safeOrigin(
        new Request("http://localhost:3000/api/jobs", {
          headers: { ...headers, Origin: "http://localhost:3000" },
        }),
      ),
    ).toBe(false);
    expect(
      safeOrigin(
        new Request("http://localhost:3000/api/jobs", {
          headers: { Host: "evil.example", Origin: "http://evil.example" },
        }),
      ),
    ).toBe(false);
  });
});
