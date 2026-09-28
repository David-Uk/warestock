import { create } from "zustand";
import { nanoid } from "nanoid";

export type ToastTone = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  tone: ToastTone;
  title: string;
  description?: string;
  /** Milliseconds before auto-dismiss; 0 keeps it until dismissed. */
  duration: number;
}

interface ToastState {
  queue: ToastItem[];
  push: (item: Omit<ToastItem, "id" | "duration"> & { duration?: number }) => string;
  dismiss: (id: string) => void;
  clear: () => void;
}

const timers = new Map<string, ReturnType<typeof setTimeout>>();

export const useToastStore = create<ToastState>((set, get) => ({
  queue: [],
  push: ({ duration, ...item }) => {
    const id = nanoid();
    const resolved = duration ?? (item.tone === "error" ? 8000 : 5000);
    set((state) => ({ queue: [...state.queue, { ...item, id, duration: resolved }] }));
    if (resolved > 0) {
      timers.set(
        id,
        setTimeout(() => get().dismiss(id), resolved)
      );
    }
    return id;
  },
  dismiss: (id) => {
    const timer = timers.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.delete(id);
    }
    set((state) => ({ queue: state.queue.filter((toast) => toast.id !== id) }));
  },
  clear: () => {
    timers.forEach((timer) => clearTimeout(timer));
    timers.clear();
    set({ queue: [] });
  },
}));

/** Imperative API: `toast.success('Counted 240 units')`. */
export const toast = {
  show: (title: string, options?: { description?: string; tone?: ToastTone; duration?: number }) =>
    useToastStore.getState().push({ title, tone: options?.tone ?? "info", ...options }),
  success: (title: string, description?: string, duration?: number) =>
    useToastStore.getState().push({ title, description, tone: "success", duration }),
  error: (title: string, description?: string, duration?: number) =>
    useToastStore.getState().push({ title, description, tone: "error", duration }),
  warning: (title: string, description?: string, duration?: number) =>
    useToastStore.getState().push({ title, description, tone: "warning", duration }),
  info: (title: string, description?: string, duration?: number) =>
    useToastStore.getState().push({ title, description, tone: "info", duration }),
  dismiss: (id: string) => useToastStore.getState().dismiss(id),
  clear: () => useToastStore.getState().clear(),
};
