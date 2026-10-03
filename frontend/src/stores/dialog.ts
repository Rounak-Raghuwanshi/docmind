/**
 * Promise-based dialogs: `if (await confirmDialog({...}))` reads like window.confirm, but the
 * dialog is our own accessible, themed component (rendered once by <DialogHost />).
 */
import { create } from "zustand";

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "default" | "danger";
}

export interface PromptOptions extends ConfirmOptions {
  placeholder?: string;
  defaultValue?: string;
  multiline?: boolean;
}

type Request =
  | { kind: "confirm"; options: ConfirmOptions; resolve: (ok: boolean) => void }
  | { kind: "prompt"; options: PromptOptions; resolve: (value: string | null) => void };

interface DialogState {
  current: Request | null;
  open: (req: Request) => void;
  close: () => void;
}

export const useDialogStore = create<DialogState>()((set, get) => ({
  current: null,
  open: (req) => {
    // Only one dialog at a time: cancel whatever was open.
    const prev = get().current;
    if (prev?.kind === "confirm") prev.resolve(false);
    else if (prev?.kind === "prompt") prev.resolve(null);
    set({ current: req });
  },
  close: () => set({ current: null }),
}));

export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) =>
    useDialogStore.getState().open({ kind: "confirm", options, resolve }),
  );
}

/** Resolves with the entered text ("" allowed), or null if cancelled. */
export function promptDialog(options: PromptOptions): Promise<string | null> {
  return new Promise((resolve) =>
    useDialogStore.getState().open({ kind: "prompt", options, resolve }),
  );
}
