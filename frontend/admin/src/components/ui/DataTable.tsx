import clsx from "clsx";
import { compactJson } from "@/lib/format";

export type Column<T> = {
  key: string;
  label: string;
  className?: string;
  render?: (row: T) => React.ReactNode;
};

export function DataTable<T extends Record<string, unknown>>({
  rows,
  columns,
  onRowClick,
  emptyText = "Không có dữ liệu.",
}: {
  rows: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  emptyText?: string;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={clsx(
                    "whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500",
                    column.className,
                  )}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.length ? (
              rows.map((row, index) => (
                <tr
                  key={String(row.id || row.run_id || row.article_id || row.event_id || index)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={clsx(onRowClick && "cursor-pointer hover:bg-slate-50")}
                >
                  {columns.map((column) => (
                    <td key={column.key} className="max-w-[280px] px-4 py-3 text-slate-700">
                      {column.render ? column.render(row) : compactJson(row[column.key])}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-slate-500">
                  {emptyText}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
