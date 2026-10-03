import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import type { DocumentItem } from "@/api/types";
import { Badge } from "@/components/ui";

type Doc = Pick<DocumentItem, "status" | "pages_done" | "pages_total" | "error_message">;

export function progressOf(doc: Doc): number | null {
  if (doc.status !== "processing" || !doc.pages_total) return null;
  return Math.min(1, doc.pages_done / doc.pages_total);
}

/** Status is kept live by useDocumentEvents (SSE) patching the query cache. */
export function DocumentStatusBadge({ doc }: { doc: Doc }) {
  switch (doc.status) {
    case "queued":
      return (
        <Badge>
          <Clock className="size-3" aria-hidden /> Queued
        </Badge>
      );
    case "processing": {
      const parsing = doc.pages_total && doc.pages_done < doc.pages_total;
      return (
        <Badge tone="amber">
          <Loader2 className="size-3 animate-spin" aria-hidden />
          {parsing ? `Reading ${doc.pages_done}/${doc.pages_total}` : "Indexing"}
        </Badge>
      );
    }
    case "ready":
      return (
        <Badge tone="green">
          <CheckCircle2 className="size-3" aria-hidden /> Ready
        </Badge>
      );
    case "failed":
      return (
        <span title={doc.error_message ?? undefined}>
          <Badge tone="red">
            <AlertCircle className="size-3" aria-hidden /> Failed
          </Badge>
        </span>
      );
  }
}

export function ProgressBar({ value }: { value: number }) {
  return (
    <div
      className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value * 100)}
    >
      <div
        className="h-full rounded-full bg-brand-500 transition-[width] duration-300"
        style={{ width: `${value * 100}%` }}
      />
    </div>
  );
}
