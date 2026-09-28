import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fireEvent } from "@testing-library/react";
import { Modal } from "./Modal";
import { ConfirmModal } from "./ConfirmModal";

describe("Modal", () => {
  const baseProps = {
    open: true,
    onClose: vi.fn(),
    title: "Transfer stock",
    children: <p>Body copy</p>,
  };

  it("renders nothing when closed", () => {
    const onClose = vi.fn();
    render(
      <Modal {...baseProps} open={false} onClose={onClose}>
        Body
      </Modal>
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders an accessible dialog labelled by its title", () => {
    const onClose = vi.fn();
    render(<Modal {...baseProps} onClose={onClose} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Transfer stock");
    expect(screen.getByText("Body copy")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(<Modal {...baseProps} onClose={onClose} />);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes when the backdrop is clicked", () => {
    const onClose = vi.fn();
    const { container } = render(<Modal {...baseProps} onClose={onClose} />);

    const overlay = container.firstChild as HTMLElement;
    fireEvent.mouseDown(overlay, { target: overlay });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes from the header close button and renders the footer", async () => {
    const onClose = vi.fn();
    render(
      <Modal {...baseProps} onClose={onClose} footer={<button type="button">Apply</button>}>
        Body
      </Modal>
    );

    expect(screen.getByRole("button", { name: "Apply" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("ConfirmModal", () => {
  it("fires onConfirm and onClose from its button row", async () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    render(
      <ConfirmModal
        open
        onClose={onClose}
        onConfirm={onConfirm}
        title="Delete organisation?"
        message="This action is recorded."
        confirmLabel="Delete"
        cancelLabel="Keep"
        tone="danger"
      />
    );

    expect(screen.getByText("This action is recorded.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole("button", { name: "Keep" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("blocks interaction while loading", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmModal open onClose={() => undefined} onConfirm={onConfirm} title="Confirm" loading />
    );

    expect(screen.getByRole("button", { name: /Confirm/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
  });
});
