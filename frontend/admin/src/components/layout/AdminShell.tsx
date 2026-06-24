"use client";

import { SidebarProvider, useSidebar } from "./SidebarContext";
import { Sidebar } from "./Sidebar";

function AdminShellContent({ children }: { children: React.ReactNode }) {
  const { isExpanded } = useSidebar();

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      <Sidebar />
      <div
        className={`flex min-w-0 flex-col overflow-x-hidden transition-all duration-500 ease-out ${
          isExpanded ? "md:ml-72" : "md:ml-20"
        }`}
      >
        <main className="min-w-0 px-4 pb-10 pt-4 md:px-8">{children}</main>
      </div>
    </div>
  );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AdminShellContent>{children}</AdminShellContent>
    </SidebarProvider>
  );
}

