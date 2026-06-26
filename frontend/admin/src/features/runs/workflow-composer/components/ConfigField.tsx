"use client";

import type { WorkflowFieldDefinition } from "../types";

type ConfigFieldProps = {
  field: WorkflowFieldDefinition;
  value: any;
  onChange: (value: any) => void;
};

export function ConfigField({ field, value, onChange }: ConfigFieldProps) {
  return (
    <div className="flex flex-col gap-2 rounded-[20px] border border-gray-100 bg-gray-50/50 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="text-sm font-bold text-gray-800">{field.label}</span>
          {field.description ? (
            <span className="mt-0.5 block text-xs font-semibold leading-5 text-gray-400">
              {field.description}
            </span>
          ) : null}
        </div>

        {/* Toggle switch rendering directly in the header for checkbox types */}
        {field.type === "checkbox" ? (
          <button
            type="button"
            onClick={() => onChange(!Boolean(value))}
            className={[
              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
              value ? "bg-primary" : "bg-gray-200",
            ].join(" ")}
          >
            <span
              className={[
                "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                value ? "translate-x-5" : "translate-x-0",
              ].join(" ")}
            />
          </button>
        ) : null}
      </div>

      <div className="mt-1">
        {field.type === "text" ? (
          <input
            value={String(value || "")}
            onChange={(event) => onChange(event.target.value)}
            className="focus-ring h-11 w-full rounded-full border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-700 shadow-sm"
          />
        ) : null}

        {field.type === "number" ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() =>
                onChange(Math.max(field.min ?? 0, Number(value ?? 0) - (field.step ?? 1)))
              }
              className="focus-ring flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 font-bold transition shadow-sm active:scale-95"
            >
              -
            </button>
            <input
              type="number"
              min={field.min}
              max={field.max}
              step={field.step}
              value={Number(value ?? 0)}
              onChange={(event) => onChange(Number(event.target.value))}
              className="focus-ring h-11 w-28 text-center rounded-full border border-gray-200 bg-white text-sm font-bold text-gray-700 shadow-sm"
            />
            <button
              type="button"
              onClick={() =>
                onChange(Math.min(field.max ?? Infinity, Number(value ?? 0) + (field.step ?? 1)))
              }
              className="focus-ring flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 font-bold transition shadow-sm active:scale-95"
            >
              +
            </button>
          </div>
        ) : null}

        {field.type === "select" ? (
          <div className="relative">
            <select
              value={String(value || "")}
              onChange={(event) => onChange(event.target.value)}
              className="focus-ring h-11 w-full appearance-none rounded-full border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-700 shadow-sm"
            >
              {(field.options || []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
              <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
              </svg>
            </div>
          </div>
        ) : null}

        {field.type === "multi-select" ? (
          <div className="flex flex-wrap gap-2">
            {(field.options || []).map((option) => {
              const values = Array.isArray(value)
                ? value.filter((item): item is string => typeof item === "string")
                : [];
              const selected = values.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() =>
                    onChange(
                      selected
                        ? values.filter((item) => item !== option.value)
                        : [...values, option.value],
                    )
                  }
                  className={[
                    "focus-ring h-10 rounded-full border px-4 text-xs font-bold transition duration-200 active:scale-95",
                    selected
                      ? "border-primary bg-lime-50 text-gray-950 shadow-sm"
                      : "border-gray-200 bg-white text-gray-500 hover:border-gray-300 hover:text-gray-900 shadow-sm",
                  ].join(" ")}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}
