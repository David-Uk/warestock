import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "./Card";
import { StatTile } from "./StatTile";
import { ProgressBar } from "./ProgressBar";

describe("Card", () => {
  it("renders header, body and footer slots", () => {
    render(
      <Card
        title="Capacity — Zone A"
        subtitle="4 locations"
        headerAction={<span>82% free</span>}
        footer={<span>Last updated 09:41</span>}
      >
        <p>Body copy</p>
      </Card>
    );

    expect(screen.getByRole("heading", { name: "Capacity — Zone A" })).toBeInTheDocument();
    expect(screen.getByText("4 locations")).toBeInTheDocument();
    expect(screen.getByText("82% free")).toBeInTheDocument();
    expect(screen.getByText("Body copy")).toBeInTheDocument();
    expect(screen.getByText("Last updated 09:41")).toBeInTheDocument();
  });

  it("renders without a header", () => {
    render(<Card>Plain body</Card>);
    expect(screen.getByText("Plain body")).toBeInTheDocument();
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });
});

describe("StatTile", () => {
  it("renders label, value, unit and meta", () => {
    render(<StatTile label="Stock turnover" value="82.6" unit="%" meta="Last updated 09:41" />);
    expect(screen.getByText("Stock turnover")).toBeInTheDocument();
    expect(screen.getByText("82.6")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
    expect(screen.getByText("Last updated 09:41")).toBeInTheDocument();
  });

  it("renders the delta chip", () => {
    render(<StatTile label="Alerts" value="12" delta={{ label: "+12%", direction: "up" }} />);
    expect(screen.getByText("+12%")).toBeInTheDocument();
  });
});

describe("ProgressBar", () => {
  it("exposes progressbar semantics with a clamped value", () => {
    render(<ProgressBar value={82} label="Bay 12" />);
    const bar = screen.getByRole("progressbar", { name: "Bay 12" });
    expect(bar).toHaveAttribute("aria-valuenow", "82");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("clamps out-of-range values", () => {
    render(<ProgressBar value={150} label="Over" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("picks a warning/danger tone at high fill levels", () => {
    const { rerender } = render(<ProgressBar value={90} label="Fill" />);
    expect(screen.getByRole("progressbar").querySelector("div")!.className).toContain(
      "bg-status-warning"
    );

    rerender(<ProgressBar value={99} label="Fill" />);
    expect(screen.getByRole("progressbar").querySelector("div")!.className).toContain(
      "bg-status-danger"
    );
  });
});
