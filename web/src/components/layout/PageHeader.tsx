import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/utils";

export interface Crumb {
  label: string;
  /** Omit on the current (last) crumb. */
  href?: string;
}

export interface PageHeaderProps {
  title: string;
  /** Mono eyebrow above the title, e.g. "REPLENISHMENT › ZONE A". */
  eyebrow?: string;
  description?: string;
  breadcrumbs?: Crumb[];
  /** Status chips rendered under the title. */
  chips?: ReactNode;
  /** Buttons aligned to the right (wraps below on narrow screens). */
  actions?: ReactNode;
  className?: string;
}

/** Breadcrumb + headline + chips + actions block at the top of a page. */
export function PageHeader({
  title,
  eyebrow,
  description,
  breadcrumbs,
  chips,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-space-12", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-space-4 font-mono text-mono-sm uppercase text-on-surface-variant">
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;
              return (
                <li key={`${crumb.label}-${index}`} className="flex items-center gap-space-4">
                  {crumb.href && !isLast ? (
                    <Link to={crumb.href} className="hover:text-primary-container hover:underline">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span aria-current={isLast ? "page" : undefined} className="text-on-surface">
                      {crumb.label}
                    </span>
                  )}
                  {!isLast && <span aria-hidden="true">›</span>}
                </li>
              );
            })}
          </ol>
        </nav>
      )}

      <div className="flex flex-col gap-space-8 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          {eyebrow && (
            <p className="font-mono text-mono-sm uppercase text-on-surface-variant">{eyebrow}</p>
          )}
          <h1 className="font-headline-lg text-headline-lg-mobile text-primary-container md:text-headline-lg">
            {title}
          </h1>
          {description && (
            <p className="mt-space-4 text-body-md text-on-surface-variant">{description}</p>
          )}
          {chips && (
            <div className="mt-space-8 flex flex-wrap items-center gap-space-8">{chips}</div>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-space-8">{actions}</div>
        )}
      </div>
    </div>
  );
}
