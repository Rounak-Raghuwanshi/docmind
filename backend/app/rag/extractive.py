"""Answers built by quoting the best-matching sentences, with no LLM involved.

Used when LLM_PROVIDER=none (no API key or local model available) and by the demo seeder.
Every sentence is copied verbatim from a retrieved passage, so the answer can't hallucinate,
but it can't summarise or combine facts the way a language model would.
"""

import re
from typing import Any

# Below this rerank score passages pass the relevance gate but barely match the question.
WEAK_MATCH = -0.5

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "and", "for", "what", "who", "how", "when", "does", "are", "is", "can", "must",
    "with", "this", "that", "from", "under", "which", "now", "our", "your", "should",
}  # fmt: skip


def stems(text: str) -> set[str]:
    """Crude stemming: "invoices" and "invoicing" both become "invoi"."""
    return {w[:5] for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _STOP}


def ranked_sentences(question: str, text: str) -> list[tuple[int, str]]:
    """Sentences of a passage (headings skipped), best overlap with the question first."""
    q = stems(question)
    sentences = [
        s.strip()
        for line in text.split("\n")
        for s in _SENTENCE.split(line)
        if len(s.strip()) > 30 and s.strip()[-1] in ".!?:"
    ]
    scored = [(len(q & stems(s)), s) for s in sentences]
    return sorted(scored, key=lambda x: x[0], reverse=True)


def best_sentence(question: str, text: str) -> str:
    ranked = ranked_sentences(question, text)
    return ranked[0][1] if ranked else text[:240]


def weak_match_answer(question: str, sources: list[dict[str, Any]]) -> str:
    closest = best_sentence(question, str(sources[0]["content"]))
    return (
        "I couldn't find a direct answer to this in your documents. The closest passage I found "
        f"says: “{closest}” [1]\n\nYou may need to upload a document that covers this topic."
    )


def extractive_answer(
    question: str, sources: list[dict[str, Any]], top_score: float | None = None
) -> str:
    """Quote up to three relevant sentences from the top two sources, each cited."""
    if top_score is not None and top_score < WEAK_MATCH:
        return weak_match_answer(question, sources)
    picked: list[tuple[str, int]] = []
    # Extra sentences must share enough words with the question; short questions need fewer.
    need = 1 if len(stems(question)) <= 2 else 2
    first = ranked_sentences(question, str(sources[0]["content"]))
    if not first:
        return f"{str(sources[0]['content'])[:300]} [1]"
    picked.append((first[0][1], 1))
    if len(first) > 1 and first[1][0] >= need:
        picked.append((first[1][1], 1))
    if len(sources) > 1:
        second = ranked_sentences(question, str(sources[1]["content"]))
        if second and second[0][0] >= need and second[0][1] not in {p for p, _ in picked}:
            picked.append((second[0][1], 2))
    if len(picked) == 1:
        return f"Here's what your documents say: {picked[0][0]} [{picked[0][1]}]"
    bullets = "\n".join(f"- {text} [{n}]" for text, n in picked)
    return f"Here's what your documents say:\n\n{bullets}"
