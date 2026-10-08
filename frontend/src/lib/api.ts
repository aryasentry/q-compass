export async function fetcher<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(errorMessage(data.detail));
  return data;
}
function errorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (
    detail &&
    typeof detail === "object" &&
    "message" in detail &&
    typeof detail.message === "string"
  )
    return detail.message;
  if (Array.isArray(detail))
    return detail
      .map((d) => `${d.loc?.slice(1).join(".") || "Input"}: ${d.msg}`)
      .join("; ");
  return "The request could not be completed. Please retry.";
}
export async function post<T>(path: string, body: unknown = {}): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-QCompass-Client": "local-ui",
    },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(errorMessage(data.detail));
  return data;
}
