"""Allowlisted saved recommendation exports; no calls, raw prompts or credentials."""
import json
import re
from html import escape
import pandas as pd
from langgraphagenticai.utils.export_csv import safe_csv_bytes
from langgraphagenticai.utils.safety import redact_sensitive_text


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


def allocation_rows(result):
    return [{"Ticker":h.ticker,"Company/fund":h.name,"Sector/category":h.sector,"Weight %":h.weight*100,
             "Hypothetical USD":h.dollars,"Conviction (subjective)":h.conviction,"Sizing":h.sizing,
             "Evidence IDs":"; ".join(h.citations)} for h in result.holdings] + [
                 {"Ticker":"CASH","Company/fund":"Cash (zero return assumption)","Sector/category":"Cash",
                  "Weight %":result.cash*100,"Hypothetical USD":result.cash_dollars,"Conviction (subjective)":"N/A",
                  "Sizing":"Cash target / budget residual","Evidence IDs":""}]


def json_bytes(result, credentials=()):
    encoded = json.dumps(export_payload(result, credentials),ensure_ascii=False,allow_nan=False,indent=2).encode()
    if len(encoded) > 4000000:
        raise ValueError("Export exceeds four-megabyte budget.")
    return encoded


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
             '<body><h1>AI Portfolio Architect</h1>',f'<p>{escape(p["snapshot"]["mode"])} · Research only · {escape(p["snapshot"]["retrieved_at"])}</p>',
             pd.DataFrame(rows).to_html(index=False,escape=True), '<h2>Committee review and provenance</h2>',
             '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+escape(json.dumps(p,ensure_ascii=False,indent=2))+'</pre></body></html>']
    return ''.join(parts).encode()
