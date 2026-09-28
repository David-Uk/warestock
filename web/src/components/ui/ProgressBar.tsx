import { cn } from "../../lib/utils";

export interface ProgressBarProps {
  /** 0–100. */
  value: number;
  /** Left caption above the track (e.g. "CAPACITY"). */
  label?: string;
  /** Right caption above the track (e.g. "82%"). */
  rightLabel?: string;
  tone?: "primary" | "success" | "warning" | "danger";
  /** Show the numeric percentage inside the right label automatically. */
  showPercent?: boolean;
  size?: "sm" | "md";
  className?: string;
  /** Accessible name when no label is visible. */
  "aria-label"?: string;
}

const fillTone = {
  primary: "bg-primary-container",
  success: "bg-status-success",
  warning: "bg-status-warning",
  danger: "bg-status-danger",
} as const;

function toneForValue(value: number): keyof typeof fillTone {
  if (value >= 95) return "danger";
  if (value >= 85) return "warning";
  return "primary";
}

/** Label row + hard-edged track (no rounded pill). */
export function ProgressBar({
  value,
  label,
  rightLabel,
  tone,
  showPercent = true,
  size = "md",
  className,
  ...rest
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const resolved = tone ?? toneForValue(clamped);

  return (
    <div className={cn("flex w-full flex-col gap-space-4", className)}>
      {(label || rightLabel || showPercent) && (
        <div className="flex items-baseline justify-between gap-space-8">
          {label && (
            <span className="font-label-caps text-label-caps uppercase text-on-surface-variant">
              {label}
            </span>
          )}
          <span className="ml-auto font-mono text-mono-sm text-primary-container">
            {rightLabel ?? `${clamped}%`}
          </span>
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? rest["aria-label"]}
        className={cn("w-full overflow-hidden bg-panel", size === "sm" ? "h-2" : "h-4")}
      >
        <div
          className={cn("h-full transition-[width] duration-300", fillTone[resolved])}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
