from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd


def extract_records(payload: Any):
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def to_dataframe(payload: Any) -> pd.DataFrame:
    records = extract_records(payload)
    if isinstance(records, list):
        return pd.DataFrame(records)
    if isinstance(records, dict):
        return pd.DataFrame([records])
    return pd.DataFrame()


def safe_round_df(df: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        try:
            out[col] = pd.to_numeric(out[col], errors="ignore")
        except Exception:
            pass
    return out.round(decimals)


def latest_row(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" in df.columns:
        return df.sort_values("date", ascending=False).head(1)
    return df.head(1)


def latest_n_rows(df: pd.DataFrame, n: int = 4) -> pd.DataFrame:
    if df.empty:
        return df
    if "date" in df.columns:
        return df.sort_values("date", ascending=False).head(n)
    return df.head(n)


def make_tool_response(
    tool_name: str,
    symbol_or_symbols: Any,
    data: Any,
    ok: bool = True,
    error: str | None = None,
) -> Dict[str, Any]:
    key = "symbols" if isinstance(symbol_or_symbols, list) else "symbol"
    return {
        "ok": ok,
        "tool": tool_name,
        key: symbol_or_symbols,
        "data": data,
        "error": error,
    }


def records_to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def compact_numeric(value: Any, decimals: int = 1) -> Any:
    try:
        if value is None or pd.isna(value):
            return None
    except Exception:
        pass

    try:
        x = float(value)
    except Exception:
        return value

    abs_x = abs(x)
    if abs_x >= 1_000_000_000:
        return f"${x / 1_000_000_000:.{decimals}f}B"
    if abs_x >= 1_000_000:
        return f"${x / 1_000_000:.{decimals}f}M"
    if abs_x >= 1_000:
        return f"${x / 1_000:.{decimals}f}K"
    return round(x, decimals)


def compact_percent(value: Any, decimals: int = 1) -> Any:
    try:
        if value is None or pd.isna(value):
            return None
    except Exception:
        pass

    try:
        x = float(value)
    except Exception:
        return value

    if -1.0 <= x <= 1.0:
        x = x * 100.0
    return f"{x:.{decimals}f}%"


def rectangular_rows(rows: List[List[Any]], fill_value: Any = "N/A") -> List[List[Any]]:
    if not rows:
        return rows
    max_len = max(len(r) for r in rows)
    return [list(r) + [fill_value] * (max_len - len(r)) for r in rows]
