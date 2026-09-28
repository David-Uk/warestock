import React from "react";
import { cn } from "../../lib/utils";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: React.ReactNode;
  /** Secondary line under the label. */
  description?: string;
  error?: string;
}

/**
 * Rigid 22px sleeve, 2px border, navy fill when checked.
 * The whole row is the label so the hit area meets the 48px target.
 */
export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, error, className, id, ...props }, ref) => {
    const autoId = React.useId();
    const checkboxId = id ?? autoId;

    return (
      <label
        htmlFor={checkboxId}
        className={cn(
          "flex min-h-touch-target-min cursor-pointer items-center gap-space-12 rounded px-space-4",
          "text-body-md text-on-surface",
          error && "text-status-danger",
          className
        )}
      >
        <input
          ref={ref}
          id={checkboxId}
          type="checkbox"
          className="peer sr-only"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${checkboxId}-error` : undefined}
          {...props}
        />
        <span
          className={cn(
            "flex size-[22px] shrink-0 items-center justify-center rounded-xs border-2 bg-white transition-colors",
            "peer-checked:border-primary-container peer-checked:bg-primary-container",
            "peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary-container",
            error ? "border-status-danger" : "border-primary-container",
            "peer-checked:[&_.check-glyph]:opacity-100"
          )}
        >
          <span className="check-glyph material-symbols-outlined text-[16px] leading-none text-white opacity-0 transition-opacity">
            check
          </span>
        </span>
        <span className="flex flex-col gap-space-2">
          <span>{label}</span>
          {description && (
            <span className="text-body-sm text-on-surface-variant">{description}</span>
          )}
          {error && (
            <span id={`${checkboxId}-error`} className="text-body-sm font-bold text-status-danger">
              {error}
            </span>
          )}
        </span>
      </label>
    );
  }
);
Checkbox.displayName = "Checkbox";
