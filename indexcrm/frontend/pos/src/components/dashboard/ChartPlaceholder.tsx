import { BarChart3 } from "lucide-react";

type ChartPlaceholderProps = {
  title: string;
  description?: string;
  values?: number[];
};

export function ChartPlaceholder({
  title,
  description,
  values = [],
}: ChartPlaceholderProps) {
  const maxValue = Math.max(...values, 0);

  return (
    <section className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-900">{title}</h2>
          {description ? (
            <p className="text-sm font-semibold text-slate-400">{description}</p>
          ) : null}
        </div>
        <BarChart3 aria-hidden="true" className="h-5 w-5 text-slate-400" />
      </div>
      {values.length > 0 && maxValue > 0 ? (
        <div className="flex h-56 items-end gap-2 rounded-xl border border-slate-100 bg-slate-50 p-4">
          {values.map((value, index) => (
            <div
              key={index}
              className="flex-1 rounded-lg bg-primary-500"
              style={{ height: `${Math.max(8, (value / maxValue) * 100)}%` }}
            />
          ))}
        </div>
      ) : (
        <div className="flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-center">
          <div>
            <BarChart3 aria-hidden="true" className="mx-auto h-8 w-8 text-slate-300" />
            <div className="mt-3 text-sm font-bold text-slate-500">
              Diagramma ma'lumoti hali mavjud emas
            </div>
            <div className="mt-1 text-sm font-semibold text-slate-400">
              Xulosa kartalari va jadvallar jonli API ma'lumotidan foydalanadi.
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
