import { JobPanel } from "@/components/job-panel";
import { notFound } from "next/navigation";
export const metadata = { title: "Experiment activity" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$/.test(id)) notFound();
  return <JobPanel id={id} />;
}
