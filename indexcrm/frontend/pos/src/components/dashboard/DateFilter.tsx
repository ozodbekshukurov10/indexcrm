"use client";

type DateFilterProps = {
  dateFrom: string;
  dateTo: string;
  onChange: (value: { dateFrom: string; dateTo: string }) => void;
};

export function DateFilter({ dateFrom, dateTo, onChange }: DateFilterProps) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-100 bg-white p-3 shadow-sm sm:flex-row sm:items-end">
      <label className="block">
        <span className="mb-1 block text-xs font-bold uppercase tracking-wider text-slate-400">
          Dan
        </span>
        <input
          type="date"
          value={dateFrom}
          onChange={(event) =>
            onChange({ dateFrom: event.target.value, dateTo })
          }
          className="h-10 rounded-lg border border-slate-200 px-3 font-semibold transition focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
        />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-bold uppercase tracking-wider text-slate-400">
          Gacha
        </span>
        <input
          type="date"
          value={dateTo}
          onChange={(event) =>
            onChange({ dateFrom, dateTo: event.target.value })
          }
          className="h-10 rounded-lg border border-slate-200 px-3 font-semibold transition focus:border-primary-400 focus:outline-none focus:ring-4 focus:ring-primary-100"
        />
      </label>
    </div>
  );
}
