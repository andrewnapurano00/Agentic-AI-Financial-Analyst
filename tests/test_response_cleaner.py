from langgraphagenticai.utils.response_cleaner import clean_financial_text


def test_research_sections_become_markdown_headings():
    raw = (
        "Overview: Acme rallied on earnings. "
        "Key Findings: Revenue grew 18 %. Risks: Valuation is elevated. "
        "Bottom Line: Momentum remains positive."
    )

    cleaned = clean_financial_text(raw)

    assert cleaned.startswith("### Overview\n")
    assert "\n### Key Findings\n" in cleaned
    assert "\n### Risks\n" in cleaned
    assert "\n### Bottom Line\n" in cleaned
    assert "18%" in cleaned


def test_research_bullets_and_numbered_sections_are_normalized():
    raw = "1. Price performance: Up strongly\n\u2022 Volume expanded\n\u2014 News sentiment improved"

    cleaned = clean_financial_text(raw)

    assert cleaned.startswith("### Price performance\n")
    assert "- Volume expanded" in cleaned
    assert "- News sentiment improved" in cleaned


def test_existing_markdown_heading_is_not_duplicated():
    cleaned = clean_financial_text("## Overview\nBusiness remains resilient.")

    assert cleaned == "### Overview\nBusiness remains resilient."
