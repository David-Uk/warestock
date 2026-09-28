import { cn } from "../../lib/utils";

export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const sizes: Record<NonNullable<SpinnerProps["size"]>, string> = {
  sm: "size-4 border-2",
  md: "size-8 border-[3px]",
  lg: "size-12 border-4",
};

/**
 * Indeterminate activity indicator. Announced via role="status" so screen
 * readers hear the label while it spins.
 */
export function Spinner({ size = "md", label = "Loading", className }: SpinnerProps) {
  return (
    <span role="status" aria-label={label} className={cn("inline-flex", className)}>
      <span
        className={cn(
          "animate-spin rounded-full border-on-surface/20 border-t-primary-container",
          sizes[size]
        )}
      />
      <span className="sr-only">{label}</span>
    </span>
  );
}
