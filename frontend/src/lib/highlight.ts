/** Matching helpers for highlighting a cited snippet inside the PDF text layer. */

export function normaliseForMatch(s: string): string {
  return s
    .toLowerCase()
    .replace(/-\s+/g, "") // hyphenated line breaks were joined during ingestion
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * A PDF text item (roughly one line) belongs to the cited passage if it appears inside the
 * snippet, or, for the first line, if it contains the snippet's opening words.
 */
export function shouldHighlight(item: string, snippetNorm: string): boolean {
  const n = normaliseForMatch(item);
  // Short fragments ("₹50,000", "or") appear all over a page; only phrases are distinctive.
  if (n.length < 15 || !snippetNorm) return false;
  if (snippetNorm.includes(n)) return true;
  const head = snippetNorm.slice(0, 24);
  return head.length >= 12 && n.includes(head);
}

export function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );
}
