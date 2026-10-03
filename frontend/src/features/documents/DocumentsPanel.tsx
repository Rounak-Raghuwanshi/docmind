import { FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { useDocuments } from "@/api/documents";
import { EmptyState, Skeleton } from "@/components/ui";
import { hasRole, useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { useUi } from "@/stores/ui";
import { DocumentStatusBadge, ProgressBar, progressOf } from "./DocumentStatusBadge";
import { DocumentViewer } from "./DocumentViewer";
import { UploadDropzone } from "./UploadDropzone";

/** Right-hand panel: the document list, or the viewer when a citation/document is open. */
export function DocumentsPanel() {
  const ws = useCurrentWorkspace();
  const { data: docs, isLoading } = useDocuments(ws.id);
  const { activeCitation, viewerDocumentId, openCitation, openDocument } = useUi();

  if (viewerDocumentId) {
    return (
      <DocumentViewer
        key={`${viewerDocumentId}:${activeCitation?.chunk_id ?? ""}`}
        documentId={viewerDocumentId}
        citation={activeCitation}
        onClose={() => {
          openCitation(null);
          openDocument(null);
        }}
      />
    );
  }

  return (
    <section aria-label="Documents" className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <h2 className="text-sm font-semibold">Documents</h2>
        <Link
          to={`/w/${ws.id}/documents`}
          className="text-xs font-medium text-brand-600 hover:underline"
        >
          Manage
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : !docs?.length ? (
          <EmptyState icon={<FileText className="size-8" />} title="No documents">
            Upload something to start asking questions.
          </EmptyState>
        ) : (
          <ul className="space-y-1">
            {docs.map((d) => {
              const progress = progressOf(d);
              return (
                <li key={d.id}>
                  <button
                    type="button"
                    disabled={d.status !== "ready"}
                    onClick={() => openDocument(d.id)}
                    className="w-full rounded-lg px-2 py-2 text-left hover:bg-slate-100 disabled:cursor-default disabled:hover:bg-transparent dark:hover:bg-slate-800"
                  >
                    <div className="flex items-center gap-2">
                      <span className="min-w-0 flex-1 truncate text-sm">{d.filename}</span>
                      <DocumentStatusBadge doc={d} />
                    </div>
                    {progress !== null && (
                      <div className="mt-1.5">
                        <ProgressBar value={progress} />
                      </div>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {hasRole(ws, "editor") && (
          <div className="mt-4">
            <UploadDropzone ws={ws.id} compact />
          </div>
        )}
      </div>
    </section>
  );
}
