import { RunsPage } from "@/features/runs/RunsPage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pipeline Runner - FinEvent Control",
  description: "Khởi chạy và giám sát các pipeline trích xuất thông tin sự kiện tài chính thời gian thực.",
};

export default function Page() {
  return <RunsPage />;
}
