import type { LucideIcon, LucideProps } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  icon: Icon,
  actions,
  minimal = false,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  actions?: ReactNode;
  minimal?: boolean;
}) {
  if (minimal) {
    return (
      <div className="px-2 pt-2 lg:px-0">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-lime-100 px-2.5 py-1 text-[10px] font-bold uppercase text-lime-700">
            {Icon ? <Icon size={12} strokeWidth={2.4} /> : null}
            {eyebrow}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-2 pt-2 lg:px-0">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-lime-100 px-2.5 py-1 text-[10px] font-bold uppercase text-lime-700">
              {Icon ? <Icon size={12} strokeWidth={2.4} /> : null}
              {eyebrow}
            </span>
          </div>
          <h1 className="font-anton text-4xl font-black uppercase leading-tight text-gray-900">
            {title}
          </h1>
          {description ? <p className="mt-2 max-w-3xl text-sm font-medium text-gray-500">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </div>
  );
}

export function HeaderActionIcon({ icon: Icon }: { icon: (props: LucideProps) => JSX.Element }) {
  return <Icon className="h-4 w-4" strokeWidth={2.4} />;
}
