import React from "react";
import { cn } from "../../lib/utils";
import { Spinner } from "./Spinner";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "hazard"
  | "ghost"
  | "cancel"
  | "confirm"
  | "danger";

export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner, sets aria-busy and blocks clicks. */
  loading?: boolean;
  /** Leading Material Symbol rendered inside the label gap. */
  icon?: string;
  /** Stretch to container width (mobile default in Stitch layouts). */
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary-container text-white hover:bg-primary-hover active:bg-primary-active",
  confirm: "bg-primary-container text-white hover:bg-primary-hover active:bg-primary-active",
  secondary:
    "bg-white text-primary-container border-2 border-primary-container hover:bg-surface-container active:bg-panel",
  hazard: "bg-status-danger text-white hover:bg-[#DC2626] active:bg-[#B91C1C]",
  danger: "bg-status-danger text-white hover:bg-[#DC2626] active:bg-[#B91C1C]",
  cancel:
    "bg-white text-on-surface-variant border-2 border-frame hover:bg-surface-container-low active:bg-panel",
  ghost:
    "bg-transparent text-primary-container border border-frame hover:bg-surface-container active:bg-panel",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-touch-target-dense px-space-12 text-body-md",
  md: "min-h-[52px] sm:min-h-touch-target-min px-space-16 text-body-lg",
  lg: "min-h-[56px] px-space-24 text-body-lg",
};

/**
 * Primary interactive control. 48px minimum hit area (40px `sm` for
 * in-table dense actions), 4px radius, hard 2px borders.
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      fullWidth,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-space-8 rounded font-primary font-semibold",
          "transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-container",
          "disabled:pointer-events-none disabled:opacity-50",
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && "w-full",
          className
        )}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? (
          <Spinner size="sm" label="Working" />
        ) : (
          icon && (
            <span className="material-symbols-outlined text-[20px] leading-none" aria-hidden="true">
              {icon}
            </span>
          )
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
