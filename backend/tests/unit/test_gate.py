"""Relevance gate, using scores measured on real documents (see app/rag/gate.py)."""

from dataclasses import dataclass

from app.rag.gate import GateConfig, decide

CFG = GateConfig(threshold=-2.0, floor=-9.0, agree_rank=5)


@dataclass
class C:
    vector_rank: int | None
    keyword_rank: int | None
    rerank_score: float | None


def test_confident_english_match_answers() -> None:
    assert decide([C(1, 1, 7.6)], True, CFG) == "answer"


def test_hinglish_passages_found_by_both_retrievers_are_not_refused() -> None:
    # "What is a closure?" on a Hinglish JS guide: right chunk is #2 vector, #3 keyword, rerank -7.9
    assert decide([C(2, 3, -7.88), C(5, 4, -8.0)], True, CFG) == "uncertain"
    # "let vs const": #3 vector, #1 keyword, rerank -2.2
    assert decide([C(3, 1, -2.23)], True, CFG) == "uncertain"


def test_off_topic_questions_are_refused_without_the_llm() -> None:
    # "Capital of Australia?" on the JS guide: no agreement, ~-11
    assert decide([C(1, None, -11.24), C(None, 1, -11.3)], True, CFG) == "refuse"
    # "Corporate tax rate in Singapore?" on tax notes: agreement exists but below the floor
    assert decide([C(3, 2, -9.4), C(1, None, -7.89)], True, CFG) == "refuse"


def test_agreement_outside_top_ranks_does_not_count() -> None:
    assert decide([C(8, 2, -3.0), C(2, 9, -3.0)], True, CFG) == "refuse"


def test_edge_cases() -> None:
    assert decide([], True, CFG) == "refuse"
    assert decide([C(1, None, None)], False, CFG) == "answer"  # no reranker: can't gate
