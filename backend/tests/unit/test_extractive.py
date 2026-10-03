from app.rag.extractive import WEAK_MATCH, best_sentence, extractive_answer, stems

GST = (
    "6. E-way bills and e-invoicing\n\n"
    "An e-way bill is required to move goods worth more than ₹50,000 in a consignment. "
    "It has Part A and Part B.\n\n"
    "E-invoicing is mandatory for businesses whose aggregate turnover exceeds the notified "
    "threshold, currently ₹5 crore."
)


def test_stems_match_word_variants() -> None:
    assert "invoi" in stems("invoices") and "invoi" in stems("e-invoicing")
    assert "what" not in str(stems("what is this"))


def test_best_sentence_skips_headings_and_picks_overlap() -> None:
    s = best_sentence("Who must generate e-invoices?", GST)
    assert s.startswith("E-invoicing is mandatory")


def test_extractive_answer_quotes_and_cites() -> None:
    sources = [
        {"content": GST},
        {"content": "Unrelated text about payroll taxes and salaries here."},
    ]
    ans = extractive_answer("When is an e-way bill required for goods?", sources, top_score=4.0)
    assert ans.startswith("Here's what your documents say")
    assert "₹50,000" in ans and "[1]" in ans and "[2]" not in ans


def test_weak_match_says_so() -> None:
    ans = extractive_answer("GST rate on gold?", [{"content": GST}], top_score=WEAK_MATCH - 1)
    assert ans.startswith("I couldn't find a direct answer")
    assert "[1]" in ans
