import { cn, formatQty } from "../../lib/utils";

export interface PaginationProps {
  /** 1-based current page. */
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  /** Total item count for the "1–20 of 1,240" readout. */
  total?: number;
  pageSize?: number;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  /** Override the default range readout. */
  rangeLabel?: string;
  className?: string;
}

/** Build a windowed page list with "…" gaps: 1 … 4 5 [6] 7 8 … 20 */
function getPageItems(page: number, pageCount: number): Array<number | "gap"> {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);

  const items: Array<number | "gap"> = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(pageCount - 1, page + 1);

  if (start > 2) items.push("gap");
  for (let p = start; p <= end; p += 1) items.push(p);
  if (end < pageCount - 1) items.push("gap");
  items.push(pageCount);
  return items;
}

/**
 * Pagination footbar: mono range readout, optional items-per-page
 * select, prev/next and numbered page buttons.
 */
export function Pagination({
  page,
  pageCount,
  onPageChange,
  total,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [20, 50, 100],
  rangeLabel,
  className,
}: PaginationProps) {
  const safePageCount = Math.max(1, pageCount);
  const safePage = Math.min(Math.max(1, page), safePageCount);
  const from = pageSize ? (safePage - 1) * pageSize + 1 : undefined;
  const to = pageSize && total !== undefined ? Math.min(safePage * pageSize, total) : undefined;

  const label =
    rangeLabel ??
    (total !== undefined && from !== undefined && to !== undefined
      ? `${formatQty(from)}–${formatQty(to)} of ${formatQty(total)}`
      : `Page ${safePage} of ${safePageCount}`);

  const go = (next: number) => {
    const clamped = Math.min(Math.max(1, next), safePageCount);
    if (clamped !== safePage) onPageChange(clamped);
  };

  return (
    <nav
      aria-label="Pagination"
      className={cn(
        "flex flex-col items-stretch justify-between gap-space-12 border-t border-frame bg-surface-container-low px-space-16 py-space-12 sm:flex-row sm:items-center",
        className
      )}
    >
      <div className="flex items-center gap-space-12">
        <span className="font-mono text-mono-sm uppercase text-on-surface-variant">{label}</span>
        {onPageSizeChange && (
          <label className="flex items-center gap-space-4 font-mono text-mono-sm uppercase text-on-surface-variant">
            <span className="sr-only sm:not-sr-only">Rows</span>
            <select
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="rounded-xs border border-frame bg-white px-space-4 py-space-2 font-mono text-mono-sm text-primary-container"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="flex items-center gap-space-4">
        <button
          type="button"
          onClick={() => go(safePage - 1)}
          disabled={safePage <= 1}
          aria-label="Previous page"
          className="flex size-touch-target-dense items-center justify-center rounded-xs border border-frame bg-white text-primary-container disabled:opacity-40"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
            chevron_left
          </span>
        </button>

        {getPageItems(safePage, safePageCount).map((item, index) =>
          item === "gap" ? (
            <span
              key={`gap-${index}`}
              aria-hidden="true"
              className="px-space-4 font-mono text-mono-sm text-on-surface-variant"
            >
              …
            </span>
          ) : (
            <button
              key={item}
              type="button"
              onClick={() => go(item)}
              aria-label={`Page ${item}`}
              aria-current={item === safePage ? "page" : undefined}
              className={cn(
                "flex size-touch-target-dense items-center justify-center rounded-xs border font-mono text-mono-md",
                item === safePage
                  ? "border-primary-container bg-secondary-container text-on-secondary-container"
                  : "border-frame bg-white text-primary-container hover:bg-surface-container"
              )}
            >
              {item}
            </button>
          )
        )}

        <button
          type="button"
          onClick={() => go(safePage + 1)}
          disabled={safePage >= safePageCount}
          aria-label="Next page"
          className="flex size-touch-target-dense items-center justify-center rounded-xs border border-frame bg-white text-primary-container disabled:opacity-40"
        >
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">
            chevron_right
          </span>
        </button>
      </div>
    </nav>
  );
}
