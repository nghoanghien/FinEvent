import type { LucideIcon } from "lucide-react";
import clsx from "clsx";

const toneClass = {
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
  sky: "border-sky-200 bg-sky-50 text-sky-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  rose: "border-rose-200 bg-rose-50 text-rose-700",
  slate: "border-slate-200 bg-slate-50 text-slate-700",
};

export function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "slate",
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  tone?: keyof typeof toneClass;
}) {
  return (
    <section className="panel p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
          <p className="mt-2 truncate text-2xl font-semibold text-slate-950">{value}</p>
        </div>
        <div className={clsx("rounded-lg border p-2.5", toneClass[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {description ? <p className="mt-3 text-sm text-slate-500">{description}</p> : null}
    </section>
  );
}
