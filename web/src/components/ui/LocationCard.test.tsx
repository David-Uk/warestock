import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LocationCard } from "./LocationCard";

describe("LocationCard", () => {
  const baseProps = {
    coordinate: "A-04-BAY-12-LVL-2",
    zone: "Zone A — Racking Level 2",
    sku: "SKU-48291",
    capacity: 82,
    status: "online" as const,
  };

  it("renders coordinate, zone and sku", () => {
    render(<LocationCard {...baseProps} />);
    expect(screen.getByText("A-04-BAY-12-LVL-2")).toBeInTheDocument();
    expect(screen.getByText("Zone A — Racking Level 2")).toBeInTheDocument();
    expect(screen.getByText("SKU-48291")).toBeInTheDocument();
  });

  it("maps status to a visible pill", () => {
    const { rerender } = render(<LocationCard {...baseProps} />);
    expect(screen.getByText("Online")).toBeInTheDocument();

    rerender(<LocationCard {...baseProps} status="halted" />);
    expect(screen.getByText("Halted")).toBeInTheDocument();
  });

  it("shows the capacity meter and audit meta", () => {
    render(<LocationCard {...baseProps} lastCounted="today 09:41" />);
    expect(screen.getByRole("progressbar", { name: "Capacity" })).toHaveAttribute(
      "aria-valuenow",
      "82"
    );
    expect(screen.getByText(/last counted today 09:41/i)).toBeInTheDocument();
  });

  it("fires the CTA when provided, and omits it otherwise", async () => {
    const onOpen = vi.fn();
    const { rerender } = render(<LocationCard {...baseProps} onOpen={onOpen} />);

    await userEvent.click(screen.getByRole("button", { name: "Open bay" }));
    expect(onOpen).toHaveBeenCalledTimes(1);

    rerender(<LocationCard {...baseProps} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
