import { Sidebar } from "./Sidebar";

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Sidebar />
      <div className="flex min-w-0 flex-col overflow-x-hidden md:ml-28">
        <main className="min-w-0 px-4 pb-10 pt-4 md:px-8">{children}</main>
      </div>
    </div>
  );
}
