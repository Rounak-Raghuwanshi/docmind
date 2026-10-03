import re
from typing import Any

_MARKER = re.compile(r"\[(\d{1,2})\]")


def cited_numbers(answer: str) -> list[int]:
    """Distinct [n] markers in order of first appearance."""
    seen: list[int] = []
    for m in _MARKER.finditer(answer):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def strip_invalid_markers(answer: str, valid: set[int]) -> str:
    """Remove markers that point at sources the model was never given."""
    return _MARKER.sub(lambda m: m.group(0) if int(m.group(1)) in valid else "", answer)


def build_citations(answer: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map [n] markers to the n-th source (1-based). Unknown numbers are dropped."""
    citations: list[dict[str, Any]] = []
    for n in cited_numbers(answer):
        if 1 <= n <= len(sources):
            src = sources[n - 1]
            citations.append(
                {
                    "n": n,
                    "chunk_id": str(src["chunk_id"]),
                    "document_id": str(src["document_id"]),
                    "filename": src["filename"],
                    "page": src["page_start"],
                    "page_end": src["page_end"],
                    "snippet": src["content"][:200],
                }
            )
    return citations
