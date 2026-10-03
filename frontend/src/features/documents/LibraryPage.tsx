import {
  ChevronDown,
  ChevronRight,
  Eye,
  FileText,
  MessageSquarePlus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { Fragment, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useDeleteDocument, useDocuments, useReprocessDocument } from "@/api/documents";
import type { DocumentItem } from "@/api/types";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { hasRole, useCurrentWorkspace } from "@/features/workspaces/useWorkspaceContext";
import { formatBytes, relativeTime } from "@/lib/format";
import { useUi } from "@/stores/ui";
import { DocumentStatusBadge, ProgressBar, progressOf } from "./DocumentStatusBadge";
import { UploadDropzone } from "./UploadDropzone";

function IconButton({
  label,
  onClick,
  children,
  danger,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 ${danger ? "hover:text-red-600" : "hover:text-slate-800 dark:hover:text-slate-100"}`}
    >
      {children}
    </button>
  );
}

function DocumentRow({ doc, canEdit }: { doc: DocumentItem; canEdit: boolean }) {
  const [open, setOpen] = useState(false);
  const ws = useCurrentWorkspace();
  const del = useDeleteDocument(ws.id);
  const reprocess = useReprocessDocument(ws.id);
  const { openDocument, setDraft } = useUi();
  const navigate = useNavigate();
  const progress = progressOf(doc);

  return (
    <Fragment>
      <tr className="border-t border-slate-200 dark:border-slate-800">
        <td className="py-3 pl-4 pr-2">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-label={open ? "Hide details" : "Show details"}
            className="rounded p-1 text-slate-400 hover:text-slate-700"
            disabled={doc.status !== "ready" && !doc.error_message}
          >
            {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          </button>
        </td>
        <td className="max-w-0 py-3 pr-4">
          <div className="flex items-center gap-2">
            <FileText className="size-4 shrink-0 text-slate-400" aria-hidden />
            <span className="truncate font-medium" title={doc.filename}>
              {doc.filename}
            </span>
          </div>
          {progress !== null && (
            <div className="mt-2 max-w-xs">
              <ProgressBar value={progress} />
            </div>
          )}
        </td>
        <td className="py-3 pr-4">
          <DocumentStatusBadge doc={doc} />
        </td>
        <td className="hidden py-3 pr-4 text-sm text-slate-500 sm:table-cell">
          {doc.pages_total ?? "—"}
        </td>
        <td className="hidden py-3 pr-4 text-sm text-slate-500 md:table-cell">
          {formatBytes(doc.size_bytes)}
        </td>
        <td className="hidden py-3 pr-4 text-sm text-slate-500 lg:table-cell">
          {relativeTime(doc.created_at)}
        </td>
        <td className="py-3 pr-4">
          <div className="flex justify-end gap-1">
            {doc.status === "ready" && (
              <IconButton
                label="View"
                onClick={() => {
                  openDocument(doc.id);
                  navigate(`/w/${ws.id}`);
                }}
              >
                <Eye className="size-4" />
              </IconButton>
            )}
            {canEdit && (doc.status === "failed" || doc.status === "ready") && (
              <IconButton
                label="Reprocess"
                onClick={() => reprocess.mutate(doc.id, { onError: (e) => toast.error(e.message) })}
              >
                <RefreshCw className="size-4" />
              </IconButton>
            )}
            {canEdit && (
              <IconButton
                label="Delete"
                danger
                onClick={() => {
                  if (confirm(`Delete “${doc.filename}”? Answers will no longer cite it.`)) {
                    del.mutate(doc.id, { onError: (e) => toast.error(e.message) });
                  }
                }}
              >
                <Trash2 className="size-4" />
              </IconButton>
            )}
          </div>
        </td>
      </tr>
      {open && (
        <tr className="bg-slate-50 dark:bg-slate-900/50">
          <td />
          <td colSpan={6} className="py-3 pr-4 text-sm">
            {doc.error_message && (
              <p className="text-red-600 dark:text-red-400">{doc.error_message}</p>
            )}
            {doc.summary ? (
              <p className="text-slate-700 dark:text-slate-300">{doc.summary}</p>
            ) : (
              doc.status === "ready" && (
                <p className="text-slate-500">Summary is being generated…</p>
              )
            )}
            {doc.suggested_questions && doc.suggested_questions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {doc.suggested_questions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      setDraft(q);
                      navigate(`/w/${ws.id}`);
                    }}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-300 px-3 py-1 text-xs hover:border-brand-400 hover:text-brand-700 dark:border-slate-700"
                  >
                    <MessageSquarePlus className="size-3" aria-hidden /> {q}
                  </button>
                ))}
              </div>
            )}
            {doc.status === "ready" && (
              <p className="mt-3 text-xs text-slate-500">
                {doc.chunk_count} passages indexed · {doc.embedding_model}
              </p>
            )}
          </td>
        </tr>
      )}
    </Fragment>
  );
}

export function LibraryPage() {
  const ws = useCurrentWorkspace();
  const { data: docs, isLoading, error, refetch } = useDocuments(ws.id);
  const canEdit = hasRole(ws, "editor");

  return (
    <main className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="text-2xl font-semibold">Library</h1>
        <p className="mt-1 text-sm text-slate-500">
          Documents are read, split into passages and indexed in the background. You can keep
          working while they process.
        </p>
        {canEdit && (
          <div className="mt-6">
            <UploadDropzone ws={ws.id} />
          </div>
        )}

        <div className="mt-8 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
          {error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : isLoading ? (
            <div className="space-y-3 p-4">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-8" />
              ))}
            </div>
          ) : !docs?.length ? (
            <EmptyState icon={<FileText className="size-10" />} title="No documents yet">
              {canEdit
                ? "Upload PDFs, Word files, text or Markdown. Scanned PDFs are OCR'd automatically."
                : "An editor or owner of this workspace can upload documents."}
            </EmptyState>
          ) : (
            <table className="w-full table-fixed text-left">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-900">
                <tr>
                  <th className="w-10 py-2 pl-4" aria-label="Details" />
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="w-36 py-2 pr-4 font-medium">Status</th>
                  <th className="hidden w-16 py-2 pr-4 font-medium sm:table-cell">Pages</th>
                  <th className="hidden w-20 py-2 pr-4 font-medium md:table-cell">Size</th>
                  <th className="hidden w-28 py-2 pr-4 font-medium lg:table-cell">Added</th>
                  <th className="w-28 py-2 pr-4" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <DocumentRow key={d.id} doc={d} canEdit={canEdit} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}
