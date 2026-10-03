import { ChevronLeft, ChevronRight, Minus, Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { Spinner } from "@/components/ui";
import { escapeHtml, normaliseForMatch, shouldHighlight } from "@/lib/highlight";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface Props {
  data: ArrayBuffer;
  page: number;
  snippet?: string | null;
}

/** Opens at the cited page and highlights the cited passage in the text layer. */
export default function PdfViewer({ data, page: initialPage, snippet }: Props) {
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(initialPage);
  const [scale, setScale] = useState(1);
  const [width, setWidth] = useState(560);
  const containerRef = useRef<HTMLDivElement>(null);

  // react-pdf takes ownership of the buffer it's given, so hand it a copy.
  const file = useMemo(() => ({ data: new Uint8Array(data.slice(0)) }), [data]);
  const snippetNorm = useMemo(() => normaliseForMatch(snippet ?? ""), [snippet]);

  useEffect(() => setPage(initialPage), [initialPage]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(
      ([entry]) => entry && setWidth(Math.max(280, entry.contentRect.width - 32)),
    );
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const textRenderer = useCallback(
    ({ str }: { str: string }) =>
      snippetNorm && page === initialPage && shouldHighlight(str, snippetNorm)
        ? `<mark class="cite-highlight">${escapeHtml(str)}</mark>`
        : escapeHtml(str),
    [snippetNorm, page, initialPage],
  );

  const scrollToHighlight = () => {
    containerRef.current
      ?.querySelector("mark.cite-highlight")
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-3 py-2 text-sm dark:border-slate-800">
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded p-1 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span className="tabular-nums" aria-live="polite">
            Page {page} {numPages > 0 && `of ${numPages}`}
          </span>
          <button
            type="button"
            className="rounded p-1 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800"
            onClick={() => setPage((p) => Math.min(numPages, p + 1))}
            disabled={!numPages || page >= numPages}
            aria-label="Next page"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
            aria-label="Zoom out"
          >
            <Minus className="size-4" />
          </button>
          <span className="w-12 text-center tabular-nums">{Math.round(scale * 100)}%</span>
          <button
            type="button"
            className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800"
            onClick={() => setScale((s) => Math.min(3, s + 0.25))}
            aria-label="Zoom in"
          >
            <Plus className="size-4" />
          </button>
        </div>
      </div>
      <div ref={containerRef} className="flex-1 overflow-auto bg-slate-100 p-4 dark:bg-slate-900">
        <Document
          file={file}
          onLoadSuccess={({ numPages: n }) => setNumPages(n)}
          loading={
            <div className="flex justify-center p-8">
              <Spinner />
            </div>
          }
          error={<p className="p-4 text-sm text-red-600">Couldn't display this PDF.</p>}
        >
          <Page
            pageNumber={page}
            width={width * scale}
            customTextRenderer={textRenderer}
            onRenderTextLayerSuccess={scrollToHighlight}
            className="mx-auto shadow-md"
            loading={
              <div className="flex justify-center p-8">
                <Spinner />
              </div>
            }
          />
        </Document>
      </div>
    </div>
  );
}
