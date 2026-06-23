import clsx from "clsx";
import type { ReactNode } from "react";
import { compactJson } from "@/lib/format";

export type Column<T> = {
  key: string;
  label: string;
  className?: string;
  render?: (row: T) => ReactNode;
};

export function DataTable<T extends Record<string, unknown>>({
  rows,
  columns,
  onRowClick,
  emptyText = "Không có dữ liệu.",
  isLoading = false,
  loadingRows = 6,
}: {
  rows: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  emptyText?: string;
  isLoading?: boolean;
  loadingRows?: number;
}) {
  return (
    <div className="overflow-hidden rounded-[32px] border border-gray-100/60 bg-white shadow-[0_8px_40px_rgba(0,0,0,0.04)]">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-white">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={clsx(
                    "whitespace-nowrap border-b border-gray-100 px-5 py-4 text-left text-[11px] font-black uppercase text-gray-400",
                    column.className,
                  )}
                >
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {isLoading ? (
              Array.from({ length: loadingRows }).map((_, rowIndex) => (
                <tr key={`loading-${rowIndex}`}>
                  {columns.map((column, columnIndex) => (
                    <td key={`${column.key}-${rowIndex}`} className="px-5 py-4">
                      <div
                        className={clsx(
                          "h-4 rounded-full shimmer-surface",
                          columnIndex === 0 ? "w-36" : columnIndex % 2 ? "w-24" : "w-28",
                        )}
                      />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length ? (
              rows.map((row, index) => (
                <tr
                  key={String(row.id || row.run_id || row.article_id || row.event_id || index)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={clsx("transition-colors", onRowClick && "cursor-pointer hover:bg-lime-50/40")}
                >
                  {columns.map((column) => (
                    <td key={column.key} className="max-w-[320px] px-5 py-4 text-gray-700">
                      {column.render ? column.render(row) : compactJson(row[column.key])}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-16 text-center text-sm font-medium text-gray-400">
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
