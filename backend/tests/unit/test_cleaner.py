from app.rag.cleaner import clean_pages, find_repeated_lines, normalise
from app.rag.types import Page


def test_normalise_fixes_hyphenation_and_whitespace() -> None:
    assert normalise("short-\nterm   gains\t here") == "short-term gains here"
    assert normalise("a\n\n\n\nb") == "a\n\nb"
    assert normalise("ﬁle") == "file"  # NFKC expands ligatures


def test_repeated_headers_and_footers_are_removed() -> None:
    pages = [
        Page(i, f"ACME Policy Manual\nBody text for page {i}.\nMore content {i}.\nPage {i} of 4")
        for i in range(1, 5)
    ]
    assert find_repeated_lines(pages) == {"acme policy manual", "page # of #"}
    cleaned = clean_pages(pages)
    for i, page in enumerate(cleaned, start=1):
        assert "ACME" not in page.text
        assert "of 4" not in page.text
        assert f"Body text for page {i}." in page.text


def test_short_documents_keep_everything() -> None:
    pages = [Page(1, "Title\nBody"), Page(2, "Title\nBody two")]
    assert find_repeated_lines(pages) == set()
    assert clean_pages(pages)[0].text == "Title\nBody"


def test_body_lines_repeated_mid_page_are_kept() -> None:
    # A phrase repeated in the middle of pages is content, not a header.
    pages = [Page(i, f"Head {i}\nA\nB\nRepeated phrase\nC\nD\nFoot {i}") for i in range(1, 5)]
    assert all("Repeated phrase" in p.text for p in clean_pages(pages))
