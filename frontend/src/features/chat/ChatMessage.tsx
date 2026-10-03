import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Search, StopCircle, ThumbsDown, ThumbsUp, Zap } from "lucide-react";
import { useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendFeedback } from "@/api/chat";
import type { Citation, Message } from "@/api/types";
import { Badge } from "@/components/ui";
import { linkCitations } from "@/lib/citations";
import { cn, formatMs } from "@/lib/format";
import { CitationChip } from "./CitationChip";
import { SourcesDebug } from "./SourcesDebug";
import { notify } from "@/lib/notify";
import { promptDialog } from "@/stores/dialog";

export interface DisplayMessage extends Pick<
  Message,
  "role" | "content" | "status" | "not_found" | "cached" | "total_ms"
> {
  id: string | null;
  citations: Citation[] | null; // null while streaming (markers not yet validated)
  feedback?: 1 | -1 | null;
  error?: string | null;
  model?: string | null;
}

function AnswerMarkdown({ text, citations }: { text: string; citations: Citation[] | null }) {
  const byN = new Map((citations ?? []).map((c) => [c.n, c]));
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      urlTransform={(url) => (url.startsWith("cite:") ? url : defaultUrlTransform(url))}
      components={{
        a: ({ href, children }) => {
          if (href?.startsWith("cite:")) {
            const c = byN.get(Number(href.slice(5)));
            return c ? <CitationChip citation={c} /> : null;
          }
          return (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          );
        },
      }}
    >
      {linkCitations(text, citations)}
    </ReactMarkdown>
  );
}

function Feedback({
  messageId,
  initial,
  conversationId,
}: {
  messageId: string;
  initial: 1 | -1 | null | undefined;
  conversationId: string;
}) {
  const [rating, setRating] = useState<1 | -1 | null>(initial ?? null);
  const qc = useQueryClient();
  async function rate(value: 1 | -1) {
    let comment: string | undefined;
    if (value === -1) {
      const text = await promptDialog({
        title: "What was wrong with this answer?",
        description: "Optional. Your note helps the workspace owner improve the documents.",
        placeholder: "e.g. It missed the limit for senior citizens",
        confirmText: "Send feedback",
        multiline: true,
      });
      if (text === null) return; // cancelled: don't record a rating
      comment = text.trim() || undefined;
    }
    const prev = rating;
    setRating(value);
    try {
      await sendFeedback(messageId, value, comment);
      qc.invalidateQueries({ queryKey: ["conversations", conversationId] });
    } catch {
      setRating(prev);
      notify.error("Couldn't save your feedback");
    }
  }
  return (
    <div className="flex items-center gap-1">
      {([1, -1] as const).map((v) => {
        const Icon = v === 1 ? ThumbsUp : ThumbsDown;
        return (
          <button
            key={v}
            type="button"
            onClick={() => rate(v)}
            aria-pressed={rating === v}
            aria-label={v === 1 ? "Helpful" : "Not helpful"}
            className={cn(
              "rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800",
              rating === v ? "text-brand-600" : "text-slate-400",
            )}
          >
            <Icon className="size-4" />
          </button>
        );
      })}
    </div>
  );
}

export function ChatMessage({
  message,
  conversationId,
  streaming = false,
}: {
  message: DisplayMessage;
  conversationId: string;
  streaming?: boolean;
}) {
  const [showSources, setShowSources] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  const waiting = streaming && !message.content;
  const done = !streaming && !!message.id;
  return (
    <article className="group" aria-busy={streaming}>
      <div
        className={cn(
          "prose prose-sm prose-slate max-w-none dark:prose-invert prose-p:my-2 prose-ul:my-2 prose-li:my-0.5",
          streaming && message.content && "typing-caret",
          message.not_found && "text-slate-600 dark:text-slate-400",
        )}
      >
        {waiting ? (
          <p className="flex items-center gap-2 text-slate-500">
            <span className="inline-flex gap-1" aria-hidden>
              <span className="size-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
              <span className="size-1.5 animate-bounce rounded-full bg-slate-400" />
            </span>
            Searching your documents…
          </p>
        ) : (
          <AnswerMarkdown text={message.content} citations={message.citations} />
        )}
      </div>

      {message.error && (
        <p
          role="alert"
          className="mt-2 flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400"
        >
          <AlertTriangle className="size-4" aria-hidden /> {message.error}
        </p>
      )}

      {message.citations && message.citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Sources">
          {message.citations.map((c) => (
            <CitationChip key={`${c.n}-${c.chunk_id}`} citation={c} inline={false} />
          ))}
        </div>
      )}

      {done && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          {message.status === "stopped" && (
            <Badge>
              <StopCircle className="size-3" aria-hidden /> Stopped
            </Badge>
          )}
          {message.status === "error" && <Badge tone="red">Error</Badge>}
          {message.model === "extractive" && (
            <span title="No AI model is configured, so this answer quotes the best-matching sentences directly. Set LLM_PROVIDER and an API key in backend/.env for written answers.">
              <Badge>Quoted from documents · no LLM</Badge>
            </span>
          )}
          {message.cached && (
            <Badge tone="brand">
              <Zap className="size-3" aria-hidden /> Cached
            </Badge>
          )}
          {message.total_ms !== null && <span>{formatMs(message.total_ms)}</span>}
          <span className="flex-1" />
          {!message.cached && (
            <button
              type="button"
              onClick={() => setShowSources((s) => !s)}
              aria-expanded={showSources}
              className="flex items-center gap-1 rounded px-1.5 py-1 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <Search className="size-3.5" aria-hidden /> {showSources ? "Hide" : "Show"} sources
            </button>
          )}
          {message.id && (
            <Feedback
              messageId={message.id}
              initial={message.feedback}
              conversationId={conversationId}
            />
          )}
        </div>
      )}
      {showSources && message.id && <SourcesDebug messageId={message.id} />}
    </article>
  );
}
