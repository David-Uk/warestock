import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Textarea } from "./Textarea";

describe("Textarea", () => {
  it("associates its label and accepts input", async () => {
    render(<Textarea label="Notes" />);
    const field = screen.getByLabelText("Notes");

    await userEvent.type(field, "Variance approved by shift lead.");
    expect(field).toHaveValue("Variance approved by shift lead.");
  });

  it("shows a live character counter when enabled", async () => {
    render(<Textarea label="Notes" maxLength={20} showCount />);
    expect(screen.getByText("0/20")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Notes"), "abc");
    expect(screen.getByText("3/20")).toBeInTheDocument();
  });

  it("renders error text and sets aria-invalid", () => {
    render(<Textarea label="Reason" error="Required for audit" />);
    expect(screen.getByLabelText("Reason")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Required for audit")).toBeInTheDocument();
  });
});
