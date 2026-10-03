import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, UploadCloud, X, XCircle } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { uploadDocument } from "@/api/documents";
import { keys } from "@/api/keys";
import { ApiError } from "@/lib/api";
import { cn, formatBytes } from "@/lib/format";
import { ACCEPT_ATTR, validateFile } from "@/lib/uploads";
import { ProgressBar } from "./DocumentStatusBadge";

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  state: "uploading" | "done" | "error";
  error?: string;
  controller: AbortController;
}

export function UploadDropzone({ ws, compact = false }: { ws: string; compact?: boolean }) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const patch = (id: string, p: Partial<UploadItem>) =>
    setItems((list) => list.map((i) => (i.id === id ? { ...i, ...p } : i)));

  async function start(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const id = crypto.randomUUID();
      const controller = new AbortController();
      const invalid = validateFile(file);
      setItems((list) => [
        {
          id,
          file,
          progress: 0,
          state: invalid ? "error" : "uploading",
          error: invalid ?? undefined,
          controller,
        },
        ...list,
      ]);
      if (invalid) continue;
      uploadDocument(ws, file, (p) => patch(id, { progress: p }), controller.signal)
        .then(() => {
          patch(id, { state: "done", progress: 1 });
          qc.invalidateQueries({ queryKey: keys.documents(ws) });
          qc.invalidateQueries({ queryKey: keys.workspaces });
          setTimeout(() => setItems((list) => list.filter((i) => i.id !== id)), 2500);
        })
        .catch((err: unknown) => {
          const msg =
            err instanceof ApiError
              ? err.message
              : err instanceof DOMException
                ? "Cancelled"
                : "Upload failed";
          patch(id, { state: "error", error: msg });
        });
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) start(e.dataTransfer.files);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed text-center transition-colors",
          compact ? "px-4 py-4" : "px-6 py-10",
          dragging
            ? "border-brand-500 bg-brand-50 dark:bg-brand-950/40"
            : "border-slate-300 hover:border-slate-400 dark:border-slate-700",
        )}
      >
        <UploadCloud className={cn("text-brand-500", compact ? "size-6" : "size-10")} aria-hidden />
        <p className="mt-2 text-sm">
          <button
            type="button"
            className="font-semibold text-brand-600 hover:underline"
            onClick={() => inputRef.current?.click()}
          >
            Choose files
          </button>{" "}
          or drag them here
        </p>
        {!compact && (
          <p className="mt-1 text-xs text-slate-500">
            PDF, DOCX, TXT or Markdown · up to 20 MB each
          </p>
        )}
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT_ATTR}
          className="sr-only"
          aria-label="Upload documents"
          onChange={(e) => {
            if (e.target.files) start(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="mt-3 space-y-2" aria-live="polite">
          {items.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800"
            >
              <div className="flex items-center gap-2">
                {item.state === "done" && (
                  <CheckCircle2 className="size-4 text-emerald-500" aria-label="Uploaded" />
                )}
                {item.state === "error" && (
                  <XCircle className="size-4 text-red-500" aria-label="Failed" />
                )}
                <span className="min-w-0 flex-1 truncate">{item.file.name}</span>
                <span className="text-xs text-slate-500">{formatBytes(item.file.size)}</span>
                {item.state === "uploading" ? (
                  <button
                    type="button"
                    onClick={() => item.controller.abort()}
                    aria-label={`Cancel ${item.file.name}`}
                  >
                    <X className="size-4 text-slate-400 hover:text-slate-700" />
                  </button>
                ) : item.state === "error" ? (
                  <button
                    type="button"
                    onClick={() => setItems((l) => l.filter((i) => i.id !== item.id))}
                    aria-label="Dismiss"
                  >
                    <X className="size-4 text-slate-400 hover:text-slate-700" />
                  </button>
                ) : null}
              </div>
              {item.state === "uploading" && (
                <div className="mt-2">
                  <ProgressBar value={item.progress} />
                </div>
              )}
              {item.error && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{item.error}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
