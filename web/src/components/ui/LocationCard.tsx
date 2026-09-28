import type { ReactNode } from "react";
import { cn } from "../../lib/utils";
import { Badge } from "./Badge";
import { Button } from "./Button";
import { ProgressBar } from "./ProgressBar";

export type LocationStatus = "online" | "low" | "halted";

export interface LocationCardProps {
  /** Mono coordinate, e.g. "A-04-BAY-12-LVL-2". */
  coordinate: string;
  /** Zoning description, e.g. "Racking Level 2 — Electronics". */
  zone?: string;
  description?: string;
  sku?: string;
  quantity?: number;
  /** 0–100 capacity fill. */
  capacity: number;
  status: LocationStatus;
  lastCounted?: string;
  /** Full-width footer CTA; omit for a read-only card. */
  onOpen?: () => void;
  openLabel?: string;
  /** Custom wireframe illustration shown in the body; replaces the default bay glyph. */
  wireframe?: ReactNode;
  className?: string;
}

const statusMap: Record<LocationStatus, { label: string; tone: "success" | "warning" | "danger" }> =
  {
    online: { label: "Online", tone: "success" },
    low: { label: "Low Vol", tone: "warning" },
    halted: { label: "Halted", tone: "danger" },
  };

/**
 * Bay locator card: navy mono header + status pill, wireframe body,
 * capacity meter, audit meta and full-width CTA.
 */
export function LocationCard({
  coordinate,
  zone,
  description,
  sku,
  quantity,
  capacity,
  status,
  lastCounted,
  onOpen,
  openLabel = "Open bay",
  wireframe,
  className,
}: LocationCardProps) {
  const statusMeta = statusMap[status];

  return (
    <article
      className={cn(
        "flex flex-col overflow-hidden rounded border border-frame bg-surface-container-lowest shadow-md",
        className
      )}
    >
      <header className="flex items-center justify-between gap-space-8 bg-primary-container px-space-16 py-space-12">
        <div className="flex min-w-0 items-center gap-space-8 text-white">
          <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
            view_in_ar
          </span>
          <span className="truncate font-mono text-mono-md font-bold text-white">{coordinate}</span>
        </div>
        <Badge tone={statusMeta.tone} icon={false} size="tag">
          {statusMeta.label}
        </Badge>
      </header>

      <div className="flex flex-col gap-space-12 p-space-16">
        <div className="flex items-start gap-space-12 rounded border border-frame bg-surface-container-low p-space-12">
          <div className="flex size-16 shrink-0 items-center justify-center bg-panel text-outline">
            <span className="material-symbols-outlined text-[28px]" aria-hidden="true">
              {{ online: "deployed_code", low: "motion_photos_on", halted: "gpp_bad" }[status]}
            </span>
          </div>
          <div className="min-w-0 flex-1">
            {zone && (
              <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">
                {zone}
              </p>
            )}
            {sku && <p className="font-mono text-mono-md text-primary-container">{sku}</p>}
            {description && <p className="text-body-sm text-on-surface-variant">{description}</p>}
          </div>
        </div>

        {wireframe}

        <ProgressBar
          value={capacity}
          label="Capacity"
          rightLabel={quantity !== undefined ? `${capacity}% · ${quantity}` : undefined}
          showPercent={false}
        />

        {lastCounted && (
          <p className="font-mono text-mono-sm uppercase text-on-surface-variant">
            Last counted {lastCounted}
          </p>
        )}
      </div>

      {onOpen && (
        <div className="border-t border-frame p-space-16">
          <Button variant="secondary" fullWidth onClick={onOpen}>
            {openLabel}
          </Button>
        </div>
      )}
    </article>
  );
}
