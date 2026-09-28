import React from "react";
import { cn } from "../../lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Rendered above the field as a label-caps caption; wired via htmlFor. */
  label?: string;
  /** Validation message; sets aria-invalid and is announced via aria-describedby. */
  error?: string;
  /** Helper text shown when there is no error. */
  hint?: string;
  /** Trailing adornment (icon or button), e.g. password reveal. */
  icon?: React.ReactNode;
  /** Amber scanner-well treatment for barcode/sku fields. */
  scanner?: boolean;
}

/**
 * Text field with industrial form styling: mono value, 2px frame,
 * 52px handheld / 48px desktop height, hard focus ring.
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, icon, scanner, id, ...props }, ref) => {
    const autoId = React.useId();
    const inputId = id ?? autoId;
    const describedBy = [error && `${inputId}-error`, hint && `${inputId}-hint`]
      .filter(Boolean)
      .join(" ");

    return (
      <div className="flex w-full flex-col gap-space-4">
        {label && (
          <label
            htmlFor={inputId}
            className="font-label-caps text-label-caps uppercase text-primary-container"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy || undefined}
            className={cn(
              "w-full rounded border-2 bg-white px-space-16 font-mono text-mono-md text-primary-container",
              "min-h-[52px] sm:min-h-touch-target-min",
              "placeholder:text-outline placeholder:font-mono placeholder:text-mono-md",
              "focus:outline-none focus:border-primary-container focus:ring-4 focus:ring-primary-container/15",
              error
                ? "border-status-danger focus:border-status-danger focus:ring-status-danger/15"
                : "border-frame-strong",
              scanner && "bg-[#FCF9F2] border-status-warning",
              icon && "pr-space-48",
              className
            )}
            {...props}
          />
          {icon && (
            <div className="absolute right-0 top-0 flex h-full w-touch-target-min items-center justify-center text-outline">
              {icon}
            </div>
          )}
        </div>
        {error ? (
          <span id={`${inputId}-error`} className="text-body-sm font-bold text-status-danger">
            {error}
          </span>
        ) : (
          hint && (
            <span id={`${inputId}-hint`} className="text-body-sm text-on-surface-variant">
              {hint}
            </span>
          )
        )}
      </div>
    );
  }
);
Input.displayName = "Input";
