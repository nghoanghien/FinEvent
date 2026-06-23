import { SettingsPage } from "@/features/settings/SettingsPage";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API Settings - FinEvent Control",
  description: "Cấu hình đường dẫn kết nối API FastAPI và thông tin xác thực quản trị viên (Admin API key).",
};

export default function Page() {
  return <SettingsPage />;
}
