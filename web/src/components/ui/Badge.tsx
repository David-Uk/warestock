import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

export type BadgeTone = "success" | "warning" | "danger" | "info" | "neutral" | "live";

export interface BadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
  /** Material Symbol name; `false` hides the icon entirely. */
  icon?: string | false;
  /** Micro tag (2px radius, 11px) vs status chip (4px, 12px + icon). */
  size?: "tag" | "chip";
  className?: string;
  title?: string;
}

const defaultIcon: Record<BadgeTone, string | false> = {
  success: "check_circle",
  warning: "warning",
  danger: "error",
  info: "info",
  neutral: false,
  live: "sensors",
};

const toneClasses: Record<BadgeTone, string> = {
  success: "bg-status-success-bg text-status-success border-status-success",
  warning: "bg-status-warning-bg text-status-warning-ink border-status-warning",
  danger: "bg-status-danger-bg text-status-danger border-status-danger",
  info: "bg-primary-fixed/40 text-primary-container border-primary-fixed-dim",
  neutral: "bg-surface-container text-on-surface-variant border-outline-variant",
  live: "bg-tertiary-fixed/40 text-on-tertiary-fixed-variant border-tertiary-fixed-dim",
};

/**
 * Status chip / micro tag. Mono, uppercase, hard 1px border — the
 * "no soft pills" rule from DESIGN.md §3.
 */
export function Badge({
  tone = "neutral",
  children,
  icon,
  size = "chip",
  className,
  title,
}: BadgeProps) {
  const glyph = icon === undefined ? defaultIcon[tone] : icon;

  return (
    <span
      title={title}
      className={cn(
        "inline-flex w-fit items-center gap-space-4 whitespace-nowrap border font-mono font-bold uppercase",
        toneClasses[tone],
        size === "chip"
          ? "rounded px-space-8 py-space-2 text-mono-sm"
          : "rounded-xs px-space-4 py-space-2 text-label-caps",
        className
      )}
    >
      {glyph && (
        <span className="material-symbols-outlined text-[14px] leading-none" aria-hidden="true">
          {glyph}
        </span>
      )}
      {children}
    </span>
  );
}
