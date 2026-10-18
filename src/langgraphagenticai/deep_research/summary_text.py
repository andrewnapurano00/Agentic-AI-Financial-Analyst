"""Remove provenance prose from executive presentation, preserving saved evidence."""
import re

STATEMENT = r"(?:(?:annual|quarterly|audited|reported|TTM)\s+)*(?:income[ _-]statements?|balance[ _-]sheets?(?:[ _-]statements?)?|cash[ _-]flow[ _-]statements?|financial[ _-]statements?|annual reports?|form\s+10-[KQ])"
REFERENCE = rf"(?:{STATEMENT}|\bE\d{{3}}\b|source\s*(?:IDs?|references?)|evidence\s*(?:IDs?|references?)|\bFMP\b|(?:income|balance|cash_flow)_(?:ttm|quarterly|annual))"


def clean_summary_references(value):
    text = str(value or "")
    # References disappear; useful dates, amounts and business qualifiers stay.
    def link(match):
        return "" if re.search(REFERENCE, match[1], re.I) else match[1]
    text = re.sub(r"\[([^]\n]+)\]\(https?://[^)]+\)", link, text)
    text = re.sub(r"\[([^]\n]+)\]", lambda m: "" if re.search(REFERENCE, m[1], re.I) else m[0], text)
    text = re.sub(r"\(([^()\n]+)\)", lambda m: "" if re.search(REFERENCE, m[1], re.I) else m[0], text)
    text = re.sub(r"(?im)^\s*(?:statement (?:references?|date|period|basis|currency)|data sources?|methodology|calculation basis|source fields?)\s*:[^\n]*", "", text)
    attribution = rf"(?:according to|based on|as (?:shown|reported|disclosed) in|per)\s+(?:the\s+)?(?:FMP(?:'s)?\s+)?{STATEMENT}(?:\s+for\s+(?:FY\s*)?20\d{{2}})?\s*[,;:]?\s*"
    def remove_attribution(pattern, value):
        def replace(match):
            first = match["initial"]
            prefix = match.string[:match.start()].rstrip()
            return first.upper() if not prefix or prefix[-1] in ".!?" else first
        value = re.sub(pattern + r"(?P<initial>[A-Za-z])", replace, value, flags=re.I)
        return re.sub(pattern, "", value, flags=re.I)
    text = remove_attribution(attribution, text)
    text = remove_attribution(rf"(?:the\s+)?{STATEMENT}\s+(?:shows?|reports?|indicates?|reveals?|suggests?|confirms?|highlights?)\s+(?:that\s+)?", text)
    # Older saved memos may name a statement without an attribution verb.
    # Use business language, keeping the surrounding dates, amounts and caveats.
    for pattern, replacement in (
        (r"\b(?:income|profit[ -]and[ -]loss)[ _-]statements?\b", "operating performance"),
        (r"\bcash[ _-]flow[ _-]statements?\b", "cash generation"),
        (r"\bbalance[ _-]sheets?(?:[ _-]statements?)?\b", "financial position"),
        (r"\bfinancial[ _-]statements?\b", "financial results"),
    ):
        text = re.sub(pattern, replacement, text, flags=re.I)
    text = re.sub(r"\b(?:income|balance|cash_flow)_(?:ttm|quarterly|annual)(?:\.[A-Za-z_]+)?\b", "", text, flags=re.I)
    text = re.sub(r"https?://\S+|\bE\d{3}\b", "", text)
    text = re.sub(r"[ \t]+([,.;:])", r"\1", re.sub(r"[ \t]{2,}", " ", text))
    return text.strip()
