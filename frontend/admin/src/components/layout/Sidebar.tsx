"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import {
  Activity,
  BarChart3,
  Bot,
  Boxes,
  Database,
  FileText,
  LayoutDashboard,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const navItems: { href: string; label: string; short: string; icon: LucideIcon }[] = [
  { href: "/admin", label: "Tổng quan", short: "OV", icon: LayoutDashboard },
  { href: "/admin/runs", label: "Workflow", short: "WF", icon: Activity },
  { href: "/admin/reports", label: "Báo cáo", short: "RP", icon: BarChart3 },
  { href: "/admin/database", label: "Database", short: "DB", icon: Database },
  { href: "/admin/outputs", label: "Outputs", short: "OUT", icon: Boxes },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);

  return (
    <aside
      className={`nav-container liquid-glass-container fixed left-6 z-50 hidden flex-col overflow-hidden rounded-3xl shadow-2xl backdrop-blur-sm transition-all duration-500 ease-out md:flex ${
        expanded ? "bottom-6 top-6 w-72" : "bottom-24 top-24 w-20"
      }`}
      style={{
        background: expanded
          ? "linear-gradient(135deg, rgba(120, 200, 65, 0.15) 0%, rgba(180, 229, 13, 0.1) 50%, rgba(120, 200, 65, 0.08) 100%)"
          : "linear-gradient(135deg, rgba(120, 200, 65, 0.2) 0%, rgba(180, 229, 13, 0.15) 100%)",
        boxShadow: expanded
          ? "0 25px 45px rgba(0, 0, 0, 0.15), 0 0 80px rgba(120, 200, 65, 0.1)"
          : "0 15px 25px -10px rgba(0,0,0,0.12), 0 0 20px -10px rgba(120,200,65,0.08)",
      }}
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-30 transition-transform duration-700"
        style={{
          background: `
            radial-gradient(circle at 20% 20%, rgba(120, 200, 65, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(180, 229, 13, 0.2) 0%, transparent 50%),
            radial-gradient(circle at 40% 60%, rgba(120, 200, 65, 0.1) 0%, transparent 50%)
          `,
          filter: "blur(1px)",
          transform: expanded ? "scale(1.1) rotate(2deg)" : "scale(1)",
        }}
      />

      <div
        onClick={() => router.push("/admin")}
        className="profile-section liquid-glass-nav-item group relative flex cursor-pointer items-center border-b border-white/30 p-6 shadow-[inset_0_0_12px_8px_rgba(255,255,255,0.1)] transition-all duration-300"
        style={{
          background: "linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)",
        }}
      >
        <div
          className="absolute inset-0 rounded-t-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{
            background: "linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(120, 200, 65, 0.1) 100%)",
            backdropFilter: "blur(10px)",
          }}
        />

        <div
          className={`relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/20 bg-white/20 shadow-[inset_0_0_12px_8px_rgba(255,255,255,0.3)] backdrop-blur-md transition-transform duration-300 group-hover:scale-110 ${
            !expanded ? "mx-auto" : ""
          }`}
        >
          <Bot size={22} className="text-gray-700 drop-shadow-sm" strokeWidth={2.4} />
        </div>
        {expanded ? (
          <div className="relative ml-4 min-w-0">
            <p className="truncate text-sm font-bold tracking-normal text-gray-800 drop-shadow-sm">FinEvent Admin</p>
            <p className="truncate text-xs font-medium tracking-normal text-gray-600 drop-shadow-sm">
              NLP/RAG operations
            </p>
          </div>
        ) : null}
      </div>

      <div className="relative flex flex-1 flex-col overflow-hidden px-3 py-6">
        <div className={`mb-4 ${expanded ? "px-4" : "text-center"}`}>
          <p className="mb-3 overflow-hidden whitespace-nowrap text-xs font-bold uppercase tracking-normal text-gray-600 drop-shadow-sm">
            {expanded ? "Quản trị workflow" : "FE"}
          </p>
        </div>

        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
          return (
            <SidebarNavItem
              key={item.href}
              item={item}
              expanded={expanded}
              active={active}
              onClick={() => router.push(item.href)}
            />
          );
        })}
      </div>

      <div
        className="relative border-t border-white/30 p-4"
        style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%)" }}
      >
        <SidebarNavItem
          item={{ href: "/admin/settings", label: "API settings", short: "API", icon: FileText }}
          expanded={expanded}
          active={pathname.startsWith("/admin/settings")}
          onClick={() => router.push("/admin/settings")}
        />
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
      title={item.label}
      onClick={onClick}
      className={`my-1 flex cursor-pointer items-center rounded-xl px-4 py-3 transition-all duration-300 ${
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
      ) : null}
    </div>
  );
}
