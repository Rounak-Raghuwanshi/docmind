import type { Citation } from "@/api/types";
import { formatPages } from "@/lib/citations";
import { cn } from "@/lib/format";
import { useUi } from "@/stores/ui";

export function CitationChip({
  citation,
  inline = true,
}: {
  citation: Citation;
  inline?: boolean;
}) {
  const { openCitation, activeCitation } = useUi();
  const active = activeCitation?.chunk_id === citation.chunk_id && activeCitation.n === citation.n;
  const label = `Source ${citation.n}: ${citation.filename}, ${formatPages(citation)}`;
  return (
    <button
      type="button"
      onClick={() => openCitation(citation)}
      title={`${label}\n\n“${citation.snippet}…”`}
      aria-label={label}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-semibold transition-colors",
        inline ? "mx-0.5 h-5 min-w-5 px-1 align-text-top text-[11px]" : "gap-1.5 px-2 py-1 text-xs",
        active
          ? "bg-brand-600 text-white"
          : "bg-brand-100 text-brand-800 hover:bg-brand-200 dark:bg-brand-950 dark:text-brand-300 dark:hover:bg-brand-900",
      )}
    >
      {inline ? (
        citation.n
      ) : (
        <>
          <span>[{citation.n}]</span>
          <span className="max-w-[12rem] truncate font-normal">{citation.filename}</span>
          <span className="font-normal opacity-70">{formatPages(citation)}</span>
        </>
      )}
    </button>
  );
}
