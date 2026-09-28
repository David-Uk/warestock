import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AlertBanner } from "./AlertBanner";

describe("AlertBanner", () => {
  it("renders the title and body", () => {
    render(
      <AlertBanner tone="warning" title="Reorder threshold breached">
        4 SKUs below safety stock.
      </AlertBanner>
    );
    expect(screen.getByText("Reorder threshold breached")).toBeInTheDocument();
    expect(screen.getByText("4 SKUs below safety stock.")).toBeInTheDocument();
  });

  it('uses role="alert" for critical tone and role="status" otherwise', () => {
    const { rerender } = render(
      <AlertBanner tone="critical" title="Discrepancy">
        Variance
      </AlertBanner>
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();

    rerender(
      <AlertBanner tone="info" title="Info">
        Note
      </AlertBanner>
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("calls onDismiss from the dismiss button", async () => {
    const onDismiss = vi.fn();
    render(
      <AlertBanner tone="info" title="Info" onDismiss={onDismiss}>
        Note
      </AlertBanner>
    );

    await userEvent.click(screen.getByRole("button", { name: "Dismiss message" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("omits the dismiss button when no handler is given", () => {
    render(
      <AlertBanner tone="info" title="Info">
        Note
      </AlertBanner>
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
