import { useQuery } from "@tanstack/react-query";
import { FileText, X } from "lucide-react";
import { lazy, Suspense } from "react";
import { fetchDocumentFile, fetchPageText, useDocument } from "@/api/documents";
import type { Citation } from "@/api/types";
import { ErrorState, Spinner } from "@/components/ui";
import { formatPages } from "@/lib/citations";

const PdfViewer = lazy(() => import("./PdfViewer"));

function TextSectionViewer({
  documentId,
  page,
  snippet,
}: {
  documentId: string;
  page: number;
  snippet?: string;
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["documents", documentId, "pages", page],
    queryFn: () => fetchPageText(documentId, page),
  });
  if (isLoading)
    return (
      <div className="flex justify-center p-8">
        <Spinner />
      </div>
    );
  if (error) return <ErrorState error={error} />;
  const head = snippet?.slice(0, 60);
  return (
    <div className="h-full overflow-y-auto p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
        Section {page}
      </p>
      {data?.map((chunk, i) => {
        const cited = !!head && chunk.includes(head);
        return (
          <p
            key={i}
            className={`mb-3 whitespace-pre-wrap rounded-md p-2 text-sm leading-relaxed ${cited ? "bg-yellow-100 dark:bg-yellow-900/40" : ""}`}
          >
            {chunk}
          </p>
        );
      })}
    </div>
  );
}

export function DocumentViewer({
  documentId,
  citation,
  onClose,
}: {
  documentId: string;
  citation: Citation | null;
  onClose: () => void;
}) {
  const doc = useDocument(documentId);
  const isPdf = doc.data?.content_type === "application/pdf";
  const file = useQuery({
    queryKey: ["documents", documentId, "file"],
    queryFn: () => fetchDocumentFile(documentId),
    enabled: isPdf,
    staleTime: Infinity,
    gcTime: 5 * 60_000,
  });
  const page = citation?.page ?? 1;

  return (
    <section aria-label="Document viewer" className="flex h-full flex-col">
      <div className="flex items-start gap-2 border-b border-slate-200 p-3 dark:border-slate-800">
        <FileText className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{doc.data?.filename ?? "Loading…"}</p>
          {citation && (
            <p className="text-xs text-slate-500">
              Source [{citation.n}] · {formatPages(citation)}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close viewer"
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
        >
          <X className="size-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1">
        {doc.error ? (
          <ErrorState error={doc.error} />
        ) : !doc.data ? (
          <div className="flex justify-center p-8">
            <Spinner />
          </div>
        ) : isPdf ? (
          file.error ? (
            <ErrorState error={file.error} onRetry={() => file.refetch()} />
          ) : file.data ? (
            <Suspense
              fallback={
                <div className="flex justify-center p-8">
                  <Spinner />
                </div>
              }
            >
              <PdfViewer data={file.data} page={page} snippet={citation?.snippet} />
            </Suspense>
          ) : (
            <div className="flex justify-center p-8">
              <Spinner label="Loading PDF" />
            </div>
          )
        ) : (
          <TextSectionViewer documentId={documentId} page={page} snippet={citation?.snippet} />
        )}
      </div>
    </section>
  );
}
