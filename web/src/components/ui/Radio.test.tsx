import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Radio, RadioGroup } from "./Radio";

describe("Radio / RadioGroup", () => {
  it("groups radios under a legend and allows a single selection", async () => {
    render(
      <RadioGroup legend="Count method">
        <Radio name="method" label="Barcode scan" defaultChecked />
        <Radio name="method" label="Manual entry" />
        <Radio name="method" label="Photo count" />
      </RadioGroup>
    );

    expect(screen.getByRole("group", { name: "Count method" })).toBeInTheDocument();
    expect(screen.getByLabelText("Barcode scan")).toBeChecked();

    await userEvent.click(screen.getByLabelText("Photo count"));
    expect(screen.getByLabelText("Photo count")).toBeChecked();
    expect(screen.getByLabelText("Barcode scan")).not.toBeChecked();
  });

  it("fires onChange", async () => {
    const onChange = vi.fn();
    render(
      <RadioGroup legend="Method">
        <Radio name="m" label="Scan" onChange={onChange} />
      </RadioGroup>
    );

    await userEvent.click(screen.getByLabelText("Scan"));
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("renders group-level errors", () => {
    render(
      <RadioGroup legend="Method" error="Choose a method">
        <Radio name="m" label="Scan" />
      </RadioGroup>
    );
    expect(screen.getByText("Choose a method")).toBeInTheDocument();
    expect(screen.getByRole("group")).toHaveAttribute("aria-invalid", "true");
  });
});
