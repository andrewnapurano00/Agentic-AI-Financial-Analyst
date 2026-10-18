"""CSV serialization for user/provider text in downloadable tables."""

import pandas as pd

from langgraphagenticai.utils.safety import redact_sensitive_text, redact_value


def _safe_text_cell(value):
    if isinstance(value, (dict, list, tuple)):
        value = str(redact_value(value))
    if not isinstance(value, str):
        return value
    text = redact_sensitive_text(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def safe_spreadsheet_text_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy provider/user text and labels with credential and formula protection."""
    clean = frame.copy()
    for column in clean.select_dtypes(include=["object", "string", "category"]).columns:
        clean[column] = clean[column].map(_safe_text_cell)
    clean.columns = [_safe_text_cell(label) for label in clean.columns]
    return clean


def safe_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Keep numeric columns numeric while making textual spreadsheet cells inert."""
    return safe_spreadsheet_text_frame(frame).to_csv(index=False).encode("utf-8")
