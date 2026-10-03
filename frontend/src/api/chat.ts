import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { keys } from "./keys";
import type {
  Analytics,
  Conversation,
  ConversationDetail,
  Insights,
  Page,
  RetrievalDebug,
} from "./types";

export function useConversations(ws: string) {
  return useQuery({
    queryKey: keys.conversations(ws),
    queryFn: () => api<Page<Conversation>>(`/api/workspaces/${ws}/conversations?limit=100`),
    select: (page) => page.items,
  });
}

export function useConversation(id: string | undefined) {
  return useQuery({
    queryKey: keys.conversation(id ?? ""),
    queryFn: () => api<ConversationDetail>(`/api/conversations/${id}`),
    enabled: !!id,
  });
}

export function createConversation(ws: string, documentIds: string[] | null) {
  return api<Conversation>(`/api/workspaces/${ws}/conversations`, {
    method: "POST",
    body: { document_ids: documentIds },
  });
}

export function useUpdateConversation(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; title?: string; document_ids?: string[] | null }) =>
      api<Conversation>(`/api/conversations/${id}`, { method: "PATCH", body }),
    onMutate: async ({ id, title }) => {
      if (!title) return;
      await qc.cancelQueries({ queryKey: keys.conversations(ws) });
      const prev = qc.getQueryData<Page<Conversation>>(keys.conversations(ws));
      qc.setQueryData<Page<Conversation>>(keys.conversations(ws), (old) =>
        old ? { ...old, items: old.items.map((c) => (c.id === id ? { ...c, title } : c)) } : old,
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(keys.conversations(ws), ctx.prev),
    onSettled: (_d, _e, { id }) => {
      qc.invalidateQueries({ queryKey: keys.conversations(ws) });
      qc.invalidateQueries({ queryKey: keys.conversation(id) });
    },
  });
}

export function useDeleteConversation(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/conversations/${id}`, { method: "DELETE" }),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: keys.conversations(ws) });
      const prev = qc.getQueryData<Page<Conversation>>(keys.conversations(ws));
      qc.setQueryData<Page<Conversation>>(keys.conversations(ws), (old) =>
        old ? { ...old, items: old.items.filter((c) => c.id !== id) } : old,
      );
      return { prev };
    },
    onError: (_e, _id, ctx) => ctx?.prev && qc.setQueryData(keys.conversations(ws), ctx.prev),
    onSettled: () => qc.invalidateQueries({ queryKey: keys.conversations(ws) }),
  });
}

export function sendFeedback(messageId: string, rating: 1 | -1, comment?: string) {
  return api<void>(`/api/messages/${messageId}/feedback`, {
    method: "POST",
    body: { rating, comment: comment || null },
  });
}

export function useRetrievalDebug(messageId: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.retrieval(messageId),
    queryFn: () => api<RetrievalDebug>(`/api/messages/${messageId}/retrieval`),
    enabled,
    staleTime: Infinity,
  });
}

export function useAnalytics(ws: string, days: number) {
  return useQuery({
    queryKey: keys.analytics(ws, days),
    queryFn: () => api<Analytics>(`/api/workspaces/${ws}/analytics?days=${days}`),
  });
}

export function useInsights(ws: string, days: number) {
  return useQuery({
    queryKey: ["workspaces", ws, "insights", days],
    queryFn: () => api<Insights>(`/api/workspaces/${ws}/insights?days=${days}`),
  });
}
