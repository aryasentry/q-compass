"use client";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Dataset } from "@/lib/types";
import { ExperimentForm } from "./experiment-form";
import { Failure, Loading, PageHeading, Warnings } from "./ui";
export function NewExperiment() {
  const router = useRouter();
  const { data, error, isLoading, mutate } = useSWR<{
    datasets: Dataset[];
    warnings: string[];
  }>("/api/datasets", fetcher);
  return (
    <>
      <PageHeading
        title="New experiment"
        description="Choose the rules. Compare every solver on the same problem."
      />
      {error ? <Failure error={error} retry={() => void mutate()} /> : null}
      {isLoading ? <Loading /> : null}
      <Warnings messages={data?.warnings} />
      {data ? (
        <ExperimentForm
          datasets={data.datasets}
          onSubmitted={(id) => router.push(`/jobs/${id}`)}
        />
      ) : null}
    </>
  );
}
