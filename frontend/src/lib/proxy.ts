const identifier = /^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$/;
export function allowedRoute(method: string, segments: string[]) {
  if (!segments.length || segments.some((s) => !identifier.test(s)))
    return false;
  const path = segments.join("/");
  if (method === "GET")
    return (
      /^(health|datasets|runs|jobs)$/.test(path) ||
      /^(datasets|runs|jobs)\/[^/]+$/.test(path) ||
      /^runs\/[^/]+\/export$/.test(path)
    );
  if (method === "POST")
    return (
      /^(jobs|downloads)$/.test(path) ||
      /^jobs\/[^/]+\/cancel$/.test(path) ||
      /^datasets\/[^/]+\/verify$/.test(path)
    );
  return false;
}
export function safeOrigin(request: Request) {
  const url = new URL(request.url);
  if (!["localhost", "127.0.0.1"].includes(url.hostname)) return false;
  // Next may normalize request.url to localhost even when the browser used 127.0.0.1.
  // Host is browser-controlled only by navigation and must itself remain loopback.
  const host = request.headers.get("host") || url.host;
  if (
    !/^(localhost|127\.0\.0\.1)(:[0-9]{1,5})?$/.test(host) ||
    url.protocol !== "http:"
  )
    return false;
  const origin = request.headers.get("origin");
  return origin
    ? origin === `http://${host}`
    : request.headers.get("sec-fetch-site") !== "cross-site";
}
export async function boundedBody(request: Request) {
  const reader = request.body?.getReader();
  if (!reader) return "{}";
  const parts: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 65536) {
      await reader.cancel();
      throw new Error("Request exceeds 64 KiB");
    }
    parts.push(value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    bytes.set(part, offset);
    offset += part.length;
  }
  return new TextDecoder().decode(bytes);
}
