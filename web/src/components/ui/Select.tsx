import React from "react";
import { cn } from "../../lib/utils";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  /** Material Symbol shown inside the leading edge. */
  icon?: string;
  /** Options rendered as `<option>` children when `children` is not supplied. */
  options?: Array<{ value: string; label: string; disabled?: boolean }>;
}

/**
 * Native select with the industrial field treatment (styled with system
 * chevron so keyboard behaviour stays native).
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, hint, icon, options, id, children, ...props }, ref) => {
    const autoId = React.useId();
    const selectId = id ?? autoId;
    const describedBy = [error && `${selectId}-error`, hint && `${selectId}-hint`]
      .filter(Boolean)
      .join(" ");

    return (
      <div className="flex w-full flex-col gap-space-4">
        {label && (
          <label
            htmlFor={selectId}
            className="font-label-caps text-label-caps uppercase text-primary-container"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span
              className="material-symbols-outlined pointer-events-none absolute left-space-12 top-1/2 -translate-y-1/2 text-[20px] text-outline"
              aria-hidden="true"
            >
              {icon}
            </span>
          )}
          <select
            ref={ref}
            id={selectId}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy || undefined}
            className={cn(
              "w-full appearance-none rounded border-2 bg-white px-space-16 font-mono text-mono-md text-primary-container",
              "min-h-[52px] sm:min-h-touch-target-min",
              "focus:outline-none focus:border-primary-container focus:ring-4 focus:ring-primary-container/15",
              'bg-[url("data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2024%2024%27%3E%3Cpath%20fill%3D%27%2344474d%27%20d%3D%27M7%2010l5%205%205-5z%27%2F%3E%3C%2Fsvg%3E")] bg-[length:24px] bg-[right_8px_center] bg-no-repeat pr-space-48',
              error
                ? "border-status-danger focus:border-status-danger focus:ring-status-danger/15"
                : "border-frame-strong",
              icon && "pl-space-48",
              className
            )}
            {...props}
          >
            {children ??
              options?.map((option) => (
                <option key={option.value} value={option.value} disabled={option.disabled}>
                  {option.label}
                </option>
              ))}
          </select>
        </div>
        {error ? (
          <span id={`${selectId}-error`} className="text-body-sm font-bold text-status-danger">
            {error}
          </span>
        ) : (
          hint && (
            <span id={`${selectId}-hint`} className="text-body-sm text-on-surface-variant">
              {hint}
            </span>
          )
        )}
      </div>
    );
  }
);
Select.displayName = "Select";
