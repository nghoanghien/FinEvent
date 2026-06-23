"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Activity,
  BarChart3,
  Boxes,
  Database,
  FileText,
  LayoutDashboard,
  Settings,
} from "lucide-react";

const navItems = [
  { href: "/admin", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/admin/runs", label: "Workflow", icon: Activity },
  { href: "/admin/reports", label: "Báo cáo", icon: BarChart3 },
  { href: "/admin/database", label: "Database", icon: Database },
  { href: "/admin/outputs", label: "Outputs", icon: Boxes },
  { href: "/admin/settings", label: "Thiết lập", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white lg:block">
      <div className="flex h-full flex-col">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-white">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-950">FinEvent Admin</p>
              <p className="text-xs text-slate-500">NLP/RAG operations</p>
            </div>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const active =
              pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition",
                  active
                    ? "bg-slate-950 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto border-t border-slate-200 p-4">
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
            <p className="font-medium text-slate-700">Local-first dashboard</p>
            <p className="mt-1">UI chỉ gọi FastAPI admin API, không truy cập model hay DB trực tiếp.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
