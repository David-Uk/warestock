import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Icon } from "./Icon";

export type BannerTone = "info" | "success" | "warning" | "critical";

export interface AlertBannerProps {
  tone?: BannerTone;
  /** Label-caps eyebrow, e.g. "DISCREPANCY". */
  title: string;
  children?: ReactNode;
  /** Trailing action (link or button). */
  action?: ReactNode;
  /** Dismiss button handler; renders an X when provided. */
  onDismiss?: () => void;
  className?: string;
}

const toneClasses: Record<BannerTone, string> = {
  info: "border-l-primary-container bg-surface-container-low text-on-surface",
  success: "border-l-status-success bg-status-success-bg text-on-surface",
  warning: "border-l-status-warning bg-status-warning-bg text-on-surface",
  critical: "border-l-status-danger bg-status-danger-bg text-on-surface",
};

const toneIcon: Record<BannerTone, string> = {
  info: "info",
  success: "task_alt",
  warning: "warning",
  critical: "error",
};

const iconColor: Record<BannerTone, string> = {
  info: "text-primary-container",
  success: "text-status-success",
  warning: "text-status-warning-ink",
  critical: "text-status-danger",
};

/**
 * Article-style alert with the 4px left status strip — the "alert
 * manager row" language from the Stitch dashboard screens.
 */
export function AlertBanner({
  tone = "info",
  title,
  children,
  action,
  onDismiss,
  className,
}: AlertBannerProps) {
  return (
    <div
      role={tone === "critical" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-space-12 rounded border border-l-4 border-frame p-space-16",
        toneClasses[tone],
        className
      )}
    >
      <Icon
        name={toneIcon[tone]}
        size={20}
        className={cn("mt-space-2 shrink-0", iconColor[tone])}
      />
      <div className="flex min-w-0 flex-1 flex-col gap-space-4">
        <p className="font-label-caps text-label-caps uppercase">{title}</p>
        {children && <div className="text-body-md">{children}</div>}
        {action && <div className="mt-space-4 flex flex-wrap gap-space-8">{action}</div>}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss message"
          className="-m-space-4 flex size-touch-target-dense shrink-0 items-center justify-center rounded text-on-surface-variant hover:bg-black/5"
        >
          <Icon name="close" size={20} />
        </button>
      )}
    </div>
  );
}
