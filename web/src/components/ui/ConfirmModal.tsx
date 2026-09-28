import type { ReactNode } from "react";
import { Button } from "./Button";
import { Modal } from "./Modal";

export interface ConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  /** Confirmation question; optional for extra context. */
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "primary" | "danger";
  loading?: boolean;
}

/**
 * "Are you sure?" pattern — the single approved confirmation for all
 * destructive actions (DESIGN.md §9.2).
 */
export function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "primary",
  loading = false,
}: ConfirmModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="cancel" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "hazard" : "primary"}
            onClick={onConfirm}
            loading={loading}
            data-autofocus
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && <p>{message}</p>}
    </Modal>
  );
}
