import { useNavigate } from "react-router-dom";
import { AppShell, PageHeader, type NavGroup } from "../../components/layout";
import { Badge, Button, Card, StatTile } from "../../components/ui";

const nav: NavGroup[] = [
  {
    label: "Operations",
    items: [
      { label: "Overview", icon: "space_dashboard", href: "/design/shell" },
      {
        label: "Alerts",
        icon: "notifications",
        href: "/design",
        badge: (
          <Badge tone="danger" size="tag">
            12
          </Badge>
        ),
      },
      { label: "Manifest", icon: "table_view", href: "/design#table" },
    ],
  },
  {
    label: "Administration",
    items: [
      { label: "Component gallery", icon: "widgets", href: "/design" },
      { label: "Sign in", icon: "login", href: "/auth/login" },
    ],
  },
];

const mobileNav = [
  { label: "Overview", icon: "space_dashboard", href: "/design/shell" },
  { label: "Gallery", icon: "widgets", href: "/design" },
  { label: "Alerts", icon: "notifications", href: "/design?view=alerts" },
  { label: "Sign in", icon: "login", href: "/auth/login" },
];

/** Live preview of the shared app chrome (sidebar + top bar + tab bar). */
export default function ShellDemo() {
  const navigate = useNavigate();

  return (
    <AppShell
      brand={
        <div className="flex flex-col">
          <span className="font-label-caps text-label-caps uppercase tracking-widest">
            Warestock
          </span>
          <span className="font-mono text-mono-sm text-white/60">AI OPS CONSOLE</span>
        </div>
      }
      nav={nav}
      mobileNav={mobileNav}
      sidebarFooter={
        <div className="flex items-center justify-between gap-space-8">
          <Badge tone="live" size="tag" icon="sensors">
            System online
          </Badge>
          <span className="font-mono text-mono-sm text-on-surface-variant">v0.1.0</span>
        </div>
      }
      topbarActions={
        <div className="flex items-center gap-space-8">
          <Badge tone="neutral" icon={false}>
            North Hub — Zone A
          </Badge>
          <Button size="sm" variant="ghost" icon="arrow_back" onClick={() => navigate("/design")}>
            Back to gallery
          </Button>
        </div>
      }
      user={{ name: "Dana Whitfield", subtitle: "Warehouse Manager", initials: "DW" }}
      onSignOut={() => navigate("/auth/login")}
    >
      <div className="flex flex-col gap-space-16 p-space-16 md:p-space-24">
        <PageHeader
          title="Shell preview"
          eyebrow="OPERATIONS › OVERVIEW"
          description="Sidebar, top bar and mobile tab bar from AppShell — resize the viewport to see the responsive states."
          chips={<Badge tone="live">Live</Badge>}
        />
        <div className="grid gap-space-16 md:grid-cols-3">
          <StatTile label="On hand units" value="12,480" accent="top" meta="Zone A" />
          <StatTile
            label="Open alerts"
            value="12"
            accent="left"
            tone="danger"
            meta="8 unresolved"
          />
          <StatTile
            label="Fill rate"
            value="96"
            unit="%"
            accent="top"
            tone="success"
            meta="This shift"
          />
        </div>
        <Card title="Note" icon="info">
          <p className="text-body-md text-on-surface-variant">
            Nav links point back to the gallery so you can move between the two previews.
          </p>
        </Card>
      </div>
    </AppShell>
  );
}
