import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * Custom `--text-*` scale from index.css. tailwind-merge only knows the
 * default `text-{t-shirt-size}` classes, so without these entries it treats
 * e.g. `text-body-lg` as a *text color* and strips a preceding `text-white`.
 */
const textScale = [
  "headline-xl",
  "headline-xl-mobile",
  "headline-lg",
  "headline-lg-mobile",
  "headline-md",
  "body-lg",
  "body-md",
  "body-sm",
  "mono-xl",
  "mono-lg",
  "mono-md",
  "mono-sm",
  "label-caps",
] as const;

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": textScale.map((size) => `text-${size}`),
    },
  },
});

/**
 * Merge conditional class names with Tailwind conflict resolution.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a quantity with thousands separators: 12480 -> "12,480" */
export function formatQty(value: number): string {
  return new Intl.NumberFormat("en-GB").format(value);
}

/** Format a ratio as a whole percentage: 0.826 -> "83%" */
export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

/** Format an ISO date for UI display: "2026-09-28" -> "28 Sep 2026" */
export function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function capitalize(value: string): string {
  return value.length === 0 ? value : value[0].toUpperCase() + value.slice(1);
}

export function truncate(value: string, maxLength: number): string {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`;
}
