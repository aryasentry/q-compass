import { allowedRoute, boundedBody, safeOrigin } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function handle(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (!allowedRoute(request.method, path))
    return Response.json({ detail: "Unknown API route" }, { status: 404 });
  if (!safeOrigin(request))
    return Response.json(
      { detail: "Only same-origin local requests are accepted" },
      { status: 403 },
    );
  let body: string | undefined;
  if (request.method === "POST") {
    if (
      request.headers.get("x-qcompass-client") !== "local-ui" ||
      !request.headers.get("content-type")?.startsWith("application/json")
    )
      return Response.json(
        { detail: "Explicit JSON application request required" },
        { status: 403 },
      );
    try {
      body = await boundedBody(request);
      JSON.parse(body);
    } catch (error) {
      return Response.json(
        { detail: error instanceof Error ? error.message : "Invalid JSON" },
        { status: 400 },
      );
    }
  }
  const upstream = new URL(
    process.env.QCOMPASS_API_URL || "http://127.0.0.1:8000",
  );
  if (
    !["127.0.0.1", "localhost"].includes(upstream.hostname) ||
    upstream.protocol !== "http:"
  )
    return Response.json(
      { detail: "Backend must be a local HTTP service" },
      { status: 503 },
    );
  upstream.pathname = `/api/${path.join("/")}`;
  upstream.search = new URL(request.url).search;
  try {
    const response = await fetch(upstream, {
      method: request.method,
      body,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-QCompass-Client": "local-ui",
      },
      signal: AbortSignal.timeout(60000),
    });
    const headers = new Headers({ "Cache-Control": "no-store" });
    for (const key of ["content-type", "content-disposition"]) {
      const value = response.headers.get(key);
      if (value) headers.set(key, value);
    }
    return new Response(response.body, { status: response.status, headers });
  } catch {
    return Response.json(
      {
        detail:
          "The Python engine is unavailable. Start the local API on port 8000 and retry. Saved data has not been changed.",
      },
      { status: 502 },
    );
  }
}
export { handle as GET, handle as POST };
