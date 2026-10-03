import type { Citation } from "@/api/types";

/**
 * Turn "[1]" markers into markdown links with a custom scheme the renderer turns into chips.
 * Markers without a matching citation (the model invented a source) are removed.
 */
export function linkCitations(text: string, citations: Citation[] | null): string {
  const valid = citations ? new Set(citations.map((c) => c.n)) : null;
  return text.replace(/\[(\d{1,2})\](?!\()/g, (match, n: string) => {
    const num = Number(n);
    if (valid === null) return match; // still streaming: leave markers as typed
    return valid.has(num) ? `[${num}](cite:${num})` : "";
  });
}

export function formatPages(c: Pick<Citation, "page" | "page_end">): string {
  return c.page_end && c.page_end !== c.page ? `pp. ${c.page}–${c.page_end}` : `p. ${c.page}`;
}
