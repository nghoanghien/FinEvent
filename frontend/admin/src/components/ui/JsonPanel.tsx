export function JsonPanel({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[560px] overflow-auto rounded-lg border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
