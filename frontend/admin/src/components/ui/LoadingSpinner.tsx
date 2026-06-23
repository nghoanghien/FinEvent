import clsx from "clsx";

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <span
      aria-label="Loading"
      className={clsx(
        "inline-block h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-primary",
        className,
      )}
    />
  );
}
