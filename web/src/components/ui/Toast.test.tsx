import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "../../store/toastStore";
import { Toaster } from "./Toast";

describe("Toaster", () => {
  beforeEach(() => {
    act(() => {
      toast.clear();
    });
  });

  afterEach(() => {
    act(() => {
      toast.clear();
    });
    vi.useRealTimers();
  });

  it("renders nothing while the queue is empty", () => {
    render(<Toaster />);
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("shows success toasts as status and error toasts as alerts", () => {
    render(<Toaster />);

    act(() => {
      toast.success("Count saved", "A-04 reconciled.");
      toast.error("Scan failed", "Barcode not in zone.");
    });

    expect(screen.getByText("Count saved")).toBeInTheDocument();
    expect(screen.getByText("A-04 reconciled.")).toBeInTheDocument();

    const alerts = screen.getAllByRole("alert");
    expect(alerts).toHaveLength(1);
    expect(alerts[0]).toHaveTextContent("Scan failed");
  });

  it("dismisses a toast from its close button", async () => {
    render(<Toaster />);
    act(() => {
      toast.warning("Low stock");
    });

    await userEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
    expect(screen.queryByText("LOW STOCK")).not.toBeInTheDocument();
  });

  it("auto-dismisses after its duration", () => {
    vi.useFakeTimers();
    render(<Toaster />);

    act(() => {
      toast.info("Shift handover", undefined, 1000);
    });
    expect(screen.getByText("Shift handover")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.queryByText("Shift handover")).not.toBeInTheDocument();
  });
});
