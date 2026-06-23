import clsx from "clsx";
import { statusTone } from "@/lib/format";

type Tone = "success" | "info" | "warning" | "danger" | "neutral";

const toneClass: Record<Tone, string> = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  neutral: "border-slate-200 bg-slate-50 text-slate-700",
};

export function StatusBadge({
  value,
  tone,
  className,
}: {
  value?: string | null;
  tone?: Tone;
  className?: string;
}) {
  const resolvedTone = tone || (statusTone(value || "") as Tone);
  return (
    <span
      className={clsx(
        "inline-flex h-6 items-center rounded-full border px-2.5 text-xs font-medium",
        toneClass[resolvedTone],
        className,
      )}
    >
      {value || "unknown"}
    </span>
  );
}
