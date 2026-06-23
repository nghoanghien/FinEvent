import type { ReactNode } from "react";
import { Filter, RefreshCw, RotateCcw, Search, X } from "lucide-react";

export function TableToolbar({
  title,
  description,
  searchTerm,
  activeFiltersCount = 0,
  onSearchClick,
  onFilterClick,
  onClearAll,
  onResetFilters,
  onRefresh,
  isRefreshing,
  extraActions,
}: {
  title: string;
  description: string;
  searchTerm?: string;
  activeFiltersCount?: number;
  onSearchClick?: () => void;
  onFilterClick?: () => void;
  onClearAll?: () => void;
  onResetFilters?: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  extraActions?: ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-6 bg-white p-8 pb-4 md:flex-row md:items-end">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <div className="h-6 w-1.5 rounded-full bg-primary" />
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">{title}</h3>
        </div>
        <p className="pl-3.5 text-sm font-medium text-gray-400">{description}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {onSearchClick ? (
          <button
            type="button"
            onClick={onSearchClick}
            className={`h-12 w-12 rounded-full transition-all duration-300 flex items-center justify-center group ${
              searchTerm
                ? "bg-primary text-white shadow-lg shadow-primary/30"
                : "bg-gray-100 text-gray-600 hover:-translate-y-0.5 hover:bg-white hover:shadow-xl"
            }`}
            title="Search"
          >
            <Search className={`h-5 w-5 ${searchTerm ? "animate-pulse" : "transition-transform group-hover:scale-110"}`} />
          </button>
        ) : null}

        {onFilterClick ? (
          activeFiltersCount > 0 ? (
            <div className="flex items-center gap-1 rounded-full border border-primary/40 bg-primary p-1 pr-2 shadow-lg shadow-primary/20">
              <button
                type="button"
                onClick={onFilterClick}
                className="flex items-center gap-2 rounded-full px-3 py-2.5 transition-colors hover:bg-black/10"
              >
                <Filter className="h-4 w-4 text-white" />
                <span className="text-xs font-bold uppercase text-white">Filtered</span>
              </button>
              <button
                type="button"
                onClick={onResetFilters}
                className="rounded-2xl p-1.5 text-white transition-colors hover:bg-black/10"
                title="Clear all filters"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={onFilterClick}
              className="h-12 w-12 rounded-full border border-gray-100 bg-gray-100 text-gray-600 shadow-sm transition-all duration-300 flex items-center justify-center group hover:-translate-y-0.5 hover:bg-white hover:shadow-xl"
              title="Filter"
            >
              <Filter className="h-5 w-5 transition-transform group-hover:scale-110" />
            </button>
          )
        ) : null}

        {onRefresh ? (
          <button
            type="button"
            onClick={onRefresh}
            className="eatzy-icon-button"
            title="Refresh"
          >
            <RefreshCw className={`h-5 w-5 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
        ) : null}

        {extraActions}

        {(searchTerm || activeFiltersCount > 0) && onClearAll ? (
          <button
            type="button"
            onClick={onClearAll}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-50 text-gray-400 transition-all hover:bg-red-50 hover:text-danger"
            title="Clear all"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
