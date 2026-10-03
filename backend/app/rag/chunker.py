"""Structure-aware chunking: headings > paragraphs > sentences, with sentence-level overlap.

Every chunk keeps the page range it came from (for citations) and the nearest heading
(prefixed as context, which noticeably improves retrieval of short, generic passages).
"""

import re
from dataclasses import dataclass

from app.rag.tokens import count_tokens
from app.rag.types import ChunkDraft, Page

# Split after . ! ? (optionally followed by a closing quote/bracket) when the next
# sentence starts with a capital, digit, quote or bracket. Avoids "e.g. foo" and "3.5".
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]?\s+(?=[\"'(\[A-Z0-9])")
_MD_HEADING = re.compile(r"^#{1,6}\s+")
_NUMBERED_HEADING = re.compile(
    r"^((section|chapter|part|article|schedule|rule)\s+[\w.()-]+|\d+(\.\d+)*\.?\s+[A-Z])",
    re.IGNORECASE,
)
_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "viz.", "sec.", "no.", "vs.", "mr.", "ms.", "dr.", "rs.")


@dataclass(slots=True)
class _Unit:
    text: str
    page: int
    tokens: int
    starts_paragraph: bool


def is_heading(paragraph: str) -> bool:
    line = paragraph.strip()
    if "\n" in line or not line:
        return False
    if _MD_HEADING.match(line):
        return True
    ends_like_prose = line.endswith((".", ",", ";", ":"))
    if len(line) > 90 or (ends_like_prose and not _NUMBERED_HEADING.match(line)):
        return False
    words = line.split()
    if len(words) > 12:
        return False
    if _NUMBERED_HEADING.match(line):
        return True
    letters = [c for c in line if c.isalpha()]
    return (
        bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.8 and len(words) >= 2
    )


def split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_END.split(text.replace("\n", " "))
    sentences: list[str] = []
    for part in (p.strip() for p in parts):
        if not part:
            continue
        # Re-join false splits after common abbreviations ("Sec. 80D").
        if sentences and sentences[-1].lower().endswith(_ABBREVIATIONS):
            sentences[-1] = f"{sentences[-1]} {part}"
        else:
            sentences.append(part)
    return sentences


def _hard_split(sentence: str, max_tokens: int) -> list[str]:
    """Last resort for a single "sentence" longer than a chunk (tables, run-on OCR text)."""
    words = sentence.split()
    step = max(1, int(max_tokens / 1.3))
    return [" ".join(words[i : i + step]) for i in range(0, len(words), step)]


def chunk_pages(
    pages: list[Page],
    *,
    title: str,
    target_tokens: int = 400,
    overlap_tokens: int = 60,
) -> list[ChunkDraft]:
    min_tokens = max(1, target_tokens // 4)
    chunks: list[ChunkDraft] = []
    current: list[_Unit] = []
    current_tokens = 0
    heading = ""
    chunk_heading = ""

    def flush(carry_overlap: bool) -> None:
        nonlocal current, current_tokens, chunk_heading
        if not current:
            return
        body = ""
        for u in current:
            if body:
                body += "\n\n" if u.starts_paragraph else " "
            body += u.text
        context = f"{title} › {chunk_heading}" if chunk_heading else title
        chunks.append(
            ChunkDraft(
                index=len(chunks),
                page_start=current[0].page,
                page_end=current[-1].page,
                context=context,
                content=body,
                token_count=current_tokens,
            )
        )
        tail: list[_Unit] = []
        if carry_overlap and overlap_tokens > 0:
            # Carry whole trailing sentences (never partial ones) into the next chunk.
            budget = 0
            for u in reversed(current[1:]):
                if budget + u.tokens > overlap_tokens:
                    break
                tail.insert(0, u)
                budget += u.tokens
        current = tail
        current_tokens = sum(u.tokens for u in tail)
        chunk_heading = heading

    for page in pages:
        # Page breaks are soft boundaries: citations point at page_start, so chunks that
        # straddle fewer pages make "see page N" more precise. Tiny pages still merge.
        if current_tokens >= min_tokens:
            flush(carry_overlap=False)
        for paragraph in (p.strip() for p in page.text.split("\n\n")):
            if not paragraph:
                continue
            if is_heading(paragraph):
                # A heading is a hard boundary unless the current chunk is still tiny.
                if current_tokens >= min_tokens:
                    flush(carry_overlap=False)
                heading = _MD_HEADING.sub("", paragraph).strip()
                if not current:
                    chunk_heading = heading
                current.append(_Unit(heading, page.number, count_tokens(heading), True))
                current_tokens += current[-1].tokens
                continue

            first = True
            for sentence in split_sentences(paragraph):
                pieces = (
                    _hard_split(sentence, target_tokens)
                    if count_tokens(sentence) > target_tokens
                    else [sentence]
                )
                for piece in pieces:
                    n = count_tokens(piece)
                    if current and current_tokens + n > target_tokens:
                        flush(carry_overlap=True)
                    if not current:
                        chunk_heading = heading
                    current.append(_Unit(piece, page.number, n, first))
                    current_tokens += n
                    first = False
    flush(carry_overlap=False)
    return chunks
