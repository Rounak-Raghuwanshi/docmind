"""The relevance gate: decide whether retrieved passages are worth sending to the LLM.

Signal 1, the cross-encoder score, is excellent on English text but is an English-only model:
on other languages or code-mixed text (e.g. Hinglish notes) it scores *correct* passages low.
Measured on a Hinglish JavaScript guide: right passages -2 to -8, off-topic questions ~-11.

Signal 2, retriever agreement: vector search and keyword search are independent. When both
rank the same passage near the top, that passage is very likely relevant, whatever its language.

    confident  -> top rerank score >= threshold                           -> answer
    uncertain  -> some passage is top-N in BOTH retrievers and its rerank
                  score is above a floor                                  -> answer (the LLM
                  may still say "not found"; uncited answers count as not found)
    otherwise  -> refuse without calling the LLM
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


class _Scored(Protocol):
    vector_rank: int | None
    keyword_rank: int | None
    rerank_score: float | None


Decision = Literal["answer", "uncertain", "refuse"]


@dataclass(frozen=True, slots=True)
class GateConfig:
    threshold: float = -2.0  # confident relevance
    floor: float = -9.0  # below this, even agreeing retrievers aren't enough
    agree_rank: int = 5  # "near the top" in both lists


def decide(chunks: Sequence[_Scored], reranked: bool, cfg: GateConfig) -> Decision:
    if not chunks:
        return "refuse"
    if not reranked:
        # Lite mode (no reranker): only answer when full-text search found real term matches;
        # otherwise every question would reach the LLM with arbitrary nearest neighbours.
        return "answer" if any(c.keyword_rank is not None for c in chunks) else "refuse"
    top = max((c.rerank_score for c in chunks if c.rerank_score is not None), default=None)
    if top is not None and top >= cfg.threshold:
        return "answer"
    for c in chunks:
        if (
            c.vector_rank is not None
            and c.keyword_rank is not None
            and c.vector_rank <= cfg.agree_rank
            and c.keyword_rank <= cfg.agree_rank
            and c.rerank_score is not None
            and c.rerank_score >= cfg.floor
        ):
            return "uncertain"
    return "refuse"
