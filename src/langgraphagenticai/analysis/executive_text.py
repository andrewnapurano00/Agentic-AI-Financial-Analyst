"""Reader-facing prose; saved evidence and validation stay intact."""
import re
from langgraphagenticai.deep_research.executive import executive_prose
from langgraphagenticai.utils.safety import redact_sensitive_text


def executive_text(value):
    text = executive_prose(redact_sensitive_text(value))
    text = re.sub(r"\[\s*(?:[NTE]\d+|\d+)(?:\s*[,;]\s*(?:[NTE]\d+|\d+))*\s*\]", "", text)
    text = re.sub(r"\b(?:according to|as reported by|as noted by)\s+(?:the\s+)?(?:supplied\s+)?(?:sources?|coverage|data|articles?|reports?)\s*[,;:]?\s*", "", text, flags=re.I)
    text = re.sub(r"\b(?:provider[- ](?:reported\s+)?|FMP\s+|Marketaux\s+|Serper\s+)", "", text, flags=re.I)
    text = re.sub(r"\b(?:source|reference|citation)\s*#?\s*\d+\b", "", text, flags=re.I)
    text = re.sub(r"[\[(][A-Z0-9.^-]{1,16}[:.][A-Za-z_][\w .:/,-]*[\])]", "", text)
    return re.sub(r"\s+([,.;:])", r"\1", text).strip()
