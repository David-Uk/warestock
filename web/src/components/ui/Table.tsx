import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** Cell renderer; falls back to `accessor`, then `(row as any)[key]`. */
  render?: (row: T) => ReactNode;
  accessor?: keyof T | ((row: T) => ReactNode);
  align?: "left" | "center" | "right";
  /** Right-aligned JetBrains Mono numerics (manifest style). */
  mono?: boolean;
  width?: string;
  sortable?: boolean;
  /** Hide the column below this breakpoint. */
  hideBelow?: "sm" | "md" | "lg";
}

export interface SortState {
  key: string;
  dir: "asc" | "desc";
}

export interface TableProps<T> {
  columns: Array<Column<T>>;
  rows: T[];
  getRowId: (row: T, index: number) => string;
  /** Visible table caption (screen-reader accessible). */
  caption?: string;
  loading?: boolean;
  skeletonRows?: number;
  /** Rendered in place of rows when not loading and rows is empty. */
  emptyState?: ReactNode;
  sort?: SortState | null;
  onSort?: (next: SortState) => void;
  /** Navy header (default) vs light header. */
  headerVariant?: "dark" | "light";
  stickyHeader?: boolean;
  rowClassName?: (row: T) => string;
  onRowClick?: (row: T) => void;
  className?: string;
}

const hideClasses: Record<NonNullable<Column<never>["hideBelow"]>, string> = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
};

function cellContent<T>(column: Column<T>, row: T): ReactNode {
  if (column.render) return column.render(row);
  if (typeof column.accessor === "function") return column.accessor(row);
  if (column.accessor !== undefined) return row[column.accessor] as ReactNode;
  return (row as Record<string, unknown>)[column.key] as ReactNode;
}

/**
 * Manifest data table: navy header row, hairline grid, alternating
 * rows, mono right-aligned numerics, sortable headers with aria-sort.
 */
export function Table<T>({
  columns,
  rows,
  getRowId,
  caption,
  loading = false,
  skeletonRows = 5,
  emptyState,
  sort = null,
  onSort,
  headerVariant = "dark",
  stickyHeader = false,
  rowClassName,
  onRowClick,
  className,
}: TableProps<T>) {
  const showBody = !loading && rows.length > 0;
  const showEmpty = !loading && rows.length === 0;

  return (
    <div className={cn("w-full overflow-x-auto rounded border border-frame", className)}>
      <table className="w-full border-collapse text-left">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead
          className={cn(
            headerVariant === "dark"
              ? "bg-primary-container text-white"
              : "bg-surface-container-high text-primary-container",
            stickyHeader && "sticky top-0 z-10"
          )}
        >
          <tr>
            {columns.map((column) => {
              const active = sort?.key === column.key;
              const ariaSort = active
                ? sort.dir === "asc"
                  ? "ascending"
                  : "descending"
                : undefined;

              return (
                <th
                  key={column.key}
                  scope="col"
                  style={column.width ? { width: column.width } : undefined}
                  aria-sort={column.sortable ? ariaSort : undefined}
                  className={cn(
                    "border-b border-black/20 px-space-16 py-space-12 font-label-caps text-label-caps uppercase",
                    column.align === "right" && "text-right",
                    column.align === "center" && "text-center",
                    column.hideBelow && hideClasses[column.hideBelow]
                  )}
                >
                  {column.sortable && onSort ? (
                    <button
                      type="button"
                      onClick={() =>
                        onSort({
                          key: column.key,
                          dir: active && sort.dir === "asc" ? "desc" : "asc",
                        })
                      }
                      className={cn(
                        "inline-flex items-center gap-space-4 hover:underline",
                        column.align === "right" && "flex-row-reverse"
                      )}
                    >
                      {column.header}
                      <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                        {active
                          ? sort.dir === "asc"
                            ? "arrow_upward"
                            : "arrow_downward"
                          : "unfold_more"}
                      </span>
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody>
          {loading &&
            Array.from({ length: skeletonRows }, (_, rowIndex) => (
              <tr key={`skeleton-${rowIndex}`} className="border-b border-frame">
                {columns.map((column) => (
                  <td key={column.key} className="px-space-16 py-space-12">
                    <Skeleton height={16} />
                  </td>
                ))}
              </tr>
            ))}

          {showBody &&
            rows.map((row, index) => (
              <tr
                key={getRowId(row, index)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  "border-b border-frame last:border-b-0",
                  index % 2 === 1 && "bg-surface-container-low",
                  onRowClick && "cursor-pointer hover:bg-primary-fixed/30",
                  rowClassName?.(row)
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      "px-space-16 py-space-12 text-body-md text-on-surface",
                      column.align === "right" && "text-right",
                      column.align === "center" && "text-center",
                      column.mono && "font-mono text-mono-md [font-variant-numeric:tabular-nums]",
                      column.hideBelow && hideClasses[column.hideBelow]
                    )}
                  >
                    {cellContent(column, row)}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>

      {showEmpty && (
        <div className="p-space-16">
          {emptyState ?? (
            <EmptyState icon="inbox" heading="No records" description="Nothing to show here yet." />
          )}
        </div>
      )}
    </div>
  );
}
