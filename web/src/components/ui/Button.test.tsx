import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its children and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save count</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Save count" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies variant styling", () => {
    const { rerender } = render(<Button variant="hazard">Delete</Button>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("bg-status-danger");

    rerender(<Button variant="secondary">Transfer</Button>);
    expect(screen.getByRole("button").className).toContain("border-2");
    expect(screen.getByRole("button").className).toContain("border-primary-container");
  });

  it("exposes a loading state with aria-busy and blocks clicks", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Saving
      </Button>
    );

    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Saving");
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();

    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders a leading material icon when provided", () => {
    render(<Button icon="download">Export</Button>);
    expect(screen.getByText("download")).toBeInTheDocument();
  });

  it("stays disabled when the disabled prop is set", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
