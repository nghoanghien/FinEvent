import { RunDetailPage } from "@/features/runs/RunDetailPage";

export default async function Page({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <RunDetailPage runId={runId} />;
}
