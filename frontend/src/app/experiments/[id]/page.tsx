import { RunLoader } from "@/components/run-loader";
import { notFound } from "next/navigation";
export const metadata = { title: "Saved experiment" };
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const [{ id }, { tab }] = await Promise.all([params, searchParams]);
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$/.test(id)) notFound();
  return (
    <RunLoader
      id={id}
      tab={tab === "controller" || tab === "record" ? tab : "results"}
    />
  );
}
