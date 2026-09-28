import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "./Input";

describe("Input", () => {
  it("associates the label with the field", () => {
    render(<Input label="SKU" />);
    expect(screen.getByLabelText("SKU")).toBeInTheDocument();
  });

  it("announces validation errors via aria-invalid and aria-describedby", () => {
    render(<Input label="Location" error="Location does not exist." />);
    const input = screen.getByLabelText("Location");

    expect(input).toHaveAttribute("aria-invalid", "true");
    const describedBy = input.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();

    const error = document.getElementById(describedBy!.split(" ")[0]);
    expect(error).toHaveTextContent("Location does not exist.");
  });

  it("renders hint text when there is no error", () => {
    render(<Input label="SKU" hint="Pull the trigger to scan." />);
    expect(screen.getByText("Pull the trigger to scan.")).toBeInTheDocument();
  });

  it("keeps hint and error mutually exclusive", () => {
    render(<Input label="SKU" hint="Hint" error="Error" />);
    expect(screen.queryByText("Hint")).not.toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("passes through native attributes", () => {
    render(<Input label="Qty" placeholder="0" defaultValue="12" scanner />);
    const input = screen.getByLabelText("Qty");
    expect(input).toHaveAttribute("placeholder", "0");
    expect(input).toHaveValue("12");
    expect(input.className).toContain("bg-[#FCF9F2]");
  });
});
