import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { keys } from "@/api/keys";
import type { DocumentEvent, DocumentItem, Page } from "@/api/types";
import { rawFetch, STREAM_URL } from "@/lib/api";
import { readSse } from "@/lib/sse";

/**
 * Live document status for a workspace. Patches the TanStack Query cache in place so every
 * component showing documents (library, filter chips, side panel) updates together.
 * Reconnects with exponential backoff; free-tier hosts drop idle connections.
 */
export function useDocumentEvents(ws: string | undefined): void {
  const qc = useQueryClient();

  useEffect(() => {
    if (!ws) return;
    const controller = new AbortController();
    let attempt = 0;

    const apply = (event: string, data: unknown) => {
      if (event === "document_deleted") {
        const { document_id } = data as { document_id: string };
        qc.setQueryData<Page<DocumentItem>>(keys.documents(ws), (old) =>
          old ? { ...old, items: old.items.filter((d) => d.id !== document_id) } : old,
        );
        return;
      }
      if (event !== "document") return;
      const ev = data as DocumentEvent;
      let known = false;
      qc.setQueryData<Page<DocumentItem>>(keys.documents(ws), (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((d) => {
            if (d.id !== ev.document_id) return d;
            known = true;
            return {
              ...d,
              status: ev.status,
              pages_done: ev.pages_done,
              pages_total: ev.pages_total,
              error_message: ev.error_message,
            };
          }),
        };
      });
      // Finished docs gain a summary/chunk count; unknown docs were uploaded by a teammate.
      if (!known || ev.status === "ready" || ev.status === "failed") {
        qc.invalidateQueries({ queryKey: keys.documents(ws) });
        qc.invalidateQueries({ queryKey: keys.document(ev.document_id) });
      }
    };

    (async () => {
      while (!controller.signal.aborted) {
        try {
          const res = await rawFetch(
            `/api/workspaces/${ws}/documents/events`,
            { headers: { Accept: "text/event-stream" }, signal: controller.signal },
            STREAM_URL,
          );
          if (res.ok) {
            attempt = 0;
            // Catch up on anything that happened while disconnected.
            qc.invalidateQueries({ queryKey: keys.documents(ws) });
            await readSse(res, apply);
          } else if (res.status === 404 || res.status === 401) {
            return;
          }
        } catch {
          if (controller.signal.aborted) return;
        }
        const delay = Math.min(30_000, 1000 * 2 ** attempt++);
        await new Promise((r) => setTimeout(r, delay));
      }
    })();

    return () => controller.abort();
  }, [ws, qc]);
}
