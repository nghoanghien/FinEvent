import { RunDetailPage } from "@/features/runs/RunDetailPage";
import type { Metadata } from "next";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ runId: string }>;
}): Promise<Metadata> {
  const { runId } = await params;
  return {
    title: `Run ${runId} Trace - FinEvent Control`,
    description: `Xem chi tiết bước chạy, milestone, hiện vật và logs của pipeline run ${runId}.`,
  };
}

export default async function Page({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <RunDetailPage runId={runId} />;
}
