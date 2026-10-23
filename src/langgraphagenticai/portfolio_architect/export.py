"""Allowlisted saved recommendation exports; no calls, raw prompts or credentials."""
import json
import gzip
import re
from html import escape
import pandas as pd
from langgraphagenticai.utils.export_csv import safe_csv_bytes
from langgraphagenticai.utils.safety import redact_sensitive_text


EXPORT_BYTE_LIMIT = 4_000_000


class ExportSizeError(ValueError):
    """Saved evidence cannot fit the bounded download; keep the report available."""


def scrub(value, credentials=()):
    if isinstance(value, dict):
        return {k:scrub(v,credentials) for k,v in value.items()}
    if isinstance(value, list):
        return [scrub(v,credentials) for v in value]
    if isinstance(value, str):
        for key in credentials:
            if key:
                value = value.replace(key,"[REDACTED]")
        value = redact_sensitive_text(value)
        # Reports need no provider/content URLs. Prevent credential query strings and active links.
        return re.sub(r"https?://\S+", "[URL omitted]", value)
    return value


def export_payload(result, credentials=()):
    payload = result.model_dump(mode="json")
    payload["mandate"].pop("objective", None)  # Do not export the raw user prompt.
    return scrub(payload, credentials)


def conviction_text(holding):
    if not holding.ai_analysis or holding.conviction == "not AI rated":
        return "Not AI rated - no validated AI rationale."
    summary = holding.ai_analysis.get("conviction_summary") or holding.ai_analysis.get("thesis", "")
    summary = " ".join(str(summary).split())
    if len(summary) > 180:
        summary = summary[:177].rsplit(" ",1)[0]+"..."
    return holding.conviction.capitalize()+" - "+summary


def allocation_rows(result):
    return [{"Ticker":h.ticker,"Company/fund":h.name,"Sector/category":h.sector,"Weight %":h.weight*100,
             "Hypothetical USD":h.dollars,"Conviction (subjective)":conviction_text(h),"Sizing":h.sizing,
             "Evidence IDs":"; ".join(h.citations)} for h in result.holdings] + [
                 {"Ticker":"CASH","Company/fund":"Cash (zero return assumption)","Sector/category":"Cash",
                  "Weight %":result.cash*100,"Hypothetical USD":result.cash_dollars,"Conviction (subjective)":"N/A",
                  "Sizing":"Cash target / budget residual","Evidence IDs":""}]


def _encoded_json(result, credentials=()):
    payload = export_payload(result, credentials)
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
    if len(encoded) > EXPORT_BYTE_LIMIT:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    return encoded


def json_bytes(result, credentials=()):
    encoded = _encoded_json(result, credentials)
    if len(encoded) > EXPORT_BYTE_LIMIT:
        raise ExportSizeError("JSON exceeds the download budget; use compressed evidence JSON.")
    return encoded


def evidence_download(result, credentials=()):
    """Keep full sanitized evidence; compress large packets without dropping records."""
    encoded = _encoded_json(result, credentials)
    if len(encoded) <= EXPORT_BYTE_LIMIT:
        return encoded, "portfolio_architect.json", "application/json"
    compressed = gzip.compress(encoded, mtime=0)
    if len(compressed) > EXPORT_BYTE_LIMIT:
        raise ExportSizeError("Evidence JSON is unavailable: even compressed evidence exceeds the four-megabyte download budget. Your saved report, allocation CSV and Research HTML remain available.")
    return compressed, "portfolio_architect.json.gz", "application/gzip"


def csv_bytes(result, credentials=()):
    frame = pd.DataFrame(scrub(allocation_rows(result), credentials))
    frame["Mode"] = result.snapshot.mode
    frame["Snapshot ID"] = result.snapshot.id
    frame["Quote retrieval UTC"] = result.snapshot.retrieved_at
    return safe_csv_bytes(frame)


def html_bytes(result, credentials=()):
    p = export_payload(result, credentials)
    rows = scrub(allocation_rows(result), credentials)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>AI Portfolio Architect</title>',
             '<body><h1>AI Portfolio Architect</h1>',f'<p>{escape(p["snapshot"]["mode"])} Â· Research only Â· {escape(p["snapshot"]["retrieved_at"])}</p>',
             pd.DataFrame(rows).to_html(index=False,escape=True), '<h2>Committee review and provenance</h2>',
             '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+escape(json.dumps(p,ensure_ascii=False,indent=2))+'</pre></body></html>']
    return ''.join(parts).encode()
