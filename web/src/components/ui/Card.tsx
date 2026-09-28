import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Icon } from "./Icon";

export interface CardProps {
  /** Navy label-caps header (Stitch "section card" treatment). */
  title?: ReactNode;
  subtitle?: string;
  icon?: string;
  /** Status pill or actions pinned to the right of the header. */
  headerAction?: ReactNode;
  /** Buttons rendered under a hairline at the bottom of the card. */
  footer?: ReactNode;
  /** Structural accent strip. */
  accent?: "none" | "top" | "left";
  tone?: "primary" | "success" | "warning" | "danger";
  /** Remove body padding (for tables / media flush to the frame). */
  flush?: boolean;
  className?: string;
  children?: ReactNode;
}

const accentTone: Record<NonNullable<CardProps["tone"]>, string> = {
  primary: "bg-primary-container",
  success: "bg-status-success",
  warning: "bg-status-warning",
  danger: "bg-status-danger",
};

/**
 * Section card: hard 1px frame, 4px radius, optional navy header bar
 * and structural accent strip.
 */
export function Card({
  title,
  subtitle,
  icon,
  headerAction,
  footer,
  accent = "none",
  tone = "primary",
  flush = false,
  className,
  children,
}: CardProps) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded border border-frame bg-surface-container-lowest shadow-md",
        className
      )}
    >
      {accent === "top" && <div className={cn("h-1", accentTone[tone])} aria-hidden="true" />}
      <div className="flex">
        {accent === "left" && (
          <div className={cn("w-1 shrink-0", accentTone[tone])} aria-hidden="true" />
        )}
        <div className="min-w-0 flex-1">
          {title && (
            <header className="flex items-center justify-between gap-space-12 bg-primary-container px-space-16 py-space-12">
              <div className="flex min-w-0 items-center gap-space-8 text-white">
                {icon && <Icon name={icon} size={20} />}
                <div className="min-w-0">
                  <h2 className="truncate font-label-caps text-label-caps uppercase">{title}</h2>
                  {subtitle && (
                    <p className="truncate font-mono text-mono-sm text-white/70">{subtitle}</p>
                  )}
                </div>
              </div>
              {headerAction && (
                <div className="flex shrink-0 items-center gap-space-8">{headerAction}</div>
              )}
            </header>
          )}
          <div className={cn(flush ? "" : "p-space-16", !title && flush && "pt-0")}>{children}</div>
          {footer && (
            <footer className="border-t border-frame bg-surface-container-low px-space-16 py-space-12">
              {footer}
            </footer>
          )}
        </div>
      </div>
    </section>
  );
}
