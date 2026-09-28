import { cn } from "../../lib/utils";

export interface IconProps {
  /** Material Symbols ligature name, e.g. "warehouse", "warning". */
  name: string;
  className?: string;
  /** Render size in pixels (defaults to 24, the Material baseline). */
  size?: number;
  "aria-hidden"?: boolean;
}

/**
 * Material Symbols Outlined glyph (font is loaded in index.html).
 * Icons are decorative by default; pass a visible text label or an
 * `aria-label` on the parent interactive element when meaning is needed.
 */
export function Icon({ name, className, size = 24, ...rest }: IconProps) {
  return (
    <span
      className={cn("material-symbols-outlined select-none", className)}
      style={{ fontSize: size, width: size, height: size }}
      aria-hidden={rest["aria-hidden"] ?? true}
    >
      {name}
    </span>
  );
}
