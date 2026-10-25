"""Bounded report checks against saved facts, never an LLM fact-check or rewrite."""
from datetime import datetime, timezone, date
import hashlib
import json
import math
import re
from pydantic import BaseModel, ConfigDict, Field
from .earnings_metrics import research_net_income, instant, safe_route
from langgraphagenticai.deep_research.quarterly_ttm import aggregate
from langgraphagenticai.utils.safety import redact_sensitive_text

MAX_TEXT = 60000
MAX_CLAIMS = 100


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    text: str = Field(max_length=4000)
    kind: str = "fact"
    ticker: str = ""
    metric: str = "unsupported"
    value: float | None = None
    scale: float = 1.
    unit: str = ""
    currency: str | None = None
    basis: str = ""
    period_end: str = ""
    earnings_end: str = ""
    prior_end: str = ""
    citations: list[str] = Field(default_factory=list, max_length=20)


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    ticker: str
    metric: str
    value: float | None
    unit: str
    currency: str | None
    basis: str
    period_end: str
    citations: list[str]
    status: str
    sources: list[dict]
    origin: str


def saved_facts(saved, reference):
    """AX-04 validates raw quarters and reconciles saved TTM; no inferred currency."""
    facts = []
    records = saved.get("evidence") or []
    ids = [e.get("id") for e in records if isinstance(e, dict)]
    if len(ids) != len(records) or any(not i for i in ids) or len(set(ids)) != len(ids):
        return [], ["Evidence register has malformed, missing or duplicate identifiers."]
    gaps = []
    for ticker in saved.get("request", {}).get("symbols", [])[:4]:
        if not isinstance(ticker, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,14}", ticker):
            continue
        for basis in ("quarterly", "annual", "TTM"):
            obs = research_net_income(saved, ticker, basis=basis, reference_time=reference)
            citations = sorted({i.source_id for i in obs.inputs})
            if basis == "TTM":
                citations += [e["id"] for e in records if e.get("symbol") == ticker and e.get("category") == "income_ttm"]
            facts.append(Fact(ticker=ticker, metric="net_income", value=obs.value, unit="currency", currency=obs.currency,
                basis=basis, period_end=obs.as_of or "", citations=citations, status=obs.status,
                sources=[{"id":i.source_id,"provider":i.provider,"route":i.route,"retrieved_at":i.retrieved_at,
                          "field":i.field,"value":i.value,"fiscal_year":i.fiscal_year,"period":i.period,"date":i.period_end} for i in obs.inputs], origin=obs.origin))
            if basis == "TTM" and obs.inputs and obs.status in {"available", "stale"}:
                # Reuse the validated fiscal window, not the saved derived revenue amount.
                raw_ids = {i.source_id for i in obs.inputs}
                raw = [e for e in records if e["id"] in raw_ids]
                if len(raw) == 1:
                    recomputed = aggregate(raw[0]["data"], ticker, ("revenue",))
                    revenue = recomputed.get("revenue")
                    revenue_ids = sorted(raw_ids)
                    for record in records:
                        if record.get("symbol") == ticker and record.get("category") == "income_ttm" and record.get("status") == "ok":
                            data = record.get("data")
                            if (isinstance(data, list) and len(data) == 1 and data[0].get("revenue") == revenue
                                    and data[0].get("date") == obs.as_of and data[0].get("reportedCurrency") == obs.currency):
                                revenue_ids.append(record["id"])
                    facts.append(Fact(ticker=ticker,metric="revenue",value=revenue,unit="currency",currency=obs.currency,
                        basis="TTM",period_end=obs.as_of or "",citations=revenue_ids,status=obs.status if revenue is not None else "missing",
                        sources=[{**source,"field":"revenue","value":next((q.get("revenue") for q in raw[0]["data"] if q.get("date") == source["date"]), None)} for source in facts[-1].sources],origin="derived"))
        quotes = [e for e in records if e.get("symbol") == ticker and e.get("category") == "quote"]
        if len(quotes) != 1 or quotes[0].get("status") != "ok":
            gaps.append(ticker+": unique successful quote unavailable.")
            continue
        e = quotes[0]
        data = e.get("data"); rows = data if isinstance(data, list) else [data]
        if len(rows) != 1 or not isinstance(rows[0], dict):
            gaps.append(ticker+": quote identity ambiguous.")
            continue
        row = rows[0]
        for metric, field in (("price", "price"), ("market_cap", "marketCap")):
            status = "available"
            try:
                amount = row.get(field)
                if (row.get("symbol") != ticker or isinstance(amount, bool) or not isinstance(amount, (int,float))
                        or not math.isfinite(amount) or amount <= 0 or not re.fullmatch(r"[A-Z]{3}", str(row.get("currency") or ""))
                        or not e.get("provider") or not safe_route(e.get("url"))):
                    raise ValueError("Quote source/amount/currency unavailable")
                stamp = datetime.fromtimestamp(float(row["timestamp"]), timezone.utc).isoformat()
                when = instant(stamp); retrieved = instant(e.get("retrieved_at")); now = instant(reference)
                if when > retrieved or retrieved > now:
                    status = "inconsistent"
                elif (now-retrieved).total_seconds() > 86400 or (now-when).total_seconds() > 7*86400:
                    status = "stale"
                facts.append(Fact(ticker=ticker,metric=metric,value=amount,unit="currency/share" if metric == "price" else "currency",currency=row["currency"],basis="point_in_time",
                    period_end=when.date().isoformat(),citations=[e["id"]],status=status,origin="provider",
                    sources=[{"id":e["id"],"provider":e["provider"],"route":safe_route(e["url"]),"retrieved_at":e["retrieved_at"],"as_of":stamp,"field":field}]))
            except (ValueError, TypeError, OverflowError, OSError):
                gaps.append(ticker+": "+metric+" source/time/currency unverifiable.")
    return facts, gaps


