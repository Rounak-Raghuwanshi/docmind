import uuid

import pytest

from app.rag.citations import (
    build_citations,
    cited_numbers,
    normalise_markers,
    strip_invalid_markers,
)
from app.rag.fusion import reciprocal_rank_fusion
from app.repositories.retrieval import keyword_query
from app.services.cache import answer_cache_key, normalise_question


def test_rrf_rewards_items_in_both_lists() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "d"]], k=60)
    order = [item for item, _ in fused]
    assert order[0] == "a"  # ranks 1 and 2
    assert order[1] == "c"  # ranks 3 and 1
    assert set(order) == {"a", "b", "c", "d"}
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["d"] == pytest.approx(1 / 63)


def test_rrf_handles_empty_lists() -> None:
    assert reciprocal_rank_fusion([[], []]) == []
    assert [i for i, _ in reciprocal_rank_fusion([["x", "y"], []])] == ["x", "y"]


SOURCES = [
    {
        "chunk_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "filename": f"doc{i}.pdf",
        "page_start": i,
        "page_end": i,
        "content": f"content {i} " * 50,
    }
    for i in range(1, 4)
]


def test_citations_map_markers_and_drop_invalid_numbers() -> None:
    answer = "Fact one [2]. Fact two [1][2]. Made up [9]."
    assert cited_numbers(answer) == [2, 1, 9]
    citations = build_citations(answer, SOURCES)
    assert [c["n"] for c in citations] == [2, 1]
    assert citations[0]["filename"] == "doc2.pdf"
    assert citations[0]["page"] == 2
    assert len(citations[0]["snippet"]) == 200


def test_strip_invalid_markers() -> None:
    assert strip_invalid_markers("A [1] B [7] C [3]", {1, 2, 3}) == "A [1] B  C [3]"


def test_cache_key_normalises_question_and_tracks_corpus_version() -> None:
    ws = uuid.uuid4()
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    k = answer_cache_key(ws, 1, None, "What is 80D?")
    assert k == answer_cache_key(ws, 1, None, "  what is   80d ")
    assert k != answer_cache_key(ws, 2, None, "What is 80D?")  # corpus changed
    assert k != answer_cache_key(uuid.uuid4(), 1, None, "What is 80D?")  # other tenant
    assert answer_cache_key(ws, 1, [d1, d2], "q") == answer_cache_key(ws, 1, [d2, d1], "q")
    assert answer_cache_key(ws, 1, [d1], "q") != answer_cache_key(ws, 1, None, "q")
    # a different model never serves another model's cached answers
    assert answer_cache_key(ws, 1, None, "q", "openai:llama") != answer_cache_key(
        ws, 1, None, "q", "none:extractive"
    )
    assert normalise_question("Hello World?!") == "hello world"


def test_keyword_query_ors_terms_and_keeps_codes() -> None:
    assert (
        keyword_query("What is the limit under 80D?")
        == "What or is or the or limit or under or 80D"
    )
    assert "GSTR-3B" in keyword_query("When is GSTR-3B due?")
    assert keyword_query("and or not") == ""
    assert keyword_query("???") == ""


def test_full_width_citation_brackets_are_normalised() -> None:
    # split across tokens, as a stream would deliver it
    assert "".join(normalise_markers(t) for t in ["₹50,000【", "1】."]) == "₹50,000[1]."
    assert cited_numbers(normalise_markers("A【2】【1】")) == [2, 1]
