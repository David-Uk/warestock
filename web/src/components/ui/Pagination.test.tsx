import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pagination } from "./Pagination";

describe("Pagination", () => {
  it("shows the item range and page size selector", () => {
    render(
      <Pagination
        page={1}
        pageCount={20}
        onPageChange={() => undefined}
        total={1240}
        pageSize={20}
        onPageSizeChange={() => undefined}
      />
    );
    expect(screen.getByText(/1–20 of 1,240/)).toBeInTheDocument();
    expect(screen.getByLabelText(/rows/i)).toBeInTheDocument();
  });

  it("disables previous on the first page and advances with next", async () => {
    const onPageChange = vi.fn();
    render(<Pagination page={1} pageCount={5} onPageChange={onPageChange} />);

    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("marks the active page with aria-current and jumps on click", async () => {
    const onPageChange = vi.fn();
    render(<Pagination page={3} pageCount={5} onPageChange={onPageChange} />);

    expect(screen.getByRole("button", { name: "Page 3" })).toHaveAttribute("aria-current", "page");

    await userEvent.click(screen.getByRole("button", { name: "Page 5" }));
    expect(onPageChange).toHaveBeenCalledWith(5);
  });

  it("collapses long ranges with gaps", () => {
    render(<Pagination page={10} pageCount={20} onPageChange={() => undefined} />);
    expect(screen.getAllByText("…").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Page 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Page 20" })).toBeInTheDocument();
  });

  it("reports page size changes", async () => {
    const onPageSizeChange = vi.fn();
    render(
      <Pagination
        page={1}
        pageCount={5}
        onPageChange={() => undefined}
        pageSize={20}
        onPageSizeChange={onPageSizeChange}
      />
    );

    await userEvent.selectOptions(screen.getByLabelText(/rows/i), "50");
    expect(onPageSizeChange).toHaveBeenCalledWith(50);
  });
});
