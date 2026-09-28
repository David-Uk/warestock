import { describe, expect, it, vi } from "vitest";
import type { ReactElement } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AppShell, type NavGroup } from "./AppShell";
import { PageHeader } from "./PageHeader";

const nav: NavGroup[] = [
  {
    label: "Operations",
    items: [
      { label: "Overview", icon: "space_dashboard", href: "/shell" },
      { label: "Alerts", icon: "notifications", href: "/alerts" },
    ],
  },
  {
    label: "Administration",
    items: [{ label: "Sign in", icon: "login", href: "/auth/login" }],
  },
];

function renderShell(ui: ReactElement, route = "/shell") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppShell
        brand={<span>WARESTOCK</span>}
        nav={nav}
        mobileNav={[nav[0].items[0], nav[1].items[0]]}
        user={{ name: "Dana Whitfield", subtitle: "Warehouse Manager", initials: "DW" }}
        onSignOut={vi.fn()}
      >
        {ui}
      </AppShell>
    </MemoryRouter>
  );
}

describe("AppShell", () => {
  it("renders brand, grouped navigation and page content", () => {
    renderShell(<p>Page body</p>);

    expect(screen.getByText("WARESTOCK")).toBeInTheDocument();
    expect(screen.getByText("Operations")).toBeInTheDocument();
    expect(screen.getByText("Administration")).toBeInTheDocument();
    expect(screen.getByText("Page body")).toBeInTheDocument();

    // Sidebar + mobile tab bar both render the links
    expect(screen.getAllByRole("link", { name: /Overview/ }).length).toBeGreaterThan(0);
  });

  it("marks the active route with aria-current", () => {
    renderShell(<p>Body</p>, "/shell");
    const active = screen.getAllByRole("link", { name: /Overview/ });
    for (const link of active) {
      expect(link).toHaveAttribute("aria-current", "page");
    }
  });

  it("opens and closes the mobile navigation drawer", async () => {
    renderShell(<p>Body</p>, "/shell");

    await userEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    // Desktop sidebar and drawer both expose the same links
    expect(screen.getAllByRole("navigation", { name: "Primary" }).length).toBe(2);

    await userEvent.click(screen.getByRole("button", { name: "Close navigation" }));
    expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1);
  });

  it("shows user identity and fires sign out", async () => {
    const onSignOut = vi.fn();
    render(
      <MemoryRouter initialEntries={["/shell"]}>
        <AppShell
          nav={nav}
          user={{ name: "Dana Whitfield", subtitle: "Warehouse Manager", initials: "DW" }}
          onSignOut={onSignOut}
        >
          <p>Body</p>
        </AppShell>
      </MemoryRouter>
    );

    expect(screen.getByText("Dana Whitfield")).toBeInTheDocument();
    expect(screen.getByText("DW")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(onSignOut).toHaveBeenCalledTimes(1);
  });
});

describe("PageHeader", () => {
  it("renders the title, eyebrow and description", () => {
    render(
      <MemoryRouter>
        <PageHeader
          title="Stock discrepancies"
          eyebrow="ZONE A"
          description="Resolve variances before handover."
        />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: "Stock discrepancies" })).toBeInTheDocument();
    expect(screen.getByText("ZONE A")).toBeInTheDocument();
    expect(screen.getByText("Resolve variances before handover.")).toBeInTheDocument();
  });

  it("renders breadcrumbs with the current page marked", () => {
    render(
      <MemoryRouter>
        <PageHeader
          title="Bay 12"
          breadcrumbs={[
            { label: "Operations", href: "/" },
            { label: "Zone A", href: "/zone-a" },
            { label: "Bay 12" },
          ]}
        />
      </MemoryRouter>
    );

    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(nav).toBeInTheDocument();
    expect(within(nav).getByText("Bay 12")).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Zone A" })).toBeInTheDocument();
  });

  it("renders chips and actions", () => {
    render(
      <MemoryRouter>
        <PageHeader
          title="Alerts"
          chips={<span>12 open</span>}
          actions={<button type="button">Acknowledge</button>}
        />
      </MemoryRouter>
    );

    expect(screen.getByText("12 open")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acknowledge" })).toBeInTheDocument();
  });
});
