import { ReportsPage } from "@/features/reports/ReportsPage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Report Vault - FinEvent Control",
  description: "Kho lưu trữ và hiển thị các báo cáo phân tích, biểu đồ và kết quả đánh giá chất lượng RAG.",
};

export default function Page() {
  return <ReportsPage />;
}
