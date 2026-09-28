import React, { useEffect, useId } from "react";
import FocusTrap from "focus-trap-react";
import { cn } from "../../lib/utils";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  /** Action row rendered under a hairline at the bottom. */
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
} as const;

/**
 * Accessible dialog: focus trap, `aria-modal`, Escape to close, scroll
 * lock, backdrop dismiss. Industrial treatment — amber top strip, navy
 * header, hairline footer.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  className,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <FocusTrap
      focusTrapOptions={{
        escapeDeactivates: false,
        onDeactivate: onClose,
        // Prefer [data-autofocus], else focus-trap falls back to the first tabbable node.
        initialFocus: () => document.querySelector<HTMLElement>("[data-autofocus]") ?? undefined,
        // jsdom has no layout, so visibility checks would find no tabbable nodes.
        tabbableOptions: {
          displayCheck: import.meta.env.MODE === "test" ? "none" : "full",
        },
      }}
    >
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-space-16"
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) onClose();
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={description ? descriptionId : undefined}
          className={cn(
            "flex max-h-[90vh] w-full flex-col overflow-hidden rounded-module border border-frame bg-white shadow-lg",
            sizeClasses[size],
            className
          )}
        >
          <div className="h-1 bg-secondary-container" aria-hidden="true" />
          <header className="flex items-center justify-between gap-space-12 bg-primary-container px-space-16 py-space-12">
            <div className="min-w-0 text-white">
              <h2 id={titleId} className="truncate font-label-caps text-label-caps uppercase">
                {title}
              </h2>
              {description && (
                <p id={descriptionId} className="truncate font-mono text-mono-sm text-white/70">
                  {description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="-m-space-4 flex size-touch-target-min shrink-0 items-center justify-center rounded text-white/80 hover:bg-white/10 hover:text-white"
            >
              <span className="material-symbols-outlined text-[20px]" aria-hidden="true">
                close
              </span>
            </button>
          </header>

          <div className="flex-1 overflow-y-auto p-space-16 text-body-md text-on-surface">
            {children}
          </div>

          {footer && (
            <footer className="flex flex-wrap justify-end gap-space-8 border-t border-frame bg-surface-container-low p-space-16">
              {footer}
            </footer>
          )}
        </div>
      </div>
    </FocusTrap>
  );
}
