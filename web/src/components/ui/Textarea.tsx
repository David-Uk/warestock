import React from "react";
import { cn } from "../../lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  /** Show a live "n / maxLength" counter (requires maxLength). */
  showCount?: boolean;
}

/** Multi-line field; resizable with an optional character counter. */
export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, hint, showCount, id, value, maxLength, onChange, ...props }, ref) => {
    const autoId = React.useId();
    const textareaId = id ?? autoId;
    // Uncontrolled fields need local tracking so the counter stays live.
    const [internalValue, setInternalValue] = React.useState("");
    const describedBy = [error && `${textareaId}-error`, hint && `${textareaId}-hint`]
      .filter(Boolean)
      .join(" ");
    const length = typeof value === "string" ? value.length : internalValue.length;

    return (
      <div className="flex w-full flex-col gap-space-4">
        {label && (
          <label
            htmlFor={textareaId}
            className="font-label-caps text-label-caps uppercase text-primary-container"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          value={value}
          maxLength={maxLength}
          onChange={(event) => {
            if (typeof value !== "string") setInternalValue(event.target.value);
            onChange?.(event);
          }}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          className={cn(
            "w-full resize-y rounded border-2 bg-white px-space-16 py-space-12 font-primary text-body-md text-on-surface",
            "min-h-[96px]",
            "placeholder:text-outline",
            "focus:outline-none focus:border-primary-container focus:ring-4 focus:ring-primary-container/15",
            error
              ? "border-status-danger focus:border-status-danger focus:ring-status-danger/15"
              : "border-frame-strong",
            className
          )}
          {...props}
        />
        <div className="flex justify-between gap-space-8">
          {error ? (
            <span id={`${textareaId}-error`} className="text-body-sm font-bold text-status-danger">
              {error}
            </span>
          ) : (
            hint && (
              <span id={`${textareaId}-hint`} className="text-body-sm text-on-surface-variant">
                {hint}
              </span>
            )
          )}
          {showCount && maxLength !== undefined && (
            <span
              className="ml-auto font-mono text-mono-sm text-on-surface-variant"
              aria-hidden="true"
            >
              {length}/{maxLength}
            </span>
          )}
        </div>
      </div>
    );
  }
);
Textarea.displayName = "Textarea";
