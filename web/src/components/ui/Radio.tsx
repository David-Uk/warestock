import React from "react";
import { cn } from "../../lib/utils";

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: React.ReactNode;
  description?: string;
}

/**
 * Same rigid sleeve language as Checkbox, circular with a navy core dot.
 * Wrap a set in <RadioGroup> for the fieldset/legend semantics.
 */
export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ label, description, className, id, ...props }, ref) => {
    const autoId = React.useId();
    const radioId = id ?? autoId;

    return (
      <label
        htmlFor={radioId}
        className={cn(
          "flex min-h-touch-target-min cursor-pointer items-center gap-space-12 rounded px-space-4",
          "text-body-md text-on-surface",
          className
        )}
      >
        <input ref={ref} id={radioId} type="radio" className="peer sr-only" {...props} />
        <span
          className={cn(
            "flex size-[22px] shrink-0 items-center justify-center rounded-full border-2 bg-white transition-colors",
            "peer-checked:border-primary-container peer-checked:bg-primary-container",
            "peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary-container",
            "border-primary-container",
            "peer-checked:[&_.dot]:opacity-100"
          )}
        >
          <span className="dot size-[8px] rounded-full bg-white opacity-0 transition-opacity" />
        </span>
        <span className="flex flex-col gap-space-2">
          <span>{label}</span>
          {description && (
            <span className="text-body-sm text-on-surface-variant">{description}</span>
          )}
        </span>
      </label>
    );
  }
);
Radio.displayName = "Radio";

export interface RadioGroupProps {
  legend: string;
  children: React.ReactNode;
  /** Error message announced for the whole group. */
  error?: string;
  className?: string;
}

/** fieldset + legend wrapper so a set of radios is announced as one control. */
export function RadioGroup({ legend, children, error, className }: RadioGroupProps) {
  return (
    <fieldset
      className={cn("flex flex-col gap-space-4 border-0 p-0", className)}
      aria-invalid={error ? true : undefined}
    >
      <legend className="font-label-caps text-label-caps uppercase text-primary-container">
        {legend}
      </legend>
      <div className="flex flex-col">{children}</div>
      {error && <span className="text-body-sm font-bold text-status-danger">{error}</span>}
    </fieldset>
  );
}
