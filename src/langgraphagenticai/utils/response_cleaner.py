from __future__ import annotations

import re


SECTION_LABELS = [
    "Executive Summary",
    "Fundamentals",
    "Fundamentals snapshot",
    "Analyst expectations",
    "Valuation",
    "Valuation and DCF",
    "Ratings",
    "Ratings and targets",
    "Risks",
    "Risks / Watch items",
    "Key drivers",
    "Key drivers and risks",
    "Bottom Line",
    "Conclusion",
    "Investment view",
    "Recommendation",
]


def _normalize_approx_currency(text: str) -> str:
    """
    Convert markdown-dangerous approximate currency syntax.

    Streamlit/Markdown can interpret:
        ~$26.6B ... ~$0.8B

    as strikethrough. Convert to:
        approx. $26.6B
    """
    if not text:
        return ""

    out = text

    # Convert "~$215.9B" / "~ $215.9B" to "approx. $215.9B"
    out = re.sub(
        r"(?<!\w)~\s*\$",
        "approx. $",
        out,
    )

    # Convert "~208" when used as approximate numeric reference.
    out = re.sub(
        r"(?<!\w)~(?=\d)",
        "approx. ",
        out,
    )

    return out


def _escape_markdown_dollars(text: str) -> str:
    """
    Escape dollar signs so Streamlit/Markdown does not interpret finance text
    like $215.9B or $4.69 as LaTeX math.
    """
    if not text:
        return ""

    # Escape $ only when it is not already escaped.
    return re.sub(r"(?<!\\)\$", r"\\$", text)


def _normalize_currency_spacing(text: str) -> str:
    """
    Clean common finance/currency spacing issues without creating Markdown math.
    """
    if not text:
        return ""

    out = text

    # Fix "$ 215.9B" -> "$215.9B" before escaping.
    out = re.sub(r"\$\s+(\d)", r"$\1", out)

    # Fix "USD$215.9B" / "USD $215.9B" -> "$215.9B"
    out = re.sub(r"\bUSD\s*\$\s*", "$", out, flags=re.IGNORECASE)

    # Normalize units only when a dollar sign is already present.
    out = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*B\b", r"$\1B", out)
    out = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*M\b", r"$\1M", out)
    out = re.sub(r"\$\s*(\d+(?:\.\d+)?)\s*K\b", r"$\1K", out)

    return out


def _clean_markdown_artifacts(text: str) -> str:
    """
    Remove Markdown artifacts that commonly damage finance output.
    """
    if not text:
        return ""

    out = text

    # Remove accidental strikethrough markers.
    out = out.replace("~~", "")

    # Normalize markdown emphasis around financial terms if the model overuses it.
    out = re.sub(r"\*\*(\s*)", r"**", out)
    out = re.sub(r"(\s*)\*\*", r"**", out)

    return out


def _format_section_headers(text: str) -> str:
    """
    Convert inline section labels into cleaner Markdown section headers.

    Example:
        Analyst expectations Street models continued...
    becomes:
        **Analyst expectations**

        Street models continued...
    """
    if not text:
        return ""

    out = text

    for label in sorted(SECTION_LABELS, key=len, reverse=True):
        escaped = re.escape(label)

        # At beginning of text
        out = re.sub(
            rf"^{escaped}\s+",
            rf"**{label}**\n\n",
            out,
            flags=re.IGNORECASE,
        )

        # At beginning of a new paragraph or line
        out = re.sub(
            rf"\n{escaped}\s+",
            rf"\n\n**{label}**\n\n",
            out,
            flags=re.IGNORECASE,
        )

    return out


def clean_financial_text(text: str) -> str:
    """
    Clean AI finance responses before rendering in Streamlit.

    Fixes:
    - Prevents $ values from rendering as LaTeX.
    - Prevents ~$ approximate values from rendering as strikethrough.
    - Normalizes bullets and spacing.
    - Makes common section labels cleaner.
    """
    if text is None:
        return ""

    out = str(text).strip()

    if not out:
        return ""

    # Normalize Windows/newline oddities.
    out = out.replace("\r\n", "\n").replace("\r", "\n")

    # Remove/clean problematic markdown artifacts.
    out = _clean_markdown_artifacts(out)

    # Convert approximate currency before dollar escaping.
    out = _normalize_approx_currency(out)

    # Normalize finance/currency formatting before escaping dollar signs.
    out = _normalize_currency_spacing(out)

    # Normalize whitespace without destroying Markdown line breaks.
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)

    # Normalize bullet styles.
    out = re.sub(r"\n\s*•\s*", "\n- ", out)
    out = re.sub(r"^\s*•\s*", "- ", out)

    # Normalize percentages.
    out = re.sub(r"(\d+(?:\.\d+)?)\s+%", r"\1%", out)

    # Clean punctuation spacing.
    out = re.sub(r"[ ]*:[ ]*", ": ", out)
    out = re.sub(r"\(\+", "(+", out)
    out = re.sub(r"\s+\)", ")", out)
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r"\s+\.", ".", out)

    # Fix common finance spacing artifacts.
    out = re.sub(r"\bP\s*/\s*E\b", "P/E", out, flags=re.IGNORECASE)
    out = re.sub(r"\bP\s*/\s*S\b", "P/S", out, flags=re.IGNORECASE)
    out = re.sub(r"\bP\s*/\s*FCF\b", "P/FCF", out, flags=re.IGNORECASE)
    out = re.sub(r"\bEV\s*/\s*EBITDA\b", "EV/EBITDA", out, flags=re.IGNORECASE)
    out = re.sub(r"\bEV\s*/\s*Sales\b", "EV/Sales", out, flags=re.IGNORECASE)
    out = re.sub(r"\bDCF\s*S\b", "DCFs", out, flags=re.IGNORECASE)

    # Improve section readability.
    out = _format_section_headers(out)

    # Escape dollar signs so Streamlit does not render finance values as LaTeX.
    out = _escape_markdown_dollars(out)

    # Remove excessive blank lines after formatting.
    out = re.sub(r"\n{3,}", "\n\n", out)

    # Remove trailing spaces line by line.
    lines = [line.rstrip() for line in out.splitlines()]
    out = "\n".join(lines).strip()

    return out


def sanitize_ai_markdown(text: str) -> str:
    """
    Backward-compatible alias.
    """
    return clean_financial_text(text)