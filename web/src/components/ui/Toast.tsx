import { useEffect } from "react";
import { cn } from "../../lib/utils";
import { useToastStore, type ToastItem, type ToastTone } from "../../store/toastStore";

const toneClasses: Record<ToastTone, { frame: string; icon: string; glyph: string }> = {
  success: { frame: "border-l-status-success", icon: "text-status-success", glyph: "task_alt" },
  error: { frame: "border-l-status-danger", icon: "text-status-danger", glyph: "error" },
  warning: { frame: "border-l-status-warning", icon: "text-status-warning-ink", glyph: "warning" },
  info: { frame: "border-l-primary-container", icon: "text-primary-container", glyph: "info" },
};

/**
 * Fixed notification stack. Mount once per app: `<Toaster />`.
 * Errors/warnings use role="alert", the rest role="status".
 * Trigger notifications with the `toast` API from `store/toastStore`.
 */
export function Toaster({ className }: { className?: string }) {
  const queue = useToastStore((state) => state.queue);
  const dismiss = useToastStore((state) => state.dismiss);

  useEffect(
    () => () => {
      // Clear any leftovers when the toaster unmounts (no-op when empty).
      if (useToastStore.getState().queue.length > 0) useToastStore.getState().clear();
    },
    []
  );

  if (queue.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Notifications"
      className={cn(
        "pointer-events-none fixed inset-x-space-16 bottom-space-16 z-[60] flex flex-col gap-space-8 sm:inset-x-auto sm:right-space-16 sm:w-[360px]",
        className
      )}
    >
      {queue.map((item: ToastItem) => {
        const tone = toneClasses[item.tone];
        return (
          <div
            key={item.id}
            role={item.tone === "error" || item.tone === "warning" ? "alert" : "status"}
            className={cn(
              "pointer-events-auto flex items-start gap-space-8 rounded border border-l-4 border-frame bg-white p-space-12 shadow-lg",
              tone.frame
            )}
          >
            <span
              className={cn("material-symbols-outlined mt-space-2 shrink-0 text-[20px]", tone.icon)}
              aria-hidden="true"
            >
              {tone.glyph}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-label-caps text-label-caps uppercase text-on-surface">
                {item.title}
              </p>
              {item.description && (
                <p className="text-body-sm text-on-surface-variant">{item.description}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              aria-label="Dismiss notification"
              className="-m-space-2 flex size-8 shrink-0 items-center justify-center rounded text-on-surface-variant hover:bg-black/5"
            >
              <span className="material-symbols-outlined text-[16px]" aria-hidden="true">
                close
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