def extract_claims(report):
    """Only full, explicit supported sentences earn numeric checks; no semantic guessing."""
    claims = []
    text = str(report or "")
    lines = text[:MAX_TEXT].splitlines()
    numeric_lines = [line for line in lines if re.search(r"\d", line) and not re.fullmatch(r"\s*#{1,6}.*", line)]
    number = r"(?P<value>[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    money = re.compile(r"(?P<ticker>[A-Z0-9][A-Z0-9.\-]{0,14}) (?:(?P<basis>TTM|annual|quarterly) (?P<metric>net income|revenue)|(?P<spot>price|market cap)) (?:was|is|:) (?P<currency>[A-Z]{3}) "+number+r"(?: (?P<scale>thousand|million|billion))? (?:as of|through) (?P<end>\d{4}-\d{2}-\d{2}) (?P<refs>\[E\d+(?:[,; ]+E\d+)*\])\.?", re.I)
    pe = re.compile(r"(?P<ticker>[A-Z0-9][A-Z0-9.\-]{0,14}) P/E (?:was|is|:) "+number+r"x as of (?P<end>\d{4}-\d{2}-\d{2}) using TTM earnings through (?P<earnings>\d{4}-\d{2}-\d{2}) (?P<currency>[A-Z]{3}) (?P<refs>\[E\d+(?:[,; ]+E\d+)*\])\.?", re.I)
    for line in numeric_lines[:MAX_CLAIMS]:
        clean = re.sub(r"^\s*[-*]\s+", "", line).strip()
        claim = Claim(text=redact_sensitive_text(line, max_length=4000), citations=re.findall(r"\bE\d+\b", clean)[:20])
        match = money.fullmatch(clean) or pe.fullmatch(clean)
        if match:
            v = match.groupdict()
            claim.ticker = v["ticker"].upper(); claim.currency = v["currency"].upper()
            claim.value = float(v["value"].replace(",", "")); claim.period_end = v["end"]
            if "earnings" in v:
                claim.metric = "pe"; claim.kind = "ratio"; claim.unit = "multiple"; claim.basis = "TTM"; claim.earnings_end = v["earnings"]
            else:
                claim.metric = (v.get("metric") or v.get("spot")).lower().replace(" ", "_")
                claim.basis = "point_in_time" if v.get("spot") else "TTM" if v["basis"].upper() == "TTM" else v["basis"].lower()
                claim.unit = "currency/share" if claim.metric == "price" else "currency"; claim.scale = {None:1.,"thousand":1e3,"million":1e6,"billion":1e9}[v.get("scale").lower() if v.get("scale") else None]
        elif re.search(r"\b(target|forecast|assum(?:e|ption)|expect|could|opinion)\b", clean, re.I):
            claim.kind = "price_target" if re.search(r"\btarget\b",clean,re.I) else "opinion"
        claims.append(claim)
    return claims, {"numeric_lines_seen":len(numeric_lines),"omitted_numeric_lines":max(0,len(numeric_lines)-MAX_CLAIMS),
                    "text_truncated":len(text)>MAX_TEXT}


