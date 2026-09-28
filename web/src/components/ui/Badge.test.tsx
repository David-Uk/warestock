import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";
import { RoleBadge } from "./RoleBadge";

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge tone="success">Reconciled</Badge>);
    expect(screen.getByText("Reconciled")).toBeInTheDocument();
  });

  it("applies tone-specific colours", () => {
    const { rerender } = render(<Badge tone="danger">Variance</Badge>);
    expect(screen.getByText("Variance").className).toContain("bg-status-danger-bg");

    rerender(<Badge tone="warning">Low stock</Badge>);
    expect(screen.getByText("Low stock").className).toContain("bg-status-warning-bg");
  });

  it("shows a default icon per tone and hides it when icon={false}", () => {
    const { rerender } = render(<Badge tone="success">OK</Badge>);
    expect(screen.getByText("check_circle")).toBeInTheDocument();

    rerender(
      <Badge tone="success" icon={false}>
        OK
      </Badge>
    );
    expect(screen.queryByText("check_circle")).not.toBeInTheDocument();
  });
});

describe("RoleBadge", () => {
  it("renders a human-readable label for a known role", () => {
    render(<RoleBadge role="superadmin" />);
    expect(screen.getByText("Superadmin")).toBeInTheDocument();
  });

  it("applies tier colours", () => {
    const { rerender } = render(<RoleBadge role="superadmin" />);
    expect(screen.getByText("Superadmin").className).toContain("bg-tier-platform-bg");

    rerender(<RoleBadge role="org_admin" />);
    expect(screen.getByText("Org Admin").className).toContain("bg-tier-org-bg");

    rerender(<RoleBadge role="warehouse_manager" />);
    expect(screen.getByText("Warehouse Manager").className).toContain("bg-tier-warehouse-bg");
  });

  it("falls back to a neutral chip for unknown roles", () => {
    render(<RoleBadge role="some_future_role" />);
    expect(screen.getByText("some_future_role")).toBeInTheDocument();
  });
});
