import { statusTone } from "@/shared/utils/format";

type Tone = "success" | "info" | "warning" | "danger" | "neutral";

const toneClass: Record<Tone, string> = {
  success: "border-primary/30 bg-lime-50 text-lime-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  warning: "border-warning/30 bg-orange-50 text-orange-700",
  danger: "border-danger/25 bg-red-50 text-red-700",
  neutral: "border-gray-200 bg-gray-50 text-gray-600",
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
      className={`inline-flex h-6 items-center rounded-full border px-2.5 text-xs font-medium ${toneClass[resolvedTone]} ${className || ""}`}
    >
      {value || "unknown"}
    </span>
  );
}