def verify_claim(claim, facts):
    def outcome(label, code, hint, expected=None, evidence=()):
        return {"claim":claim.model_dump(),"label":label,"code":code,"severity":"error" if label == "contradicted" else "info" if label in {"verified numerical fact","derived calculation","assumption/opinion"} else "warning",
                "remediation":hint,"expected":expected,"sources":[s for f in evidence for s in f.sources]}
    if claim.kind in {"opinion","assumption","price_target"}:
        return outcome("assumption/opinion","interpretation", "Future targets and subjective views are not verified facts; retain their assumptions and uncertainty.")
    if not claim.citations:
        return outcome("unverifiable","missing_citation","Add exact supporting saved evidence IDs; a URL alone is insufficient.")
    if claim.value is None or claim.metric == "unsupported" or claim.kind not in {"fact","ratio","growth"}:
        return outcome("unverifiable","unsupported_expression","Provide explicit ticker, metric, amount, currency/unit, period and citation; no prose semantics inferred.")
    if claim.scale not in {1.,1e3,1e6,1e9} or not math.isfinite(claim.value*claim.scale):
        return outcome("unverifiable","invalid_scale","Use explicit supported finite scaling.")
    needs = [(claim.metric,claim.basis,claim.period_end)]
    if claim.metric == "pe" and claim.kind == "ratio":
        needs = [("market_cap","point_in_time",claim.period_end),("net_income","TTM",claim.earnings_end)]
    elif claim.kind == "growth":
        needs += [(claim.metric,claim.basis,claim.prior_end)]
    elif claim.kind != "fact":
        return outcome("unverifiable","unsupported_formula","Only P/E and matched annual earnings growth have supported calculation meanings.")
    selected = []
    for metric,basis,end in needs:
        candidates = [f for f in facts if f.ticker == claim.ticker and f.metric == metric]
        if not candidates:
            return outcome("unverifiable","unsupported_metric","No independently validated saved observation supports this metric/ticker.")
        matches = [f for f in candidates if f.basis == basis and f.period_end == end]
        if len(matches) != 1:
            # Only contradict when the cited source actually resolves to another period.
            cited = [f for f in candidates if set(claim.citations)&set(f.citations) and f.value is not None and f.status == "available"]
            return outcome("contradicted" if cited else "unverifiable","period_mismatch","Check exact fiscal/quote date and annual/quarterly/TTM basis; no period substitution.")
        selected.append(matches[0])
    known = set().union(*(set(f.citations) for f in selected))
    if not set(claim.citations) <= known or any(not set(f.citations)&set(claim.citations) for f in selected):
        return outcome("unverifiable","citation_mismatch","Use citations resolving to every required observation; unknown, irrelevant and cross-company IDs do not count.")
    if any(f.status != "available" or f.value is None or not f.sources for f in selected):
        return outcome("unverifiable","ineligible_evidence","Resolve stale, missing, inconsistent or unavailable source evidence; retain original text.",evidence=selected)
    if not claim.currency or any(f.currency != claim.currency for f in selected):
        return outcome("contradicted","currency_mismatch","Use source-reported compatible currencies; no inferred FX conversion.",evidence=selected)
    expected = selected[0].value
    if claim.metric == "pe":
        if claim.unit != "multiple" or claim.scale != 1 or selected[1].value <= 0 or selected[0].period_end < selected[1].period_end:
            return outcome("unverifiable","invalid_multiple","P/E requires positive company earnings, compatible dated market cap and unit multiple.",evidence=selected)
        expected /= selected[1].value
    elif claim.kind == "growth":
        try:
            days = (date.fromisoformat(claim.period_end)-date.fromisoformat(claim.prior_end)).days
        except ValueError:
            days = 0
        if claim.basis != "annual" or not 340 <= days <= 390 or selected[1].value <= 0 or claim.unit != "percent" or claim.scale != 1:
            return outcome("unverifiable","invalid_comparison","Growth requires comparable annual periods and a positive prior amount; percent is percentage points.",evidence=selected)
        expected = (expected/selected[1].value-1)*100
    elif claim.unit != selected[0].unit:
        return outcome("contradicted","unit_mismatch","Check monetary units and scaling; zero is distinct from missing.",evidence=selected)
    # Strict reproducibility tolerance, not a materiality or fuzzy semantic threshold.
    if not math.isclose(claim.value*claim.scale, expected, rel_tol=1e-9, abs_tol=1e-6):
        return outcome("contradicted","amount_mismatch","Reconcile amount, explicit scaling and formula against saved source inputs; original report is retained.",expected,selected)
    label = "derived calculation" if claim.kind != "fact" or selected[0].origin == "derived" else "verified numerical fact"
    return outcome(label,"matched","Numerical amount and declared basis match saved evidence; interpretation and provider truth are not certified.",expected,selected)


