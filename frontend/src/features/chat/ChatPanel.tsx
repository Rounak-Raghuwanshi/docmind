import { useQueryClient } from "@tanstack/react-query";
import { Lightbulb, MessageSquareText } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { createConversation, useConversation, useUpdateConversation } from "@/api/chat";
import { useDocuments } from "@/api/documents";
import { keys } from "@/api/keys";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { useAsk } from "@/hooks/useChatStream";
import { useChatStore } from "@/stores/chat";
import { ChatMessage, type DisplayMessage } from "./ChatMessage";
import { Composer } from "./Composer";
import { DocumentFilter } from "./DocumentFilter";

function SuggestedQuestions({
  questions,
  onPick,
}: {
  questions: string[];
  onPick: (q: string) => void;
}) {
  if (!questions.length) return null;
  return (
    <div className="mt-8 w-full max-w-xl">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
        <Lightbulb className="size-3.5" aria-hidden /> Try asking
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {questions.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-xl border border-slate-200 p-3 text-left text-sm hover:border-brand-300 hover:bg-brand-50/50 dark:border-slate-800 dark:hover:border-brand-800 dark:hover:bg-brand-950/30"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatPanel({ conversationId }: { conversationId?: string }) {
  const ws = useCurrentWorkspace();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const ask = useAsk();
  const { data: docs } = useDocuments(ws.id);
  const { data: conv, isLoading, error, refetch } = useConversation(conversationId);
  const updateConv = useUpdateConversation(ws.id);
  const stream = useChatStore((s) => (conversationId ? s.streams[conversationId] : undefined));
  const stop = useChatStore((s) => s.stop);
  const [pendingFilter, setPendingFilter] = useState<string[]>([]);
  const [starting, setStarting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  const readyDocs = useMemo(() => (docs ?? []).filter((d) => d.status === "ready"), [docs]);
  const suggestions = useMemo(
    () => readyDocs.flatMap((d) => d.suggested_questions ?? []).slice(0, 4),
    [readyDocs],
  );
  const filter = conversationId ? (conv?.document_filter ?? []) : pendingFilter;
  const streaming = stream?.status === "streaming";

  // Follow the stream, unless the user has scrolled up to read.
  const pinnedToBottom = useRef(true);
  useEffect(() => {
    if (pinnedToBottom.current) bottomRef.current?.scrollIntoView({ block: "end" });
  }, [conv?.messages.length, stream?.text]);

  async function send(question: string) {
    if (conversationId) {
      pinnedToBottom.current = true;
      void ask(conversationId, question);
      return;
    }
    // First question of a new chat: create the conversation, then stream into it.
    setStarting(true);
    try {
      const created = await createConversation(ws.id, pendingFilter.length ? pendingFilter : null);
      qc.setQueryData(keys.conversation(created.id), { ...created, messages: [] });
      qc.invalidateQueries({ queryKey: keys.conversations(ws.id) });
      navigate(`/w/${ws.id}/c/${created.id}`);
      void ask(created.id, question);
      setPendingFilter([]);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Couldn't start the conversation");
    } finally {
      setStarting(false);
    }
  }

  function changeFilter(ids: string[]) {
    if (!conversationId) return setPendingFilter(ids);
    updateConv.mutate(
      { id: conversationId, document_ids: ids.length ? ids : null },
      { onError: (e) => toast.error(e.message) },
    );
  }

  const messages: DisplayMessage[] = conv?.messages ?? [];
  // While streaming, show the question optimistically (unless a refetch already has it)
  // followed by the partial answer.
  const last = messages[messages.length - 1];
  const questionSaved = last?.role === "user" && last.content === stream?.question;
  const streamingMessages: DisplayMessage[] = stream
    ? [
        ...(questionSaved
          ? []
          : [
              {
                id: null,
                role: "user" as const,
                content: stream.question,
                citations: [],
                status: "complete" as const,
                not_found: false,
                cached: false,
                total_ms: null,
              },
            ]),
        {
          id: stream.messageId,
          role: "assistant",
          content: stream.text,
          citations: stream.citations,
          status: stream.status === "streaming" ? "complete" : stream.status,
          not_found: stream.notFound,
          cached: stream.cached,
          total_ms: stream.totalMs,
          error: stream.error,
        },
      ]
    : [];

  const empty = !conversationId || (!isLoading && messages.length === 0 && !stream);

  return (
    <section aria-label="Chat" className="flex h-full flex-col">
      <div
        ref={scrollerRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          pinnedToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
        className="flex-1 overflow-y-auto"
      >
        {error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : conversationId && isLoading ? (
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
            <Skeleton className="ml-auto h-10 w-2/3" />
            <Skeleton className="h-24" />
          </div>
        ) : empty ? (
          <div className="flex h-full flex-col items-center justify-center px-4 py-10">
            {readyDocs.length === 0 ? (
              <EmptyState
                icon={<MessageSquareText className="size-10" />}
                title="Add documents to get started"
              >
                Upload a PDF, Word or text file. Once it's processed, ask anything and every answer
                will cite the exact page it came from.
              </EmptyState>
            ) : (
              <>
                <h1 className="text-2xl font-semibold">What would you like to know?</h1>
                <p className="mt-2 text-sm text-slate-500">
                  Answers come only from the {readyDocs.length} document
                  {readyDocs.length > 1 && "s"} in <strong>{ws.name}</strong>, with citations.
                </p>
                <SuggestedQuestions questions={suggestions} onPick={send} />
              </>
            )}
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-8 px-4 py-8">
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} conversationId={conversationId!} />
            ))}
            {streamingMessages.map((m, i) => (
              <ChatMessage
                key={`s${i}`}
                message={m}
                conversationId={conversationId!}
                streaming={m.role === "assistant" && streaming}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white/80 px-4 pb-3 pt-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="mx-auto max-w-3xl space-y-2">
          {docs && (
            <DocumentFilter
              documents={docs}
              selected={filter}
              onChange={changeFilter}
              disabled={streaming}
            />
          )}
          <Composer
            onSend={send}
            onStop={() => conversationId && stop(conversationId)}
            streaming={streaming || starting}
          />
        </div>
      </div>
    </section>
  );
}
