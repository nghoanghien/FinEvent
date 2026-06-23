import { AlertCircle, Inbox, Loader2 } from "lucide-react";

export function LoadingBlock({ label = "Đang tải dữ liệu..." }: { label?: string }) {
  return (
    <div className="panel flex min-h-[180px] items-center justify-center gap-3 p-8 text-sm text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
      {label}
    </div>
  );
}

export function EmptyBlock({
  title = "Chưa có dữ liệu",
  description,
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="panel flex min-h-[180px] flex-col items-center justify-center p-8 text-center">
      <Inbox className="h-8 w-8 text-slate-400" />
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      {description ? <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p> : null}
    </div>
  );
}

export function ErrorBlock({
  title = "Không thể tải dữ liệu",
  error,
  onRetry,
}: {
  title?: string;
  error: unknown;
  onRetry?: () => void;
}) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="panel border-red-200 bg-red-50 p-5">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-red-900">{title}</h3>
          <p className="mt-1 text-sm text-red-700">{message}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="focus-ring mt-4 rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              Thử lại
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
