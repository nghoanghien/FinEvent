export function JsonPanel({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[560px] overflow-auto rounded-[24px] border border-gray-900 bg-gray-950 p-4 text-xs leading-6 text-gray-100 shadow-inner">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
