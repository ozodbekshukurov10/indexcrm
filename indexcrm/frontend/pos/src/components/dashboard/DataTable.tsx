import { ReactNode } from "react";

import { EmptyState } from "./EmptyState";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
};

type DataTableProps<T> = {
  title?: string;
  rows: T[];
  columns: Array<DataTableColumn<T>>;
  rowKey?: (row: T, rowIndex: number) => string | number;
  emptyTitle?: string;
  emptyDescription?: string;
};

const alignClasses = {
  left: "text-left",
  right: "text-right",
  center: "text-center",
};

export function DataTable<T>({
  title,
  rows,
  columns,
  rowKey,
  emptyTitle = "Ma'lumot yo'q",
  emptyDescription,
}: DataTableProps<T>) {
  return (
    <section className="glass-card overflow-hidden rounded-xl shadow-glass">
      {title ? (
        <div className="border-b border-white/20 px-5 py-4">
          <h2 className="text-base font-black tracking-tight text-slate-900">
            {title}
          </h2>
        </div>
      ) : null}
      {rows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-white/20 bg-white/30 text-xs uppercase text-slate-500">
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={`px-5 py-3.5 font-black tracking-wider ${alignClasses[column.align ?? "left"]}`}
                  >
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr
                  key={rowKey ? rowKey(row, rowIndex) : rowIndex}
                  className="border-b border-white/20 last:border-0 transition hover:bg-white/30"
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`px-5 py-3.5 font-semibold text-slate-700 ${alignClasses[column.align ?? "left"]}`}
                    >
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
