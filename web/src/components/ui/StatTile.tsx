import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Icon } from "./Icon";

export interface StatTileProps {
  /** Label-caps eyebrow, e.g. "STOCK TURNOVER". */
  label: string;
  value: ReactNode;
  /** Small mono suffix shown after the value, e.g. "%", "ms". */
  unit?: string;
  /** Optional trailing change chip: "+12%", "▼ 4". */
  delta?: { label: string; direction: "up" | "down" | "flat" };
  icon?: string;
  /** Footer line under a hairline, e.g. "LAST UPDATED 09:41". */
  meta?: ReactNode;
  accent?: "top" | "left" | "none";
  tone?: "primary" | "success" | "warning" | "danger";
  className?: string;
}

const accentTone: Record<NonNullable<StatTileProps["tone"]>, string> = {
  primary: "bg-primary-container",
  success: "bg-status-success",
  warning: "bg-status-warning",
  danger: "bg-status-danger",
};

const deltaTone = {
  up: "text-status-success",
  down: "text-status-danger",
  flat: "text-on-surface-variant",
} as const;

/**
 * KPI tile — mono figure over label-caps caption, hard frame, optional
 * 4px structural accent bar.
 */
export function StatTile({
  label,
  value,
  unit,
  delta,
  icon,
  meta,
  accent = "none",
  tone = "primary",
  className,
}: StatTileProps) {
  return (
    <div
      className={cn(
        "flex flex-col rounded border border-frame bg-surface-container-lowest shadow-md",
        className
      )}
    >
      {accent === "top" && <div className={cn("h-1", accentTone[tone])} aria-hidden="true" />}
      <div className={cn("flex flex-1 flex-col gap-space-4", accent === "left" ? "flex-row" : "")}>
        {accent === "left" && (
          <div className={cn("w-1 shrink-0 self-stretch", accentTone[tone])} aria-hidden="true" />
        )}
        <div className="flex flex-1 flex-col gap-space-4 p-space-16">
          <div className="flex items-center justify-between gap-space-8">
            <span className="font-label-caps text-label-caps uppercase text-on-surface-variant">
              {label}
            </span>
            {icon && <Icon name={icon} size={18} className="text-outline" />}
          </div>
          <div className="flex items-baseline gap-space-4">
            <span className="font-mono text-mono-xl text-primary-container">{value}</span>
            {unit && <span className="font-mono text-mono-md text-on-surface-variant">{unit}</span>}
            {delta && (
              <span
                className={cn(
                  "ml-auto font-mono text-mono-sm font-bold",
                  deltaTone[delta.direction]
                )}
              >
                {delta.label}
              </span>
            )}
          </div>
          {meta && (
            <div className="mt-auto border-t border-frame pt-space-4 font-mono text-mono-sm uppercase text-on-surface-variant">
              {meta}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
