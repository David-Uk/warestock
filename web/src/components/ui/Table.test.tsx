import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Table, type Column, type SortState } from "./Table";

interface Row {
  id: string;
  sku: string;
  qty: number;
}

const rows: Row[] = [
  { id: "1", sku: "SKU-1", qty: 100 },
  { id: "2", sku: "SKU-2", qty: 50 },
];

const columns: Array<Column<Row>> = [
  { key: "sku", header: "SKU", accessor: "sku", mono: true, sortable: true },
  { key: "qty", header: "On hand", align: "right", render: (row) => row.qty, sortable: true },
];

const baseProps = {
  columns,
  rows,
  getRowId: (row: Row) => row.id,
  caption: "Stock manifest",
};

describe("Table", () => {
  it("renders a caption and all cells", () => {
    render(<Table {...baseProps} />);
    expect(screen.getByRole("table", { name: "Stock manifest" })).toBeInTheDocument();
    expect(screen.getByText("SKU-1")).toBeInTheDocument();
    expect(screen.getByText("SKU-2")).toBeInTheDocument();
    expect(screen.getByText("On hand")).toBeInTheDocument();
  });

  it("supports column-level accessors and renderers", () => {
    render(<Table {...baseProps} />);
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("toggles sort state from the header buttons with aria-sort", async () => {
    const onSort = vi.fn<(next: SortState) => void>();
    const sort: SortState = { key: "sku", dir: "asc" };
    const { rerender } = render(<Table {...baseProps} sort={sort} onSort={onSort} />);

    const skuHeader = screen.getByRole("columnheader", { name: /SKU/ });
    expect(skuHeader).toHaveAttribute("aria-sort", "ascending");

    await userEvent.click(within(skuHeader).getByRole("button"));
    expect(onSort).toHaveBeenCalledWith({ key: "sku", dir: "desc" });

    rerender(<Table {...baseProps} sort={{ key: "sku", dir: "desc" }} onSort={onSort} />);
    expect(screen.getByRole("columnheader", { name: /SKU/ })).toHaveAttribute(
      "aria-sort",
      "descending"
    );
  });

  it("shows skeleton rows while loading", () => {
    render(<Table {...baseProps} rows={[]} loading skeletonRows={4} />);
    expect(screen.queryByText("SKU-1")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".animate-pulse")).not.toHaveLength(0);
  });

  it("renders the empty state when there are no rows", () => {
    render(<Table {...baseProps} rows={[]} emptyState={<div>No stock found</div>} />);
    expect(screen.getByText("No stock found")).toBeInTheDocument();
  });

  it("applies custom row class names", () => {
    render(<Table {...baseProps} rowClassName={() => "custom-row"} />);
    expect(document.querySelectorAll("tbody tr.custom-row")).toHaveLength(2);
  });

  it("fires onRowClick", async () => {
    const onRowClick = vi.fn();
    render(<Table {...baseProps} onRowClick={onRowClick} />);
    await userEvent.click(screen.getByText("SKU-1"));
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });
});
