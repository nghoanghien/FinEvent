import { DatabasePage } from "@/features/database/DatabasePage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data Browser - FinEvent Control",
  description: "Giao diện duyệt cơ sở dữ liệu PostgreSQL và pgvector an toàn cho bài báo, chunk và embedding.",
};

export default function Page() {
  return <DatabasePage />;
}
