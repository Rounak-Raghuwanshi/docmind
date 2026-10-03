import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { toast } from "sonner";
import { keys } from "@/api/keys";
import type { Citation, ConversationDetail } from "@/api/types";
import { rawFetch, STREAM_URL, toApiError } from "@/lib/api";
import { readSse } from "@/lib/sse";
import { useChatStore } from "@/stores/chat";

/** Ask a question and stream the answer into the chat store. */
export function useAsk() {
  const qc = useQueryClient();
  const store = useChatStore;

  return useCallback(
    async (convId: string, question: string) => {
      const controller = new AbortController();
      store.getState().start(convId, question, controller);
      const { update, appendText } = store.getState();

      try {
        const res = await rawFetch(
          `/api/conversations/${convId}/messages`,
          {
            method: "POST",
            body: { question },
            headers: { Accept: "text/event-stream" },
            signal: controller.signal,
          },
          STREAM_URL,
        );
        if (!res.ok) throw await toApiError(res);

        await readSse(res, (event, data) => {
          switch (event) {
            case "meta": {
              const d = data as { message_id: string; rewritten_question: string };
              update(convId, { messageId: d.message_id, rewritten: d.rewritten_question });
              break;
            }
            case "token":
              appendText(convId, (data as { text: string }).text);
              break;
            case "citations":
              update(convId, { citations: data as Citation[] });
              break;
            case "done": {
              const d = data as { total_ms: number; cached: boolean; not_found: boolean };
              update(convId, {
                status: "complete",
                totalMs: d.total_ms,
                cached: d.cached,
                notFound: d.not_found,
              });
              break;
            }
            case "error": {
              const d = data as { error: { message: string } };
              update(convId, { status: "error", error: d.error.message });
              break;
            }
          }
        });
        const cur = store.getState().streams[convId];
        if (cur?.status === "streaming") {
          update(convId, { status: "error", error: "The connection closed unexpectedly." });
        }
      } catch (err) {
        if (controller.signal.aborted) {
          update(convId, { status: "stopped" });
        } else {
          const e = err as { status?: number; message?: string; retryAfter?: number };
          const message =
            e.status === 429
              ? `You're asking too quickly. Try again in ${e.retryAfter ?? 60}s.`
              : (e.message ?? "Couldn't reach the server");
          update(convId, { status: "error", error: message });
          toast.error(message);
        }
      } finally {
        // Swap the streamed answer for the saved message once the server has it.
        await qc.invalidateQueries({ queryKey: keys.conversation(convId) });
        const saved = qc.getQueryData<ConversationDetail>(keys.conversation(convId));
        const id = store.getState().streams[convId]?.messageId;
        if (!id || saved?.messages.some((m) => m.id === id)) {
          store.getState().clear(convId);
        } else {
          // Stopped streams are saved a moment after the disconnect; try once more.
          setTimeout(async () => {
            await qc.invalidateQueries({ queryKey: keys.conversation(convId) });
            store.getState().clear(convId);
          }, 600);
        }
        qc.invalidateQueries({
          queryKey: ["workspaces"],
          predicate: (q) => q.queryKey[2] === "conversations",
        });
      }
    },
    [qc, store],
  );
}
