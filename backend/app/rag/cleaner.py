"""Normalise extracted text and strip running headers/footers."""

import re
import unicodedata
from collections import Counter

from app.rag.types import Page

_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_SPACES = re.compile(r"[ \t ]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_DIGITS = re.compile(r"\d+")
_EDGE_LINES = 2  # header/footer candidates: first and last N lines of each page


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    # A hyphen at a line break is kept: in born-digital PDFs it's almost always a real compound
    # ("short-term", "e-way"), and dropping it would corrupt those words. Only the break goes.
    text = _HYPHEN_BREAK.sub(r"\1-\2", text)
    text = _SPACES.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    return _MANY_NEWLINES.sub("\n\n", "\n".join(lines)).strip()


def _signature(line: str) -> str:
    # "Page 3 of 10" and "Page 4 of 10" must count as the same footer.
    return _DIGITS.sub("#", line.lower()).strip()


def _edge_lines(text: str) -> list[str]:
    """First/last lines of a page. Short pages contribute fewer candidates, so their body
    text (e.g. one-line slides) is never mistaken for a running header."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    n = min(_EDGE_LINES, len(lines) // 3)
    if n == 0:
        return []
    return lines[:n] + lines[-n:]


def find_repeated_lines(pages: list[Page]) -> set[str]:
    """Signatures of lines that appear at a page edge on more than half of the pages."""
    if len(pages) < 3:
        return set()
    counts: Counter[str] = Counter()
    for page in pages:
        counts.update({_signature(ln) for ln in _edge_lines(page.text)})
    threshold = len(pages) / 2
    return {sig for sig, n in counts.items() if n > threshold and sig}


def clean_pages(pages: list[Page]) -> list[Page]:
    normalised = [Page(p.number, normalise(p.text), p.ocr) for p in pages]
    repeated = find_repeated_lines(normalised)
    if not repeated:
        return normalised
    cleaned: list[Page] = []
    for page in normalised:
        edges = set(_edge_lines(page.text))
        kept = [
            ln for ln in page.text.split("\n") if not (ln in edges and _signature(ln) in repeated)
        ]
        cleaned.append(
            Page(page.number, _MANY_NEWLINES.sub("\n\n", "\n".join(kept)).strip(), page.ocr)
        )
    return cleaned
