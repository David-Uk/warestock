import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "../../components/ui";
import ComponentGallery from "./ComponentGallery";
import ShellDemo from "./ShellDemo";

describe("ComponentGallery", () => {
  it("renders every section heading", () => {
    render(
      <MemoryRouter>
        <ComponentGallery />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: "WareStock Component Library" })
    ).toBeInTheDocument();
    for (const section of ["Foundations", "Buttons", "Badges & alerts", "Form controls"]) {
      expect(screen.getByRole("heading", { name: section })).toBeInTheDocument();
    }
  });

  it("opens and closes the transfer modal", async () => {
    render(
      <MemoryRouter>
        <ComponentGallery />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "Open modal" }));
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Transfer stock");

    await userEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("queues a toast from the feedback row", async () => {
    render(
      <MemoryRouter>
        <ComponentGallery />
        <Toaster />
      </MemoryRouter>
    );

    await userEvent.click(screen.getByRole("button", { name: "Success" }));
    expect(screen.getByRole("region", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByText("Count saved")).toBeInTheDocument();
  });

  it("exercises interactive controls", async () => {
    render(
      <MemoryRouter>
        <ComponentGallery />
        <Toaster />
      </MemoryRouter>
    );

    // Sortable table header
    await userEvent.click(screen.getByRole("button", { name: "SKU" }));
    // Loading / empty-state toggles
    await userEvent.click(screen.getByRole("button", { name: "Show loading" }));
    await userEvent.click(screen.getByRole("button", { name: "Stop loading" }));
    await userEvent.click(screen.getByRole("button", { name: "Show empty state" }));
    await userEvent.click(screen.getByRole("button", { name: "Show rows" }));
    // Pagination + capacity meter
    await userEvent.click(screen.getByRole("button", { name: "Page 4" }));
    await userEvent.click(screen.getByRole("button", { name: "Simulate fill change" }));
    // Dismissible banner + header actions
    const dismissButtons = screen.getAllByRole("button", { name: "Dismiss message" });
    await userEvent.click(dismissButtons[0]);
    await userEvent.click(screen.getByRole("button", { name: "Announce" }));
    // Destructive confirmation flow
    await userEvent.click(screen.getByRole("button", { name: "Destructive confirm" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument(), {
      timeout: 2000,
    });
    expect(screen.getByText("Alert ACK-2041 marked as resolved.")).toBeInTheDocument();
  }, 15000);
});

describe("ShellDemo", () => {
  it("renders the app chrome with page content", () => {
    render(
      <MemoryRouter initialEntries={["/design/shell"]}>
        <ShellDemo />
      </MemoryRouter>
    );

    expect(screen.getByText("Warestock")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Shell preview" })).toBeInTheDocument();
    expect(screen.getByText("Dana Whitfield")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
  });

  it("exposes the sign out control", async () => {
    render(
      <MemoryRouter initialEntries={["/design/shell"]}>
        <ShellDemo />
      </MemoryRouter>
    );

    const signOut = screen.getAllByRole("button", { name: "Sign out" });
    expect(signOut.length).toBeGreaterThan(0);
    await userEvent.click(signOut[0]);
  });
});
