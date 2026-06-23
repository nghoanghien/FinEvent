import type { LucideIcon } from "lucide-react";

const gradients = {
  blue: "linear-gradient(135deg, #6B73FF 0%, #000DFF 100%)",
  orange: "linear-gradient(135deg, #FCCF31 0%, #F55555 100%)",
  purple: "linear-gradient(135deg, #9796F0 0%, #FBC7D4 100%)",
  green: "linear-gradient(135deg, #43E97B 0%, #38F9D7 100%)",
};

const shadows = {
  blue: "0 10px 20px -5px rgba(0, 13, 255, 0.3)",
  orange: "0 10px 20px -5px rgba(245, 85, 85, 0.3)",
  purple: "0 10px 20px -5px rgba(151, 150, 240, 0.3)",
  green: "0 10px 20px -5px rgba(67, 233, 123, 0.3)",
};

const toneToColor = {
  emerald: "green",
  sky: "blue",
  amber: "orange",
  rose: "orange",
  slate: "purple",
} as const;

type LegacyTone = keyof typeof toneToColor;
type CardColor = keyof typeof gradients;

export function MetricCard({
  title,
  value,
  description,
  icon: Icon,
  tone,
  color,
  trendLabel,
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  tone?: LegacyTone;
  color?: CardColor;
  trendLabel?: string;
}) {
  const resolvedColor = color || toneToColor[tone || "slate"];
  return (
    <section
      className="group relative flex h-48 cursor-default animate-fade-in-up flex-col justify-between overflow-hidden rounded-[32px] p-6 text-white transition-transform duration-300 hover:-translate-y-1"
      style={{ background: gradients[resolvedColor], boxShadow: shadows[resolvedColor] }}
    >
      <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-white/10 blur-2xl transition-transform duration-700 group-hover:scale-150" />
      <div className="absolute bottom-[-20px] left-[-20px] h-24 w-24 rounded-full bg-white/10 blur-xl transition-transform duration-700 group-hover:scale-150" />

      <div className="relative z-10 flex items-start justify-between">
        <div className="w-fit rounded-2xl bg-white/20 p-3 backdrop-blur-md">
          <Icon size={24} className="text-white" strokeWidth={2.4} />
        </div>
        {trendLabel ? (
          <div className="rounded-full bg-white/20 px-3 py-1 text-xs font-bold backdrop-blur-sm">{trendLabel}</div>
        ) : null}
      </div>

      <div className="relative z-10">
        <h3 className="mb-1 text-sm font-medium text-white/80">{title}</h3>
        <div className="mb-1 truncate text-3xl font-bold">{value}</div>
        {description ? <p className="line-clamp-2 text-xs text-white/70">{description}</p> : null}
      </div>
    </section>
  );
}
