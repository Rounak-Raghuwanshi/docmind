import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_URL, getAccessToken, rawFetch, refreshSession, toApiError } from "@/lib/api";
import { keys } from "./keys";
import type { DocumentItem, Page } from "./types";

export function useDocuments(ws: string) {
  return useQuery({
    queryKey: keys.documents(ws),
    queryFn: () => api<Page<DocumentItem>>(`/api/workspaces/${ws}/documents?limit=100`),
    select: (page) => page.items,
  });
}

export function useDocument(id: string | null) {
  return useQuery({
    queryKey: keys.document(id ?? ""),
    queryFn: () => api<DocumentItem>(`/api/documents/${id}`),
    enabled: !!id,
  });
}

/**
 * Upload with real progress. fetch() can't report upload progress, so this uses XHR.
 */
export function uploadDocument(
  ws: string,
  file: File,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<DocumentItem> {
  const send = (token: string | null) =>
    new Promise<{ status: number; body: string; headers: string }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_URL}/api/workspaces/${ws}/documents`);
      xhr.withCredentials = true;
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
      xhr.onload = () =>
        resolve({
          status: xhr.status,
          body: xhr.responseText,
          headers: xhr.getAllResponseHeaders(),
        });
      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
      signal?.addEventListener("abort", () => xhr.abort());
      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    });

  return (async () => {
    let res = await send(getAccessToken());
    if (res.status === 401 && (await refreshSession())) res = await send(getAccessToken());
    const response = new Response(res.body || null, {
      status: res.status,
      headers: parseHeaders(res.headers),
    });
    if (!response.ok) throw await toApiError(response);
    return (await response.json()) as DocumentItem;
  })();
}

function parseHeaders(raw: string): Headers {
  const h = new Headers();
  raw
    .trim()
    .split(/[\r\n]+/)
    .forEach((line) => {
      const i = line.indexOf(":");
      if (i > 0) h.append(line.slice(0, i).trim(), line.slice(i + 1).trim());
    });
  return h;
}

export function useDeleteDocument(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/api/documents/${id}`, { method: "DELETE" }),
    onMutate: async (id) => {
      // Optimistic: remove the row immediately, roll back if the server refuses.
      await qc.cancelQueries({ queryKey: keys.documents(ws) });
      const prev = qc.getQueryData<Page<DocumentItem>>(keys.documents(ws));
      qc.setQueryData<Page<DocumentItem>>(keys.documents(ws), (old) =>
        old ? { ...old, items: old.items.filter((d) => d.id !== id) } : old,
      );
      return { prev };
    },
    onError: (_e, _id, ctx) => ctx?.prev && qc.setQueryData(keys.documents(ws), ctx.prev),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: keys.documents(ws) });
      qc.invalidateQueries({ queryKey: keys.workspaces });
    },
  });
}

export function useReprocessDocument(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<DocumentItem>(`/api/documents/${id}/reprocess`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.documents(ws) }),
  });
}

export async function fetchDocumentFile(id: string): Promise<ArrayBuffer> {
  const res = await rawFetch(`/api/documents/${id}/file`);
  if (!res.ok) throw await toApiError(res);
  return res.arrayBuffer();
}

export async function fetchPageText(id: string, page: number): Promise<string[]> {
  const data = await api<{ chunks: string[] }>(`/api/documents/${id}/pages/${page}`);
  return data.chunks;
}
