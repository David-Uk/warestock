import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Icon } from "./Icon";

export interface EmptyStateProps {
  /** Material Symbols name, e.g. "search_off", "inventory_2". */
  icon?: string;
  heading: string;
  description?: string;
  /** Optional call to action rendered under the description. */
  action?: ReactNode;
  className?: string;
}

/**
 * "Nothing here yet" state — keeps hairline geometry: no illustration
 * cards, just icon + label-caps heading + body copy + action.
 */
export function EmptyState({ icon, heading, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-space-8 rounded border border-dashed border-frame px-space-24 py-space-48 text-center",
        className
      )}
    >
      {icon && <Icon name={icon} size={40} className="text-outline" />}
      <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">{heading}</p>
      {description && (
        <p className="max-w-md text-body-md text-on-surface-variant">{description}</p>
      )}
      {action && <div className="mt-space-4">{action}</div>}
    </div>
  );
}
