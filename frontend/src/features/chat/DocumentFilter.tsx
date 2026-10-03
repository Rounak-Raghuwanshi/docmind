import { Check, Files } from "lucide-react";
import type { DocumentItem } from "@/api/types";
import { cn } from "@/lib/format";

/** Chips that limit a conversation to selected documents. Empty selection = all documents. */
export function DocumentFilter({
  documents,
  selected,
  onChange,
  disabled,
}: {
  documents: DocumentItem[];
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const ready = documents.filter((d) => d.status === "ready");
  if (ready.length < 2) return null;
  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  const chip =
    "inline-flex max-w-[14rem] items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors";
  return (
    <div
      className="flex flex-wrap items-center gap-1.5"
      role="group"
      aria-label="Limit to documents"
    >
      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange([])}
        aria-pressed={selected.length === 0}
        className={cn(
          chip,
          selected.length === 0
            ? "border-brand-500 bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200"
            : "border-slate-300 text-slate-600 hover:border-slate-400 dark:border-slate-700 dark:text-slate-400",
        )}
      >
        <Files className="size-3" aria-hidden /> All documents
      </button>
      {ready.map((d) => {
        const on = selected.includes(d.id);
        return (
          <button
            key={d.id}
            type="button"
            disabled={disabled}
            onClick={() => toggle(d.id)}
            aria-pressed={on}
            title={d.filename}
            className={cn(
              chip,
              on
                ? "border-brand-500 bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200"
                : "border-slate-300 text-slate-600 hover:border-slate-400 dark:border-slate-700 dark:text-slate-400",
            )}
          >
            {on && <Check className="size-3 shrink-0" aria-hidden />}
            <span className="truncate">{d.filename}</span>
          </button>
        );
      })}
    </div>
  );
}
