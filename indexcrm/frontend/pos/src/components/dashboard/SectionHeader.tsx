import { ReactNode } from "react";

type SectionHeaderProps = {
  title: string;
  description: string;
  actions?: ReactNode;
};

export function SectionHeader({ title, description, actions }: SectionHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-900">
          {title}
        </h1>
        <p className="mt-1 text-sm font-semibold text-slate-400">{description}</p>
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  );
}
