from __future__ import annotations
import io
import pdfplumber
import pandas as pd
from langgraphagenticai.ui.equity_report_tab import generate_story_pdf_report


def test_complete_summary_and_debate_export_are_paginated_safe_and_immutable(tmp_path):
    summary = "Full saved summary & valuation < 20. " * 100 + "SUMMARY_END"
    note = "Saved research and evidence. " * 180 + "NOTE_END"
    decision = dict(verdict="WATCH", best_buy="NVDA", confidence=65,
                    summary="Saved committee conclusion", debate_summary="DEBATE_END",
                    runner_up="GOOGL", created_at="2026-10-24", model="synthetic",
                    input_fingerprint="saved-fingerprint",
                    specialist_views=[dict(role="risk", preferred_ticker=None,
                                           argument="RISK_END", challenges=["CHALLENGE_END"])],
                    catalysts=["CATALYST_END"], risks=["RISK_LIST_END"],
                    invalidation_signals=["INVALIDATION_END"],
                    evidence_limitations=["LIMITATION_END", "https://example.test/?apikey=private-test-key"],
                    disclaimer="Research opinion")
    original = dict(decision)
    data = generate_story_pdf_report(pd.DataFrame(), {}, ["NVDA", "GOOGL"],
              summary, note + " secret-known-value <link href='javascript:bad'>text</link>",
              "Technology", committee=decision, generated_at="2026-10-24", secrets=("secret-known-value",))
    (tmp_path / "equity-complete.pdf").write_bytes(data)
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        assert len(pdf.pages) >= 3
        text = " ".join(page.extract_text() or "" for page in pdf.pages)
        assert all(token in text for token in ["SUMMARY_END", "NOTE_END", "DEBATE_END", "RISK_END",
            "CHALLENGE_END", "CATALYST_END", "INVALIDATION_END", "LIMITATION_END", "saved-fingerprint"])
        assert "private-test-key" not in text and "secret-known-value" not in text
        assert not any(page.hyperlinks for page in pdf.pages)
    assert decision == original


def test_missing_decision_is_explicit_without_fabricating_verdict():
    data = generate_story_pdf_report(pd.DataFrame(), {}, ["NVDA"], "Saved summary", None, "Technology")
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = " ".join(page.extract_text() or "" for page in pdf.pages)
    assert "No completed CrewAI decision matches" in text
    assert "Saved summary" in text


def test_executive_pdf_uses_portrait_formatted_summary_without_metrics(monkeypatch):
    from langgraphagenticai.ui import equity_report_tab as ui
    def forbidden(*args, **kwargs):
        raise AssertionError("PDF must not build a metrics table")
    monkeypatch.setattr(ui, "_one_page_pdf_rows", forbidden)
    data = ui.generate_story_pdf_report(
        pd.DataFrame([{"Ticker": "NVDA", "Metric": "EXCLUDED_METRIC"}]),
        {"Profile": pd.DataFrame([{"Metric": "EXCLUDED_METRIC"}])}, ["NVDA"],
        "Saved executive thesis.",
        "## Analyst conclusion\n**NVDA:** Strong cash generation.\n- Monitor valuation.\n**Biggest risks**\nGrowth may normalize.\nAnalyst Conclusion:\nNVDA: Plain saved ticker line.",
        "Technology")
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = " ".join(page.extract_text() or "" for page in pdf.pages)
        assert all(page.width == 612 and page.height == 792 for page in pdf.pages)
        assert "EXECUTIVE EQUITY BRIEF" in text and "Analyst conclusion" in text
        assert "Strong cash generation" in text and "Biggest risks" in text
        assert "EXCLUDED_METRIC" not in text and "Saved comparison metrics" not in text
        assert "**" not in text and "##" not in text
        heading_chars = [char for page in pdf.pages for char in page.chars if char.get("size", 0) == 10]
        assert heading_chars and all("Bold" in char["fontname"] for char in heading_chars)
