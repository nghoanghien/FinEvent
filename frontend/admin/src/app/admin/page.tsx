import { DashboardPage } from "@/features/dashboard/DashboardPage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Overview - FinEvent Control",
  description: "Theo dõi trạng thái hệ thống, lịch sử chạy workflow, và các báo cáo phân tích sự kiện tài chính.",
};

export default function Page() {
  return <DashboardPage />;
}
