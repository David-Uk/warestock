import { cn } from "../../lib/utils";

export interface SkeletonProps {
  className?: string;
  /** Fixed pixel width; omit to fill the parent. */
  width?: number;
  /** Fixed pixel height; defaults to one body line. */
  height?: number;
  /** Circular (avatar) instead of rectangular. */
  rounded?: boolean;
}

/** Shimmer placeholder for content that is still loading. */
export function Skeleton({ className, width, height = 16, rounded }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "block animate-pulse bg-surface-container-highest",
        rounded ? "rounded-full" : "rounded-xs",
        className
      )}
      style={{ width: width ?? "100%", height }}
    />
  );
}

/** Convenience block of stacked skeleton lines (e.g. table body while loading). */
export function SkeletonRows({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-3 p-4", className)} aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={20} width={i % 3 === 0 ? 60 : undefined} />
      ))}
    </div>
  );
}
