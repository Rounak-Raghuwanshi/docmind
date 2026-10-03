import { ArrowUp, Square } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/format";
import { useUi } from "@/stores/ui";

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({ onSend, onStop, streaming, disabled, placeholder }: Props) {
  const { draft, setDraft } = useUi();
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  // Pick up "Ask this" drafts from elsewhere in the app.
  useEffect(() => {
    if (draft) {
      setText(draft);
      setDraft("");
      ref.current?.focus();
    }
  }, [draft, setDraft]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [text]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const q = text.trim();
    if (!q || streaming || disabled) return;
    onSend(q);
    setText("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="relative">
        <label htmlFor="composer" className="sr-only">
          Ask a question
        </label>
        <textarea
          id="composer"
          ref={ref}
          rows={1}
          value={text}
          maxLength={2000}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder ?? "Ask a question about your documents…"}
          disabled={disabled}
          className="block w-full resize-none rounded-2xl border border-slate-300 bg-white py-3 pl-4 pr-14 text-sm shadow-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900"
        />
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="absolute bottom-1.5 right-1.5 flex size-9 items-center justify-center rounded-xl bg-slate-800 text-white hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900"
          >
            <Square className="size-3.5 fill-current" />
          </button>
        ) : (
          <button
            type="submit"
            aria-label="Send"
            disabled={!text.trim() || disabled}
            className={cn(
              "absolute bottom-1.5 right-1.5 flex size-9 items-center justify-center rounded-xl text-white transition-colors",
              text.trim() ? "bg-brand-600 hover:bg-brand-700" : "bg-slate-300 dark:bg-slate-700",
            )}
          >
            <ArrowUp className="size-4" />
          </button>
        )}
      </div>
      <p className="mt-1.5 px-1 text-[11px] text-slate-400">
        Enter to send · Shift+Enter for a new line · Answers cite your documents
      </p>
    </form>
  );
}
