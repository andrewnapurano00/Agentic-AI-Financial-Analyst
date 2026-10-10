"""D07-D08: bounded saved narrative excerpts and dedicated safe exports."""
import csv
import io
import json
import math
import re
from dataclasses import asdict
from urllib.parse import urlsplit, urlunsplit, quote
from langgraphagenticai.utils.safety import redact_sensitive_text

TOPICS = {
    "Business drivers": r"business|driver|company overview",
    "Supporting evidence": r"support|bull|investment thesis|executive|valuation",
    "Contrary evidence": r"contrary|counter|bear",
    "Catalysts and stated dates": r"catalyst",
    "Risks": r"risk",
    "Missing information": r"missing|gap|limitation|uncertainty",
    "Thesis invalidation": r"invalidation|invalidate|what would change",
}

def safe_text(value, credentials=(), limit=2000):
    text = str(value or "")
    # Remove complete configured values before any truncation (including encoded forms).
    for credential in sorted({str(c) for c in credentials if c}, key=len, reverse=True):
        for form in {credential, quote(credential, safe=""), json.dumps(credential)[1:-1]}:
            text = text.replace(form, "[REDACTED]")
    text = redact_sensitive_text(text)
    def url(match):
        raw = match.group(0)
        try:
            parts = urlsplit(raw)
            if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                    or re.search(r"[\s\\\x00-\x1f]",parts.netloc)):
                return "[unsafe link removed]"
            parts.port  # Validate malformed/out-of-range ports.
            # No query/fragment survives: arbitrary credentials may use arbitrary parameter names.
            return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        except ValueError:
            return "[unsafe link removed]"
    text = re.sub(r"(?<![A-Za-z0-9])(?:[A-Za-z][A-Za-z0-9+.-]*://|(?:javascript|data|vbscript|file|blob|mailto):)[^\s<>\]\)]+", url, text, flags=re.I)
    text = re.sub(r"<[^>]*>", "", text)
    return text[:limit] + ("\n[excerpt truncated]" if len(text) > limit else "")

def brief(result, credentials=()):
    raw = result.get("report") or result.get("draft") or ""
    sections = []
    heading = ""; lines = []
    for line in str(raw).splitlines():
        found = re.match(r"^\s*#{1,6}\s+(.+)$", line)
        if found:
            sections.append((heading, "\n".join(lines)))
            heading, lines = found.group(1), []
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines)))
    topics = []
    for title, pattern in TOPICS.items():
        selected = [f"{h}\n{body}" for h,body in sections if re.search(pattern,h,re.I) and body.strip()]
        topics.append(dict(topic=title, saved_ai_excerpt=safe_text("\n\n".join(selected), credentials),
                           status="saved excerpt" if selected else "Not present in saved narrative"))
    known = {e.get("id") for e in result.get("evidence", []) if isinstance(e,dict)}
    refs = sorted(set(re.findall(r"\bE\d+\b", str(raw))))
    return dict(label="Saved AI interpretation: heading excerpts, not regenerated or independently verified claims",
                topics=topics, unresolved_evidence_ids=[r for r in refs if r not in known],
                saved_evidence_ids=refs,
                note="Dates are retained only when stated in the saved narrative; absent topics and dates are not inferred.")

def evidence_register(result, credentials=()):
    records=[]
    for e in result.get("evidence",[])[:100]:
        if not isinstance(e,dict):
            continue
        data=e.get('data'); raw=data[0] if isinstance(data,list) and data and isinstance(data[0],dict) else data if isinstance(data,dict) else {}
        url=str(e.get('url') or '')
        try:
            parts=urlsplit(url)
            if parts.scheme not in {'http','https'} or not parts.hostname or parts.username or parts.password or re.search(r'[\s\\\x00-\x1f]',parts.netloc):
                url=''
            else:
                parts.port
                url=urlunsplit((parts.scheme,parts.netloc,parts.path,'',''))
        except ValueError:
            url=''
        records.append(dict(id=e.get('id'),symbol=e.get('symbol'),provider=e.get('provider'),category=e.get('category'),
            retrieved_at=e.get('retrieved_at'),status=e.get('status'),url=url,
            date=raw.get('date'),quote_timestamp=raw.get('timestamp'),period=raw.get('period'),
            currency=raw.get('reportedCurrency') or raw.get('currency'),units=raw.get('units'),
            methodology=raw.get('methodology'),note=e.get('note')))
    return _safe_packet(dict(records=records, omitted_records=max(0,len(result.get('evidence',[]))-100)),credentials)

def _safe_packet(value, credentials, depth=0):
    if depth > 12:
        return "[nested content omitted]"
    if isinstance(value,dict):
        return {safe_text(k,credentials,150): _safe_packet(v,credentials,depth+1) for k,v in list(value.items())[:100]
                if not any(s in str(k).lower() for s in ("password","secret","token","api_key","apikey"))}
    if isinstance(value,(list,tuple)):
        return [_safe_packet(v,credentials,depth+1) for v in value[:100]]
    if isinstance(value,str):
        return safe_text(value,credentials,4000)
    if isinstance(value,float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value,(int,bool)):
        return value
    return safe_text(value,credentials)

def export_packet(result, inputs, scenarios, credentials=()):
    packet = _safe_packet(dict(schema="axiom-saved-brief-v1", result_id=result.get("id"), brief=brief(result,credentials),
        saved_evidence=evidence_register(result,credentials),
        inputs=asdict(inputs), scenarios=scenarios,
        formulas={"equity_value":"saved TTM net income * (1 + user earnings change percent / 100) * user P/E",
                  "difference":"(hypothetical equity value / saved market capitalization - 1) * 100"},
        labels=["Provider facts", "Calculated audited TTM", "Saved AI interpretation", "User assumptions", "Calculated hypothetical sensitivity"]),credentials)
    # Prefer retaining the brief and model audit; large source appendices disclose omissions.
    records=packet['saved_evidence']['records']
    while records and len(json.dumps(packet,ensure_ascii=False,allow_nan=False).encode('utf-8')) > 240000:
        records.pop()
        packet['saved_evidence']['omitted_records']+=1
    return packet

def exports(packet):
    """JSON and long-form CSV carry identical safe packet content, bounded to 300KB."""
    encoded = json.dumps(packet,ensure_ascii=False,allow_nan=False)
    if len(encoded.encode("utf-8")) > 300000:
        raise ValueError("Brief export exceeds its 300KB budget.")
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["path","value"])
    def cell(v):
        if isinstance(v,str) and v.lstrip().startswith(("=","+","-","@")):
            return "'"+v
        return v
    def flatten(value,path=""):
        if isinstance(value,dict):
            for k,v in value.items(): flatten(v,f"{path}.{k}" if path else k)
        elif isinstance(value,list):
            for i,v in enumerate(value): flatten(v,f"{path}[{i}]")
        else:
            writer.writerow([cell(path),cell(value)])
    flatten(packet)
    if len(output.getvalue().encode('utf-8')) > 300000:
        raise ValueError("Brief CSV exceeds its 300KB budget.")
    return encoded, output.getvalue()
