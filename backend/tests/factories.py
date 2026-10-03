"""Builders for test documents, generated at runtime so the repo holds no binary fixtures."""

import io


def _filler(topic: str, n: int = 9) -> str:
    return " ".join(
        f"Paragraph {i} explains how the {topic} rules apply to taxpayers in ordinary situations."
        for i in range(n)
    )


TAX_PAGES = [
    (
        "INCOME TAX GUIDE\n\n"
        "Section 80C deductions\n\n"
        "Section 80C allows a deduction of up to Rs 1,50,000 for investments such as PPF, ELSS "
        "and life insurance premiums. The deduction is available to individuals and HUFs.\n\n"
        + _filler("investment")
    ),
    (
        "INCOME TAX GUIDE\n\n"
        "Section 80D health insurance\n\n"
        "Section 80D allows a deduction for health insurance premiums. The limit is Rs 25,000 for "
        "self and family, and an additional Rs 50,000 for senior citizen parents.\n\n"
        + _filler("medical")
    ),
    (
        "INCOME TAX GUIDE\n\n"
        "GST registration\n\n"
        "A supplier must register for GST when aggregate turnover exceeds Rs 40 lakh for goods. "
        "The threshold for services is Rs 20 lakh in most states.\n\n" + _filler("registration")
    ),
]


def make_pdf(pages: list[str] = TAX_PAGES) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return bytes(data)


def make_docx(paragraphs: list[tuple[str, str]]) -> bytes:
    """paragraphs: (style, text) pairs, style e.g. 'Heading 1' or 'Normal'."""
    import docx

    d = docx.Document()
    for style, text in paragraphs:
        d.add_paragraph(text, style=style)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
