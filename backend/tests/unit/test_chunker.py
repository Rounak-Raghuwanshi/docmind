import itertools

from app.rag.chunker import chunk_pages, is_heading, split_sentences
from app.rag.tokens import count_tokens
from app.rag.types import Page


def _sentences(n: int, prefix: str = "Sentence") -> str:
    return " ".join(f"{prefix} number {i} has exactly eight words here." for i in range(n))


def test_split_sentences_keeps_abbreviations_together() -> None:
    text = "Deductions under Sec. 80D are allowed. See e.g. the rules. Limits apply."
    assert split_sentences(text) == [
        "Deductions under Sec. 80D are allowed.",
        "See e.g. the rules.",
        "Limits apply.",
    ]


def test_split_sentences_does_not_split_decimals() -> None:
    assert split_sentences("The rate is 3.5 percent. It changed.") == [
        "The rate is 3.5 percent.",
        "It changed.",
    ]


def test_is_heading() -> None:
    assert is_heading("# Overview")
    assert is_heading("Section 80D")
    assert is_heading("CHAPTER VI-A DEDUCTIONS")
    assert is_heading("2.1 Eligibility")
    assert not is_heading("This is an ordinary sentence that ends with a period.")
    assert not is_heading("lowercase words without structure")


def test_chunks_respect_target_and_never_split_sentences() -> None:
    pages = [Page(1, _sentences(80))]
    chunks = chunk_pages(pages, title="Doc", target_tokens=100, overlap_tokens=0)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 100
        # every chunk starts at a sentence start and ends at a sentence end
        assert c.content.startswith("Sentence number")
        assert c.content.endswith("words here.")


def test_overlap_carries_whole_trailing_sentences() -> None:
    pages = [Page(1, _sentences(40))]
    chunks = chunk_pages(pages, title="Doc", target_tokens=60, overlap_tokens=25)
    assert len(chunks) > 2
    for prev, nxt in itertools.pairwise(chunks):
        prev_sentences = split_sentences(prev.content)
        carried = [s for s in split_sentences(nxt.content) if s in prev_sentences]
        assert carried, "consecutive chunks should share trailing sentences"
        assert prev_sentences[-len(carried) :] == carried  # a whole-sentence suffix
        assert sum(count_tokens(s) for s in carried) <= 25


def test_page_ranges_are_tracked() -> None:
    pages = [
        Page(1, _sentences(6, "First")),
        Page(2, _sentences(6, "Second")),
        Page(3, _sentences(6, "Third")),
    ]
    chunks = chunk_pages(pages, title="Doc", target_tokens=80, overlap_tokens=0)
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 3
    for c in chunks:
        assert c.page_start <= c.page_end
        if "Second" in c.content and "First" not in c.content and "Third" not in c.content:
            assert c.page_start == c.page_end == 2


def test_headings_start_new_chunks_and_set_context() -> None:
    text = "# Deductions\n\n" + _sentences(12) + "\n\n# Exemptions\n\n" + _sentences(12, "Other")
    chunks = chunk_pages([Page(1, text)], title="Tax Guide", target_tokens=400, overlap_tokens=0)
    assert len(chunks) == 2
    assert chunks[0].context == "Tax Guide › Deductions"
    assert chunks[1].context == "Tax Guide › Exemptions"
    assert chunks[1].content.startswith("Exemptions")
    assert "Deductions" in chunks[0].embedding_text


def test_oversized_sentence_is_hard_split() -> None:
    giant = " ".join(["word"] * 1000)
    chunks = chunk_pages([Page(1, giant)], title="T", target_tokens=100, overlap_tokens=0)
    assert len(chunks) >= 10
    assert all(count_tokens(c.content) <= 100 for c in chunks)


def test_empty_input() -> None:
    assert chunk_pages([Page(1, "   ")], title="T") == []
