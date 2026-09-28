import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Icon } from "./Icon";
import { Spinner } from "./Spinner";
import { Skeleton, SkeletonRows } from "./Skeleton";
import { EmptyState } from "./EmptyState";

describe("Icon", () => {
  it("renders the material symbol ligature and hides it from assistive tech", () => {
    render(<Icon name="warehouse" />);
    const glyph = screen.getByText("warehouse");
    expect(glyph).toHaveAttribute("aria-hidden", "true");
    expect(glyph.className).toContain("material-symbols-outlined");
  });
});

describe("Spinner", () => {
  it('announces itself with role="status" and a label', () => {
    render(<Spinner label="Loading stock" />);
    expect(screen.getByRole("status", { name: "Loading stock" })).toBeInTheDocument();
  });
});

describe("Skeleton", () => {
  it("is decorative and can be stacked", () => {
    const { container } = render(
      <div>
        <Skeleton width={120} />
        <SkeletonRows rows={3} />
      </div>
    );
    expect(container.querySelectorAll('[aria-hidden="true"]')).not.toHaveLength(0);
  });
});

describe("EmptyState", () => {
  it("renders heading, description and an action", () => {
    render(
      <EmptyState
        icon="search_off"
        heading="No stock found"
        description="Adjust the filters and try again."
        action={<button type="button">Clear filters</button>}
      />
    );
    expect(screen.getByText("No stock found")).toBeInTheDocument();
    expect(screen.getByText("Adjust the filters and try again.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear filters" })).toBeInTheDocument();
  });

  it("renders without optional parts", () => {
    render(<EmptyState heading="Nothing" />);
    expect(screen.getByText("Nothing")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
