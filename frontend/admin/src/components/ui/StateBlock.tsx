import { AlertCircle, Inbox } from "lucide-react";
import { LoadingSpinner } from "./LoadingSpinner";

export function LoadingBlock({ label = "Đang tải dữ liệu..." }: { label?: string }) {
  return (
    <div className="panel flex min-h-[180px] items-center justify-center gap-3 p-8 text-sm font-medium text-gray-500">
      <LoadingSpinner />
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
      <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-gray-100 text-gray-400">
        <Inbox className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-sm font-black text-gray-900">{title}</h3>
      {description ? <p className="mt-1 max-w-md text-sm font-medium text-gray-500">{description}</p> : null}
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
    <div className="rounded-[32px] border border-danger/20 bg-red-50 p-5 shadow-finevent">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white text-danger shadow-sm">
          <AlertCircle className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-black text-red-950">{title}</h3>
          <p className="mt-1 text-sm font-medium text-red-700">{message}</p>
          {onRetry ? (
            <button type="button" onClick={onRetry} className="mt-4 finevent-secondary-button">
              Thử lại
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
