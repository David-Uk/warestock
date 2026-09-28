import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Checkbox } from "./Checkbox";

describe("Checkbox", () => {
  it("toggles when the row label is clicked", async () => {
    const onChange = vi.fn();
    render(<Checkbox label="Include zero-stock SKUs" onChange={onChange} />);

    await userEvent.click(screen.getByText("Include zero-stock SKUs"));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("reflects the checked state", () => {
    render(<Checkbox label="Flag variance" defaultChecked />);
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("shows description and error text", () => {
    render(<Checkbox label="Option" description="Secondary line" error="Unavailable right now" />);
    expect(screen.getByText("Secondary line")).toBeInTheDocument();
    expect(screen.getByText("Unavailable right now")).toBeInTheDocument();
  });

  it("wires aria-describedby to the error", () => {
    render(<Checkbox label="Option" error="Unavailable" />);
    const checkbox = screen.getByRole("checkbox");
    const describedBy = checkbox.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy!)).toHaveTextContent("Unavailable");
  });
});
