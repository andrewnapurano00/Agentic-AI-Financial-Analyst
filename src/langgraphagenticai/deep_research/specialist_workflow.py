"""Independent bounded specialists over eligible saved contracts, never raw session data."""
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from uuid import uuid4

from .models import dumps, parse_symbols, utc_now
from .quarterly_ttm import METHODOLOGY, window
from .specialist_contracts import AgentResult, EvidenceRef, FinalDecision, ReviewFinding, Task
from langgraphagenticai.utils.safety import redact_value, sanitize_error
from langgraphagenticai.analysis.earnings_metrics import research_net_income

METRICS = ("Revenue (TTM)", "Net income (TTM)", "Operating income (TTM)",
           "Free cash flow (TTM)", "Operating cash flow (TTM)", "Market cap",
           "Price", "P/E (TTM)", "P/B (TTM)", "Debt / Assets", "ROE", "ROA")
LIMITS = {"model_attempts": 3, "tool_dispatches": 1, "continuations": 1,
          "duration_seconds": 90, "call_timeout_seconds": 25,
          "request_bytes": 24000, "output_tokens_per_call": 1200,
          "total_output_tokens": 3600}


def fingerprint(saved):
    selected = {key: saved.get(key) for key in ("id", "request", "evidence", "comparison", "financial_methodology")}
    return hashlib.sha256(dumps(selected).encode("utf-8")).hexdigest()


