import { Inbox } from "lucide-react";

type EmptyStateProps = {
  title: string;
  description?: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-xl p-6 text-center">
      <Inbox aria-hidden="true" className="h-8 w-8 text-slate-300" />
      <p className="mt-3 text-sm font-bold text-slate-500">{title}</p>
      {description ? (
        <p className="mt-1 text-sm font-semibold text-slate-400">{description}</p>
      ) : null}
    </div>
  );
}
