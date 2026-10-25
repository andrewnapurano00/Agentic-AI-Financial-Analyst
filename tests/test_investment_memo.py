"""Artifact-level saved-state parity and deterministic safe memo contracts."""
from copy import deepcopy
import json
import pypdfium2 as pdfium
import pytest

from langgraphagenticai.analysis.investment_memo import clean, research_memo, portfolio_memo
from langgraphagenticai.analysis.memo_pdf import pdf_bytes


def text_pages(data):
    doc = pdfium.PdfDocument(data)
    try:
        return [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    finally:
        doc.close()


def saved():
    return {"question": "A < B & earnings – café 股票", "status": "complete",
            "report": "# Thesis\nSaved thesis with zero 0 and negative -12.\n## Valuation\nNo verified target.\n## Risks\nDemand weakens.\n## Drivers\nPricing.\n## Assumptions\nUncertain margins.",
            "evidence": [{"id": f"E{i:03}", "as_of": "2026-06-30", "retrieved_at": "2026-10-23T12:00:00Z", "unit": "USD", "basis": "quarterly", "value": -12 if i else 0,
                          "url": "https://example.com/report?custom_secret=hidden#token"} for i in range(105)]}


def test_complete_safe_deterministic_sources_and_decision_added_later():
    source = saved(); original = deepcopy(source)
    memo = research_memo(source)
    data = pdf_bytes(memo)
    assert data == pdf_bytes(research_memo(source))
    pages = text_pages(data); joined = "\n".join(pages)
    assert "Full retained narrative" not in pages[0]
    for label, value in memo.sections:
        assert label in pages[0]
    assert "E104" in joined and "2026-06-30" in joined and "quarterly" in joined
    assert "-12" in joined and "value\": 0" in joined
    assert "custom_secret" not in joined and "hidden" not in joined
    assert source == original
    source["quick_decision"] = {"summary": "Later decision retained completely", "dissent": "Unresolved dissent"}
    changed = pdf_bytes(research_memo(source))
    assert changed != data
    assert "Later decision retained completely" in "\n".join(text_pages(changed))


def test_missing_long_prose_and_glyphs_are_explicit():
    source = saved(); source["question"] *= 100
    source["report"] += "\n" + "unaltered_long_appendix " * 1500
    pages = text_pages(pdf_bytes(research_memo(source)))
    assert "A < B & earnings" in pages[0]
    assert "[U+80A1]" in pages[0]  # Unsupported glyphs do not silently become black boxes.
    assert "Full retained narrative" not in pages[0]
    assert "unaltered_long_appendix" in "".join(pages[1:])
    assert "No saved narrative" in research_memo({}).thesis


def test_secret_forms_nested_keys_unsafe_urls_and_finite_zero():
    secret = "private/key-value"
    packet = clean({"api_key": secret, "n": float("nan"), "zero": 0, "negative": -1,
                    "rows": [secret, "private%2Fkey-value", "javascript:alert(1)", "https://user:password@example.com/x", "https://example.com/x?arbitrary=secret"]}, (secret,))
    assert packet["zero"] == 0 and packet["negative"] == -1 and packet["n"] is None
    data = json.dumps(packet, allow_nan=False)
    assert secret not in data and "private%2F" not in data and "api_key" not in data
    assert "arbitrary" not in data and "javascript:" not in data and "password@" not in data


def test_portfolio_projection_parity_and_unavailable_risk():
    from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    from langgraphagenticai.portfolio_architect.workflow import build
    mandate = InvestorMandate(objective="Diversified portfolio", method="equal")
    result = build(demo_snapshot(eligible_names(mandate), mandate.benchmark), mandate)
    original = result.model_dump(mode="json")
    memo = portfolio_memo(result)
    pages = text_pages(pdf_bytes(memo)); joined = "\n".join(pages)
    assert "SYNTHETIC DEMO" in pages[0]
    assert "Complete positions" not in pages[0]
    for holding in result.holdings:
        assert holding.ticker in joined
        assert f"{holding.weight:.2%}" in pages[0]
    assert "Assumptions" in joined and "retrieved" in joined
    assert "Complete source references" not in joined
    assert len(pages) < 12  # Executive memo excludes the full research universe.
    assert original == result.model_dump(mode="json")
    original["risk"]["status"] = "unavailable"
    assert "unavailable" in dict(portfolio_memo(original).sections)["Eligible historical risk"]


def test_worst_case_first_page_is_bounded():
    source = saved()
    source["question"] = "Very long heading " * 100
    source["report"] = "# Thesis\n" + "thesis " * 200 + "\n" + "\n".join("## " + section + "\n" + "word " * 200 for section in ("Valuation", "Risks", "Drivers", "Assumptions"))
    pages = text_pages(pdf_bytes(research_memo(source)))
    assert "Assumptions" in pages[0]
    assert "Full retained narrative" in pages[1]


def test_saved_audited_highlights_keep_amount_period_and_source():
    from test_claim_verification import saved as audited
    memo = research_memo(audited())
    highlight = dict(memo.sections)["Evidence highlights"]
    assert "AAPL" in highlight and "USD" in highlight and "E001" in highlight
    assert "current freshness unassessed" in highlight
    assert highlight.replace("\n", " ") in text_pages(pdf_bytes(memo))[0].replace("\r\n", " ")


def test_oversized_pdf_fails_explicitly_without_truncating_saved_result():
    source = {"report": "x" * 2_000_001}
    with pytest.raises(ValueError, match="retained original"):
        pdf_bytes(research_memo(source))
    from langgraphagenticai.analysis.memo_pdf import deferred_pdf
    with pytest.raises(ValueError, match="retained original"):
        deferred_pdf(research_memo(source))
    assert len(source["report"]) == 2_000_001


def test_session_local_download_reuse_and_later_decision_invalidation(monkeypatch):
    from unittest.mock import Mock
    from streamlit.testing.v1 import AppTest
    from langgraphagenticai.analysis import memo_pdf
    builder = Mock(wraps=memo_pdf.pdf_bytes)
    monkeypatch.setattr(memo_pdf, "pdf_bytes", builder)
    app = AppTest.from_string('''
import streamlit as st
from langgraphagenticai.ui.investment_memo import render_investment_memo
saved = {"report": "Saved thesis"}
if st.checkbox("Later decision"):
    saved["quick_decision"] = {"summary": "New saved decision"}
render_investment_memo(saved)
''', default_timeout=30).run()
    assert not app.exception and builder.call_count == 0
    download = app.session_state["_investment_memo_pdf_research"][1]
    assert callable(download)
    app.run()
    assert builder.call_count == 0
    first = download()
    assert first.startswith(b"%PDF") and builder.call_count == 1
    assert download() == first and builder.call_count == 1
    app.checkbox[0].check().run()
    assert not app.exception and builder.call_count == 1
    updated = app.session_state["_investment_memo_pdf_research"][1]
    assert updated is not download
    assert "New saved decision" in "".join(text_pages(updated()))
    app.run()
    assert builder.call_count == 2


def test_appendix_flow_does_not_split_a_number_at_chunk_boundary():
    memo = research_memo({"report": "x " * 898 + "123456.789 USD end"})
    pages = text_pages(pdf_bytes(memo))
    assert "123456.789 USD" in "".join(pages[1:])
