import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./Select";

describe("Select", () => {
  it("renders options from the options prop and labels the field", () => {
    render(
      <Select
        label="Zone"
        defaultValue="zone-a"
        options={[
          { value: "zone-a", label: "Zone A" },
          { value: "zone-b", label: "Zone B" },
        ]}
      />
    );

    const select = screen.getByLabelText("Zone");
    expect(select).toHaveValue("zone-a");
    expect(screen.getByRole("option", { name: "Zone A" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Zone B" })).toBeInTheDocument();
  });

  it("supports children for custom option markup", () => {
    render(
      <Select label="Method">
        <option value="scan">Scan</option>
      </Select>
    );
    expect(screen.getByRole("option", { name: "Scan" })).toBeInTheDocument();
  });

  it("marks invalid state and wires the error message", () => {
    render(<Select label="Zone" error="Choose a zone" />);
    const select = screen.getByLabelText("Zone");
    expect(select).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Choose a zone")).toBeInTheDocument();
  });

  it("fires onChange", async () => {
    const onChange = vi.fn();
    render(
      <Select label="Zone" onChange={onChange} defaultValue="zone-a">
        <option value="zone-a">Zone A</option>
        <option value="zone-b">Zone B</option>
      </Select>
    );

    await userEvent.selectOptions(screen.getByLabelText("Zone"), "zone-b");
    expect(onChange).toHaveBeenCalled();
  });
});