def audit_report(saved, *, reference_time=None):
    reference = reference_time or datetime.now(timezone.utc).isoformat()
    instant(reference)
    raw = str(saved.get("report") or saved.get("draft") or "")
    claims, coverage = extract_claims(raw)
    try:
        facts, gaps = saved_facts(saved, reference)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        facts, gaps = [], ["Malformed saved source register; no facts certified."]
    findings = [verify_claim(c, facts) for c in claims]
    verified = sum(f["label"] in {"verified numerical fact","derived calculation"} for f in findings)
    return {"schema":"axiom-claim-audit-v1","run_id":saved.get("id"),"reference_time":reference,
            "report_sha256":hashlib.sha256(raw.encode()).hexdigest(),
            "evidence_sha256":hashlib.sha256(json.dumps(saved.get("evidence") or [],sort_keys=True,default=str).encode()).hexdigest(),
            "coverage":{**coverage,"checked_numeric_statements":verified,"extracted_statements":len(findings)},
            "freshness":{"available_observations":sum(f.status == "available" for f in facts),"stale_observations":sum(f.status == "stale" for f in facts),"unavailable_observations":sum(f.status not in {"available","stale"} for f in facts)},
            "reconciliation":{"contradictions":sum(f["label"] == "contradicted" for f in findings),"unverifiable":sum(f["label"] == "unverifiable" for f in findings)},
            "interpretive_uncertainty":"Unassessed. Numerical checks do not verify investment theses, opinions or future targets.",
            "findings":findings,"source_gaps":gaps,
            "limitations":["Bounded extraction: at most 60,000 characters and 100 numeric lines. Unsupported sentences, tables, metrics and ambiguous language remain unverified.",
                "Supported prose: explicit earnings, TTM revenue, price/cap statements and P/E with dated TTM inputs. Revenue requires the independently validated earnings fiscal window and a separate raw-quarter revenue sum. Other metric families and ambiguous prose remain unverified; structured annual growth checks require both eligible period observations.",
                "Source instructions are data only. No source text is executed or sent to a model. No independent filing/provider truth or corporate-event comparability certification.",
                "Freshness is evaluated at the stated reference time; this audit makes no provider/model calls and never overwrites saved text."]}
