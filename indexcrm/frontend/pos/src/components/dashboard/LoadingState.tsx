type LoadingStateProps = {
  label?: string;
  description?: string;
};

export function LoadingState({
  label = "Yuklanmoqda",
  description = "Boshqaruv paneli ma'lumotlari tayyorlanmoqda.",
}: LoadingStateProps) {
  return (
    <div className="grid gap-3 rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
      <div>
        <div className="text-sm font-bold uppercase tracking-wider text-slate-400">{label}</div>
        <div className="mt-1 text-sm font-semibold text-slate-400">
          {description}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div
            key={item}
            className="h-28 animate-pulse rounded-xl border border-slate-100 bg-slate-50"
          />
        ))}
      </div>
    </div>
  );
}
