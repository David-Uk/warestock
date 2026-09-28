import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { cn } from "../../lib/utils";

export interface NavItem {
  label: string;
  /** Material Symbols name. */
  icon: string;
  href: string;
  /** Exact-match route (for index routes). */
  end?: boolean;
  /** Small trailing count/pill, e.g. open alerts. */
  badge?: ReactNode;
}

export interface NavGroup {
  /** label-caps group heading; omit for an ungrouped list. */
  label?: string;
  items: NavItem[];
}

export interface AppShellProps {
  /** Wordmark / mark block pinned to the top of the sidebar. */
  brand?: ReactNode;
  /** Slot to the right of the mobile title in the top bar (search, scanner…). */
  topbarActions?: ReactNode;
  /** Sidebar navigation (grouped, label-caps headings). */
  nav: NavGroup[];
  /** Pinned block at the bottom of the sidebar (system status, version). */
  sidebarFooter?: ReactNode;
  /** Up to five items for the mobile bottom tab bar. */
  mobileNav?: NavItem[];
  user?: { name?: string; subtitle?: string; initials?: string };
  onSignOut?: () => void;
  children: ReactNode;
}

function NavItems({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  return (
    <ul className="flex flex-col">
      {items.map((item) => (
        <li key={item.href}>
          <NavLink
            to={item.href}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex min-h-touch-target-min items-center gap-space-12 border-l-4 px-space-16 py-space-8 text-body-md transition-colors",
                isActive
                  ? "border-secondary-container bg-primary-container font-semibold text-white"
                  : "border-transparent text-on-surface hover:bg-surface-container"
              )
            }
          >
            <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
              {item.icon}
            </span>
            <span className="truncate">{item.label}</span>
            {item.badge && <span className="ml-auto">{item.badge}</span>}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

/**
 * Application chrome: sidebar (desktop), top bar and bottom tab bar
 * (mobile) with safe-area insets — mirrors the Stitch "Modern V2"
 * platform console shell.
 */
export function AppShell({
  brand,
  topbarActions,
  nav,
  sidebarFooter,
  mobileNav,
  user,
  onSignOut,
  children,
}: AppShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  return (
    <div className="flex min-h-screen bg-surface-dim">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-frame bg-surface-container-lowest lg:flex">
        <div className="bg-primary-container px-space-16 py-space-20 text-white">{brand}</div>
        <nav aria-label="Primary" className="flex-1 overflow-y-auto py-space-12">
          {nav.map((group, index) => (
            <div key={group.label ?? index} className="mb-space-16">
              {group.label && (
                <p className="px-space-16 pb-space-4 font-label-caps text-label-caps uppercase text-on-surface-variant">
                  {group.label}
                </p>
              )}
              <NavItems items={group.items} />
            </div>
          ))}
        </nav>
        {sidebarFooter && (
          <div className="border-t border-frame bg-surface-container-low p-space-12 text-body-sm">
            {sidebarFooter}
          </div>
        )}
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setDrawerOpen(false);
          }}
        >
          <div className="absolute inset-0 bg-black/50" />
          <nav
            aria-label="Primary"
            className="absolute inset-y-0 left-0 flex w-72 flex-col overflow-y-auto border-r border-frame bg-surface-container-lowest"
          >
            <div className="flex items-center justify-between bg-primary-container px-space-16 py-space-12 text-white">
              {brand}
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close navigation"
                className="-m-space-4 flex size-touch-target-min items-center justify-center rounded text-white/80 hover:bg-white/10"
              >
                <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                  close
                </span>
              </button>
            </div>
            <div className="flex-1 py-space-12">
              {nav.map((group, index) => (
                <div key={group.label ?? index} className="mb-space-16">
                  {group.label && (
                    <p className="px-space-16 pb-space-4 font-label-caps text-label-caps uppercase text-on-surface-variant">
                      {group.label}
                    </p>
                  )}
                  <NavItems items={group.items} onNavigate={() => setDrawerOpen(false)} />
                </div>
              ))}
            </div>
          </nav>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-40 flex min-h-touch-target-min items-center gap-space-8 border-b border-frame bg-surface-container-lowest px-space-12 py-space-4">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open navigation"
            className="flex size-touch-target-min shrink-0 items-center justify-center rounded text-primary-container hover:bg-surface-container lg:hidden"
          >
            <span className="material-symbols-outlined text-[24px]" aria-hidden="true">
              menu
            </span>
          </button>

          <div className="flex min-w-0 flex-1 items-center gap-space-12">{topbarActions}</div>

          {user && (
            <div className="flex items-center gap-space-8">
              <div className="hidden text-right sm:block">
                <p className="text-body-sm font-semibold text-on-surface">{user.name}</p>
                {user.subtitle && (
                  <p className="font-mono text-mono-sm uppercase text-on-surface-variant">
                    {user.subtitle}
                  </p>
                )}
              </div>
              <span
                aria-hidden="true"
                className="flex size-touch-target-dense items-center justify-center rounded-full bg-primary-container font-mono text-mono-sm font-bold text-white"
              >
                {user.initials ?? "?"}
              </span>
              {onSignOut && (
                <button
                  type="button"
                  onClick={onSignOut}
                  className="flex size-touch-target-min items-center justify-center rounded text-on-surface-variant hover:bg-surface-container"
                  aria-label="Sign out"
                >
                  <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                    logout
                  </span>
                </button>
              )}
            </div>
          )}
        </header>

        <main className="flex-1 pb-[calc(64px+env(safe-area-inset-bottom))] lg:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile bottom tab bar */}
      {mobileNav && mobileNav.length > 0 && (
        <nav
          aria-label="Sections"
          className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-frame bg-surface-container-lowest pb-[env(safe-area-inset-bottom)] lg:hidden"
        >
          {mobileNav.slice(0, 5).map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex min-h-16 flex-col items-center justify-center gap-space-2 py-space-8 text-label-caps uppercase",
                  isActive ? "text-primary-container" : "text-on-surface-variant"
                )
              }
            >
              <span className="material-symbols-outlined text-[22px]" aria-hidden="true">
                {item.icon}
              </span>
              <span className="truncate px-space-4">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