def _instant(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Unknown retrieval timezone")
    return parsed.astimezone(timezone.utc)


def collect_saved(saved, *, now=None):
    """No network. Preserve exact source inputs; reject unsupported contract meanings."""
    now = now or datetime.now(timezone.utc)
    symbols = saved.get("request", {}).get("symbols", [])
    if len(symbols) != 1 or parse_symbols(",".join(symbols)) != symbols:
        return [], ["Select an existing one-company research run."]
    if saved.get("financial_methodology") != METHODOLOGY:
        return [], ["Saved financial methodology is legacy or unavailable; explicitly run fresh audited research."]
    rows = [r for r in saved.get("comparison", []) if r.get("Ticker") == symbols[0]]
    if len(rows) != 1:
        return [], ["Company comparison is missing or ambiguous."]
    records = saved.get("evidence", [])
    refs, gaps = [], []
    for name in METRICS:
        contract = rows[0].get("Metric contracts", {}).get(name, {})
        try:
            if name == "Net income (TTM)":
                observation = research_net_income(saved, symbols[0], reference_time=now.isoformat())
                if not observation.eligible:
                    raise ValueError("Shared earnings observation: " + observation.status + "; " + "; ".join(observation.reasons))
            value = contract.get("value")
            if (contract.get("methodology") != METHODOLOGY or contract.get("status") != "ok"
                    or contract.get("applicability") != "applicable"
                    or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                    or rows[0].get(name) != value or not contract.get("inputs")):
                raise ValueError("Missing, unsupported or inconsistent contract")
            sources = contract["inputs"]
            if len(sources) > 8 or not contract.get("unit"):
                raise ValueError("Unsupported source count/unit")
            expected_unit = "currency" if name in METRICS[:7] else "multiple" if name in METRICS[7:9] else "ratio" if name == "Debt / Assets" else "fraction"
            if contract["unit"] != expected_unit:
                raise ValueError("Unsupported metric unit")
            for source in sources:
                matches = [e for e in records if e.get("id") == source.get("source_id")]
                if (len(matches) != 1 or matches[0].get("symbol") != symbols[0]
                        or matches[0].get("status") != "ok" or not matches[0].get("data")
                        or not source.get("provider") or source.get("provider") != matches[0].get("provider")
                        or source.get("retrieved_at") != matches[0].get("retrieved_at")
                        or source.get("category") != matches[0].get("category")
                        or source.get("currency_basis", "").startswith("Matching profile inference")):
                    raise ValueError("Missing, ambiguous or inferred source identity")
                data = matches[0]["data"]
                candidates = data if isinstance(data, list) else [data]
                candidates = [r for r in candidates if isinstance(r, dict)
                              and source.get("field") in r and r[source["field"]] == source.get("value")]
                if not candidates or isinstance(source.get("value"), bool) or not isinstance(source.get("value"), (int, float)) or not math.isfinite(source["value"]):
                    raise ValueError("Source input does not match its retained record")
                if source.get("category") in {"income_ttm", "cash_flow_ttm"}:
                    dated = [r for r in candidates if r.get("methodology") == METHODOLOGY and len(r.get("quarters", [])) == 4]
                    if len(dated) != 1:
                        raise ValueError("Audited four-quarter source metadata is missing or ambiguous")
                    quarters = [{**q, "symbol": symbols[0], "reportedCurrency": source["currency"]} for q in dated[0]["quarters"]]
                    ordered = window(quarters, symbols[0])
                    if ordered[0]["date"] != dated[0].get("date"):
                        raise ValueError("TTM end date differs from the audited quarter window")
                age = (now - _instant(source["retrieved_at"])).total_seconds()
                max_age = 86400 if source.get("category") == "quote" else 30 * 86400
                as_of = datetime.fromisoformat(str(source["date"]).replace("Z", "+00:00")).date()
                if not 0 <= age <= max_age or as_of > now.date():
                    raise ValueError("Stale/future or undated source")
                if source.get("category") != "quote" and not any(str(r.get("date") or r.get("as_of")) == str(source["date"]) for r in candidates):
                    raise ValueError("Source fiscal date mismatch")
                if source.get("category") == "quote":
                    from .research_metrics import quote_time
                    if not any(quote_time(r.get("timestamp")) == source["date"] for r in candidates):
                        raise ValueError("Quote timestamp mismatch")
                if not any((r.get("reportedCurrency") or r.get("currency")) == source.get("currency") for r in candidates):
                    raise ValueError("Source reporting currency mismatch")
                max_period_age = 7 if source.get("category") == "quote" else 200 if source.get("category") in {"income_ttm", "cash_flow_ttm", "balance_latest"} else 800
                if (now.date() - as_of).days > max_period_age:
                    raise ValueError("Financial/quote observation is too old for this pilot")
            currencies = {s.get("currency") for s in sources}
            if None in currencies or len(currencies) != 1:
                raise ValueError("Unknown or mismatched source currencies")
            if contract.get("unit") == "currency" and contract.get("currency") not in currencies:
                raise ValueError("Metric currency does not match inputs")
            if len(sources) == 1 and name in METRICS[:7] and value != sources[0]["value"]:
                raise ValueError("Direct metric does not match the source value")
            if name in {"P/E (TTM)", "P/B (TTM)", "Debt / Assets"}:
                if len(sources) != 2 or sources[0]["value"] < 0 or (name != "Debt / Assets" and sources[0]["value"] == 0) or sources[1]["value"] <= 0 or not math.isclose(
                        value, sources[0]["value"] / sources[1]["value"], rel_tol=1e-9, abs_tol=1e-12):
                    raise ValueError("Multiple/leverage arithmetic or denominator is inconsistent")
            if name in {"ROE", "ROA"}:
                if len(sources) != 3 or min(s["value"] for s in sources[1:]) <= 0 or not math.isclose(
                        value, sources[0]["value"] / ((sources[1]["value"] + sources[2]["value"]) / 2), rel_tol=1e-9, abs_tol=1e-12):
                    raise ValueError("Matched-balance return arithmetic is inconsistent")
            basis = contract.get("basis")
            period = json.dumps(basis, sort_keys=True, ensure_ascii=False) if basis is not None else "; ".join(
                str(s["category"]) + ":" + str(s["date"]) for s in sources)
            ref = EvidenceRef(id=f"M{METRICS.index(name)+1:03}", ticker=symbols[0], metric=name,
                value=value, unit=contract["unit"], currency=contract.get("currency"), period=redact_value(period),
                sources=redact_value(sources), formula=redact_value(contract.get("formula") or "Unavailable"))
            if len(dumps(ref.model_dump()).encode("utf-8")) > 5000:
                raise ValueError("Metric provenance exceeds pilot bounds")
            refs.append(ref)
        except (ValueError, TypeError, KeyError) as exc:
            gaps.append(name + ": " + str(exc))
    return refs, gaps


def validate_agent(task, output, refs):
    """Exact observation matching is mechanical, not semantic verification of prose."""
    known = {r.id: r for r in refs}
    errors = []
    if output.task_id != task.id or output.ticker != task.ticker:
        errors.append("Specialist identity mismatch")
    for claim in output.observations:
        ref = known.get(claim.evidence_id)
        if not ref or claim.evidence_id not in task.evidence_ids:
            errors.append("Unknown or unsubmitted evidence reference")
        elif (claim.value != ref.value or claim.unit != ref.unit or claim.currency != ref.currency or claim.period != ref.period):
            errors.append("Observation value/unit/currency/period mismatch: " + claim.evidence_id)
    if any(name not in METRICS for name in output.missing_metrics):
        errors.append("Unsupported metric lookup request")
    if any(re.search(r"\d", text) for text in [output.summary, *output.risks]):
        errors.append("Numerical statements must be structured observations, not uncited prose")
    return [ReviewFinding(task_id=task.id, severity="error", code="invalid_claim", detail=e) for e in errors]


def reconcile(agents, findings, gaps):
    completed = [a for a in agents if a["status"] == "finished"]
    disagreement = []
    if len(completed) == 2 and completed[0]["result"]["stance"] != completed[1]["result"]["stance"]:
        disagreement = [a["role"] + ": " + a["result"]["stance"] for a in completed]
    ready = len(completed) == 2 and not any(f["severity"] == "error" for f in findings)
    return FinalDecision(status="complete" if ready and not gaps else "partial" if completed else "unavailable",
        agreement="disputed" if disagreement else "aligned" if ready else "incomplete",
        summary=" | ".join(a["role"] + ": " + a["result"]["summary"] for a in completed)
            or "No validated specialist interpretation is available.",
        disagreements=disagreement,
        limitations=["Model interpretations are not investment recommendations or verified prose. "
                     "Exact observation checks do not establish semantic support. AX-04/AX-06 remain prerequisites for wider rollout.", *gaps]).model_dump()


def run_specialists(saved, call, *, now=None, clock=time.monotonic):
    """Independent first calls, one named local gap dispatch, no retries or recursive agents."""
    started = clock()
    refs, gaps = collect_saved(saved, now=now)
    run = {"id": uuid4().hex, "source_run_id": saved.get("id"), "source_fingerprint": fingerprint(saved),
           "created_at": utc_now(), "limits": dict(LIMITS), "agents": [], "findings": [], "tasks": [],
           "sources": [r.model_dump() for r in refs], "usage": [], "tool_dispatches": [], "model_attempts": 0}
    if not refs:
        run["decision"] = reconcile([], [], gaps)
        run["elapsed_seconds"] = clock() - started
        return run
    ticker = saved["request"]["symbols"][0]
    # Each specialist receives its own packet and cannot see the other's output.
    def analyze(role, selected, suffix=""):
        remaining = LIMITS["duration_seconds"] - (clock() - started)
        if remaining <= 1 or run["model_attempts"] >= LIMITS["model_attempts"]:
            return {"role": role, "status": "failed", "error": "Run duration/model-attempt limit reached", "result": None}
        task = Task(id=role + suffix, ticker=ticker, role=role,
            question=redact_value(str(saved["request"].get("question") or "Assess the saved company evidence."))[:1500],
            evidence_ids=[r.id for r in selected], tool_allowlist=["saved_metric_lookup"],
            timeout_seconds=min(25, remaining), output_tokens=1200)
        run["tasks"].append(task.model_dump())
        run["model_attempts"] += 1  # Failed requests consume the attempt, with no retries.
        try:
            output, usage = call(task, [r.model_dump() for r in selected])
            run["usage"].append({"task_id": task.id, "model": sanitize_error(usage.get("model", "Configured model")),
                "input_tokens": usage.get("input_tokens") if isinstance(usage.get("input_tokens"), int) else None,
                "output_tokens": usage.get("output_tokens") if isinstance(usage.get("output_tokens"), int) else None,
                "estimated_cost_usd": None, "pricing": "Unknown; no dollar ceiling"})
            output = AgentResult.model_validate(output)
            issues = validate_agent(task, output, selected)
            if clock() - started > LIMITS["duration_seconds"]:
                issues.append(ReviewFinding(task_id=task.id, severity="error", code="timeout", detail="Response arrived beyond the run deadline"))
            run["findings"].extend(f.model_dump() for f in issues)
            if issues:
                return {"role": role, "status": "failed", "error": "Observation/identity validation failed", "result": None}
            return {"role": role, "status": "finished", "error": None, "result": redact_value(output.model_dump())}
        except Exception as exc:
            if not run["usage"] or run["usage"][-1]["task_id"] != task.id:
                run["usage"].append({"task_id": task.id, "status": "failed", "input_tokens": None,
                                     "output_tokens": None, "pricing": "Failed request usage/cost unknown"})
            run["findings"].append(ReviewFinding(task_id=task.id, severity="error", code="stage_failure",
                detail=sanitize_error(exc)).model_dump())
            return {"role": role, "status": "failed", "error": sanitize_error(exc), "result": None}
    for role in ("fundamentals", "valuation_risk"):
        names = METRICS[:5] if role == "fundamentals" else METRICS[5:]
        selected = [r for r in refs if r.metric in names]
        if selected:
            run["agents"].append(analyze(role, selected))
        else:
            run["agents"].append({"role": role, "status": "partial", "error": "No eligible role-specific evidence", "result": None})
    # Only exact supported metric names may invoke this local saved-data tool.
    for index, agent in enumerate(run["agents"]):
        requested = agent["result"]["missing_metrics"] if agent.get("result") else []
        if requested:
            original = next(t["evidence_ids"] for t in run["tasks"] if t["id"] == agent["role"])
            found = [r for r in refs if r.metric in requested and r.id not in original]
            run["tool_dispatches"].append({"tool": "saved_metric_lookup", "requested": requested,
                                           "resolved": [r.id for r in found], "network_calls": 0})
            if found:
                selected = [r for r in refs if r.id in original or r in found]
                continuation = analyze(agent["role"], selected, "_gap")
                # Never erase a valid first interpretation when gap continuation fails.
                if continuation["status"] == "finished":
                    run["agents"][index] = continuation
            break
    unresolved = sorted({m for a in run["agents"] if a.get("result") for m in a["result"]["missing_metrics"]})
    run["decision"] = reconcile(run["agents"], run["findings"], gaps + ["Unresolved requested metric: " + m for m in unresolved])
    run["elapsed_seconds"] = clock() - started
    return run
