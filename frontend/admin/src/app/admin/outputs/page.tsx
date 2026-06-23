import { OutputsPage } from "@/features/outputs/OutputsPage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Structured Event Outputs - FinEvent Control",
  description: "Xem kết quả trích xuất sự kiện tài chính có cấu trúc, kèm chỉ số chống ảo giác (hallucination).",
};

export default function Page() {
  return <OutputsPage />;
}
