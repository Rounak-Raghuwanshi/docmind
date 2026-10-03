import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, HelpCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { cn } from "@/lib/format";
import { useDialogStore } from "@/stores/dialog";

/**
 * Renders the dialog requested through confirmDialog()/promptDialog(). Mounted once in App.
 * Accessibility: role="alertdialog", labelled title/description, Esc to cancel, focus moved
 * into the dialog, Tab kept inside it, and focus restored to the trigger afterwards.
 */
export function DialogHost() {
  const { current, close } = useDialogStore();
  const [value, setValue] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreFocus = useRef<HTMLElement | null>(null);

  const finish = (ok: boolean) => {
    if (!current) return;
    if (current.kind === "confirm") current.resolve(ok);
    else current.resolve(ok ? value : null);
    close();
    restoreFocus.current?.focus();
  };

  useEffect(() => {
    if (!current) return;
    restoreFocus.current = document.activeElement as HTMLElement | null;
    setValue(current.kind === "prompt" ? (current.options.defaultValue ?? "") : "");
    // Focus the input for prompts; for confirms focus Cancel, the safe choice.
    requestAnimationFrame(() => {
      const target = panelRef.current?.querySelector<HTMLElement>("[data-autofocus]");
      target?.focus();
    });
  }, [current]);

  useEffect(() => {
    if (!current) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        finish(false);
      }
      if (e.key === "Tab" && panelRef.current) {
        const items = panelRef.current.querySelectorAll<HTMLElement>("button, input, textarea");
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, value]);

  const o = current?.options;
  const danger = o?.tone === "danger";
  const Icon = danger ? AlertTriangle : HelpCircle;

  return (
    <AnimatePresence>
      {current && o && (
        <motion.div
          key="backdrop"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && finish(false)}
        >
          <motion.div
            ref={panelRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="dialog-title"
            aria-describedby={o.description ? "dialog-desc" : undefined}
            initial={{ opacity: 0, scale: 0.94, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 4 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
          >
            <form
              onSubmit={(e) => {
                e.preventDefault();
                finish(true);
              }}
            >
              <div className="flex gap-4">
                <span
                  className={cn(
                    "flex size-10 shrink-0 items-center justify-center rounded-full",
                    danger
                      ? "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400"
                      : "bg-brand-100 text-brand-600 dark:bg-brand-950 dark:text-brand-300",
                  )}
                >
                  <Icon className="size-5" aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 id="dialog-title" className="font-semibold">
                    {o.title}
                  </h2>
                  {o.description && (
                    <p id="dialog-desc" className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                      {o.description}
                    </p>
                  )}
                  {current.kind === "prompt" &&
                    (current.options.multiline ? (
                      <textarea
                        data-autofocus
                        rows={3}
                        value={value}
                        placeholder={current.options.placeholder}
                        onChange={(e) => setValue(e.target.value)}
                        aria-label={o.title}
                        className="mt-3 block w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-950"
                      />
                    ) : (
                      <input
                        data-autofocus
                        value={value}
                        placeholder={current.options.placeholder}
                        onChange={(e) => setValue(e.target.value)}
                        aria-label={o.title}
                        className="mt-3 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-950"
                      />
                    ))}
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => finish(false)}
                  {...(current.kind === "confirm" ? { "data-autofocus": true } : {})}
                >
                  {o.cancelText ?? "Cancel"}
                </Button>
                <Button type="submit" variant={danger ? "danger" : "primary"}>
                  {o.confirmText ?? "OK"}
                </Button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
