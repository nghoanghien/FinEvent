"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  GitBranch,
  BarChart3,
  Bot,
  Boxes,
  Database,
  FileText,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useSidebar } from "./SidebarContext";

const navItems: { href: string; label: string; short: string; icon: LucideIcon }[] = [
  { href: "/admin", label: "Tổng quan", short: "OV", icon: LayoutDashboard },
  { href: "/admin/runs", label: "Workflow", short: "WF", icon: GitBranch },
  { href: "/admin/reports", label: "Báo cáo", short: "RP", icon: BarChart3 },
  { href: "/admin/database", label: "Database", short: "DB", icon: Database },
  { href: "/admin/outputs", label: "Outputs", short: "OUT", icon: Boxes },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isExpanded, toggleSidebar, isMounted } = useSidebar();

  // Handle server-side rendering state safely
  const currentExpanded = isMounted ? isExpanded : true;

  return (
    <aside
      className={`nav-container liquid-glass-container fixed left-0 top-0 bottom-0 z-50 hidden flex-col rounded-r-3xl border-r border-white/20 shadow-xl backdrop-blur-sm transition-all duration-500 ease-out md:flex ${
        currentExpanded ? "w-72 overflow-hidden" : "w-20 overflow-visible"
      }`}
      style={{
        background: currentExpanded
          ? "linear-gradient(135deg, rgba(120, 200, 65, 0.15) 0%, rgba(180, 229, 13, 0.1) 50%, rgba(120, 200, 65, 0.08) 100%)"
          : "linear-gradient(135deg, rgba(120, 200, 65, 0.2) 0%, rgba(180, 229, 13, 0.15) 100%)",
        boxShadow: currentExpanded
          ? "0 10px 30px rgba(0, 0, 0, 0.06), 0 0 30px rgba(120, 200, 65, 0.03)"
          : "0 8px 20px rgba(0, 0, 0, 0.05)",
      }}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-30 transition-transform duration-700 rounded-r-3xl"
        style={{
          background: `
            radial-gradient(circle at 20% 20%, rgba(120, 200, 65, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(180, 229, 13, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 40% 60%, rgba(120, 200, 65, 0.1) 0%, transparent 50%)
          `,
          filter: "blur(1px)",
          transform: currentExpanded ? "scale(1.1) rotate(2deg)" : "scale(1)",
        }}
      />

      {/* Header section with branding & toggle button */}
      <div className="relative flex h-16 items-center justify-between border-b border-white/20 px-5 transition-all duration-300">
        {currentExpanded ? (
          <>
            <div className="flex items-center gap-3 min-w-0 cursor-pointer" onClick={() => router.push("/admin")}>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/20 shadow-[inset_0_0_12px_rgba(255,255,255,0.3)] backdrop-blur-md">
                <Bot size={20} className="text-gray-700" strokeWidth={2.4} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-gray-800 tracking-tight leading-tight">FinEvent Admin</p>
                <p className="truncate text-[10px] font-semibold text-gray-600">NLP/RAG ops</p>
              </div>
            </div>
            <button
              onClick={toggleSidebar}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-white/20 hover:text-gray-900 transition-colors"
              title="Thu gọn Sidebar"
            >
              <PanelLeftClose size={18} strokeWidth={2} />
            </button>
          </>
        ) : (
          <button
            onClick={toggleSidebar}
            className="mx-auto flex h-10 w-10 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-gray-500 hover:bg-white/25 hover:text-gray-900 shadow-sm transition-all duration-300 hover:scale-105"
            title="Mở rộng Sidebar"
          >
            <PanelLeft size={18} strokeWidth={2.4} />
          </button>
        )}
      </div>

      {/* Nav items list. Using overflow-visible when collapsed to prevent tooltips from being clipped */}
      <div
        className={`relative flex flex-1 flex-col px-3 py-6 scrollbar-none transition-all ${
          currentExpanded ? "overflow-y-auto" : "overflow-visible"
        }`}
      >
        {currentExpanded && (
          <div className="mb-4 px-4">
            <p className="mb-1 overflow-hidden whitespace-nowrap text-[10px] font-bold uppercase tracking-widest text-gray-500 drop-shadow-sm">
              Quản trị workflow
            </p>
          </div>
        )}

        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
          return (
            <SidebarNavItem
              key={item.href}
              item={item}
              expanded={currentExpanded}
              active={active}
              onClick={() => router.push(item.href)}
            />
          );
        })}
      </div>

      {/* Settings & Profile Section at the bottom */}
      <div className="relative mt-auto border-t border-white/20 p-4 transition-all duration-300">
        <SidebarNavItem
          item={{ href: "/admin/settings", label: "API settings", short: "API", icon: FileText }}
          expanded={currentExpanded}
          active={pathname.startsWith("/admin/settings")}
          onClick={() => router.push("/admin/settings")}
        />

        {/* User profile details matching Claude style */}
        <div
          onClick={() => router.push("/admin")}
          className={`group relative mt-4 flex cursor-pointer items-center rounded-2xl p-2 transition-all duration-300 ${
            currentExpanded
              ? "hover:bg-white/15 hover:shadow-[inset_0_0_12px_rgba(255,255,255,0.4)]"
              : "justify-center"
          }`}
        >
          <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-800 text-white font-bold text-sm shadow-md transition-transform duration-300 group-hover:scale-105">
            NH
          </div>

          {currentExpanded ? (
            <div className="ml-3 min-w-0 flex-1">
              <p className="truncate text-xs font-bold text-gray-800 leading-tight">Nguyễn Hoàng Hiên</p>
              <p className="truncate text-[10px] font-semibold text-gray-500 leading-none mt-0.5">System Admin</p>
            </div>
          ) : (
            /* Custom tooltip on hover for user avatar when collapsed */
            <div className="pointer-events-none absolute left-full ml-4 z-[60] flex opacity-0 translate-x-2 scale-95 group-hover:opacity-100 group-hover:translate-x-0 group-hover:scale-100 transition-all duration-300 ease-out items-center">
              <div className="whitespace-nowrap rounded-lg bg-gray-950 px-3 py-1.5 text-xs font-semibold text-white shadow-2xl">
                Nguyễn Hoàng Hiên (Admin)
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function SidebarNavItem({
  item,
  expanded,
  active,
  onClick,
}: {
  item: { href: string; label: string; short: string; icon: LucideIcon };
  expanded: boolean;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = item.icon;
  return (
    <div
      onClick={onClick}
      className={`group relative my-1 flex cursor-pointer items-center rounded-xl px-4 py-3 transition-all duration-300 ${
        active
          ? "bg-white/20 text-gray-900 shadow-[inset_0_0_24px_16px_rgba(255,255,255,0.9)] backdrop-blur-sm"
          : "text-gray-600 hover:bg-white/10 hover:text-gray-900 hover:shadow-[inset_0_0_18px_12px_rgba(255,255,255,0.7)]"
      }`}
    >
      <div className={`${!expanded ? "mx-auto" : ""}`}>
        <Icon size={20} strokeWidth={2.3} className="text-current" />
      </div>
      {expanded ? (
        <span className="ml-3 overflow-hidden whitespace-nowrap text-sm font-bold">{item.label}</span>
      ) : (
        /* Custom Tooltip showing item label on hover */
        <div className="pointer-events-none absolute left-full ml-4 z-[60] flex opacity-0 translate-x-2 scale-95 group-hover:opacity-100 group-hover:translate-x-0 group-hover:scale-100 transition-all duration-300 ease-out items-center">
          <div className="whitespace-nowrap rounded-lg bg-gray-950 px-3 py-1.5 text-xs font-semibold text-white shadow-2xl">
            {item.label}
          </div>
        </div>
      )}
    </div>
  );
}
