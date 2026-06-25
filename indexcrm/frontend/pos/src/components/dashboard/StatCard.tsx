import { LucideIcon } from "lucide-react";

type StatCardProps = {
  title: string;
  value: string;
  description?: string;
  icon: LucideIcon;
  tone?: "blue" | "green" | "amber" | "rose" | "slate";
};

const toneClasses = {
  blue: {
    card: "border-blue-200/60 bg-blue-50/60",
    icon: "bg-blue-100 text-blue-600",
    value: "text-blue-950",
  },
  green: {
    card: "border-emerald-200/60 bg-emerald-50/60",
    icon: "bg-emerald-100 text-emerald-600",
    value: "text-emerald-950",
  },
  amber: {
    card: "border-amber-200/60 bg-amber-50/60",
    icon: "bg-amber-100 text-amber-600",
    value: "text-amber-950",
  },
  rose: {
    card: "border-rose-200/60 bg-rose-50/60",
    icon: "bg-rose-100 text-rose-600",
    value: "text-rose-950",
  },
  slate: {
    card: "border-slate-200/60 bg-white",
    icon: "bg-slate-100 text-slate-600",
    value: "text-slate-900",
  },
};

export function StatCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "slate",
}: StatCardProps) {
  const colors = toneClasses[tone];

  return (
    <section
      className={`rounded-xl border p-5 shadow-sm transition hover:shadow-md ${colors.card}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-bold uppercase tracking-wider text-slate-500">
            {title}
          </p>
          <p className={`mt-1.5 break-words text-2xl font-black tracking-tight ${colors.value}`}>
            {value}
          </p>
        </div>
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${colors.icon}`}>
          <Icon aria-hidden="true" className="h-5 w-5" />
        </div>
      </div>
      {description ? (
        <p className="mt-3 text-sm font-semibold text-slate-500">
          {description}
        </p>
      ) : null}
    </section>
  );
}
