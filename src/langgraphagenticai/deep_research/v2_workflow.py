"""V2 stage setup and optional decisions, independent of Streamlit state."""
from __future__ import annotations

import copy
import importlib.util
import time
from urllib.parse import urlsplit

from .crew_committee import run_investment_committee
from .data import FinancialDataSource
from .v2_data import QuarterlyFinancialDataSource, quarterly_comparison_rows
from .quarterly_ttm import METHODOLOGY
from .manager import ResearchManager, failure_reason
from .v2 import (V2BudgetError, V2ConfigurationError, build_stage_llm,
                 committee_diagnostics, projected_cost, report_instruction,
                 run_quick_decision, validate_report)
from langgraphagenticai.tools.finance_tool_registry import get_finance_tools
from langgraphagenticai.tools.serper_tools import SerperClient


class QuarterlyResearchManager(ResearchManager):
    def run(self, request, app_context=()):
        # Session snapshots may contain provider TTM facts from other workspaces.
        result = super().run(request, app_context=())
        result["financial_methodology"] = METHODOLOGY
        return result


def get_v2_finance_tools(fmp_api_key, openai_api_key="", marketaux_api_key=""):
    # Explicit allowlist: new tools cannot silently introduce TTM dependencies.
    safe = {"get_company_profile", "get_price_snapshot", "get_latest_earnings_transcript",
            "get_earnings_transcript", "get_analyst_estimates", "get_price_target_consensus",
            "get_available_earnings_transcript_periods", "get_company_peers",
            "get_dcf_valuation", "get_levered_dcf", "get_ratings_snapshot", "get_stock_grades",
            "get_company_earnings", "get_dividend_history", "get_esg_ratings", "get_esg_bundle"}
    return [tool for tool in get_finance_tools(fmp_api_key, openai_api_key, marketaux_api_key) if tool.name in safe]


def preflight(config, stages, *, openai_api_key="", groq_api_key="",
              ollama_base_url="http://localhost:11434/v1"):
    for stage in stages:
        route = config["routes"][stage]
        provider = route["provider"].lower()
        prefix = f"{stage.replace('_', ' ').title()} / {route['provider']}: "
        if not route.get("model", "").strip():
            raise V2ConfigurationError(prefix + "enter a model name.")
        if provider == "openai" and not openai_api_key.strip():
            raise V2ConfigurationError(prefix + "OPENAI_API_KEY is required.")
        if provider == "groq":
            if not groq_api_key.strip():
                raise V2ConfigurationError(prefix + "GROQ_API_KEY is required.")
            if importlib.util.find_spec("langchain_groq") is None:
                raise V2ConfigurationError(prefix + "install langchain-groq in the app environment.")
        if provider == "ollama":
            parsed = urlsplit(ollama_base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query:
                raise V2ConfigurationError(prefix + "use an HTTP(S) Ollama base URL without credentials or query parameters.")
        if provider not in {"openai", "groq", "ollama"}:
            raise V2ConfigurationError(prefix + "unsupported provider.")


class LazyStage:
    """Create only the selected stage model, once it is actually invoked."""
    def __init__(self, stage, config, credentials):
        self.stage, self.config, self.credentials = stage, config, credentials
        self.model_name = config["routes"][stage]["model"]
        self._llm = None

    def _call(self, method, messages, kwargs):
        route = self.config["routes"][self.stage]
        preflight(self.config, [self.stage], **self.credentials)
        if self._llm is None:
            self._llm = build_stage_llm(route["provider"], route["model"], **self.credentials)
        if route["provider"].lower() != "openai":
            kwargs.pop("reasoning_effort", None)
            kwargs.pop("response_format", None)
            kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")
        return getattr(self._llm, method)(messages, **kwargs)

    def invoke(self, messages, **kwargs):
        return self._call("invoke", messages, kwargs)

    def stream(self, messages, **kwargs):
        return self._call("stream", messages, kwargs)


def build_manager(*, request, config, openai_api_key, groq_api_key, fmp_api_key,
                  serper_api_key, marketaux_api_key, ollama_base_url, budget,
                  stop_after_evidence, progress=None, on_text=None, checkpoint=None, saved=None):
    credentials = dict(openai_api_key=openai_api_key, groq_api_key=groq_api_key,
                       ollama_base_url=ollama_base_url)
    required = ["review"] if saved and saved.get("draft") else ["draft"] if saved else ["plan"]
    if not saved and not stop_after_evidence:
        required.append("draft")
    if not stop_after_evidence and config["interpretive_review"]:
        required.append("review")
    preflight(config, required, **credentials)
    models = {stage: LazyStage(stage, config, credentials) for stage in ("plan", "draft", "review", "follow_up")}
    limits = dict(config["limits"])
    limits["draft"] = (150, config["depth_draft_tokens"][request.depth])
    options = {}
    for stage, route in config["routes"].items():
        if route["provider"] == "OpenAI" and route["model"] in {"gpt-5", "gpt-5-mini", "gpt-5-nano"}:
            options[stage] = {"reasoning_effort": "minimal"}
    # Resuming never needs provider clients or investigation tools.
    source = QuarterlyFinancialDataSource("") if saved else QuarterlyFinancialDataSource(fmp_api_key)
    tools = [] if saved else get_v2_finance_tools(fmp_api_key, openai_api_key, marketaux_api_key)
    manager = QuarterlyResearchManager(
        models["draft"], source, SerperClient(serper_api_key), tools, progress,
        on_text=on_text, checkpoint=checkpoint, utility_llm=models["plan"], stage_llms=models,
        stage_limits=limits, context_limits=config["contexts"], stage_options=options,
        report_instruction=lambda req: report_instruction(req, config), allow_clarification_retry=False,
        deterministic_validator=validate_report,
        interpretive_review=config["interpretive_review"] or bool(saved and saved.get("status") == "review_pending"),
        max_estimated_cost_usd=budget, stop_after_evidence=stop_after_evidence,
    )
    manager.comparison_builder = quarterly_comparison_rows if not saved or saved.get("financial_methodology") == METHODOLOGY else manager.comparison_builder
    return manager


def run_decision(saved, *, openai_api_key, groq_api_key=""):
    """A decision failure never changes the saved research status or report."""
    result = copy.deepcopy(saved)
    runtime, config = result["v2_runtime"], result["v2_config"]
    mode = runtime.get("decision_mode", "None")
    if mode == "None":
        return result
    if result.get("status") != "complete" or not result.get("report"):
        result["decision_status"] = "waiting_for_report"
        return result
    lead, specialist = config["routes"]["crew_lead"], config["routes"]["crew_specialists"]
    stages = ["crew_lead"] + (["crew_specialists"] if mode == "Full committee" else [])
    started, invoked, projected = time.monotonic(), False, 0.0
    diagnostic = {"stage": "quick_decision" if mode == "Quick decision" else "committee",
                  "model": lead["model"]}
    try:
        preflight(config, stages, openai_api_key=openai_api_key, groq_api_key=groq_api_key,
                  ollama_base_url=runtime.get("ollama_base_url", "http://localhost:11434/v1"))
        projected = projected_cost(lead["model"], input_characters=config["contexts"]["committee"] + 2000,
                                   output_tokens=900 if mode == "Quick decision" else 1200)
        if mode == "Full committee" and specialist["provider"] == "OpenAI":
            projected += 2 * projected_cost(specialist["model"], input_characters=config["contexts"]["committee"] + 2000, output_tokens=1000)
        if float(result.get("estimated_model_cost_usd") or 0) + projected > float(runtime["budget"]):
            raise V2BudgetError("Decision would exceed the saved model-cost budget. No decision call was made.")
        invoked = True
        if mode == "Quick decision":
            llm = build_stage_llm(lead["provider"], lead["model"], openai_api_key=openai_api_key)
            decision, row = run_quick_decision(result, llm, model=lead["model"], max_chars=config["contexts"]["committee"])
            result["quick_decision"] = decision
            rows = [row]
        else:
            result["crewai_decision"] = run_investment_committee(
                result, openai_api_key=openai_api_key, model_name=lead["model"],
                specialist_model=specialist["model"], specialist_provider=specialist["provider"],
                groq_api_key=groq_api_key, packet_max_chars=config["contexts"]["committee"],
                ollama_base_url=runtime.get("ollama_base_url", "http://localhost:11434/v1"))
            rows = committee_diagnostics(result["crewai_decision"])
        result.setdefault("diagnostics", []).extend(rows)
        result["estimated_model_cost_usd"] = round(float(result.get("estimated_model_cost_usd") or 0) + sum(float(d.get("estimated_cost_usd") or 0) for d in rows), 6)
        result["decision_status"] = "complete"
        result.pop("decision_error", None)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, (V2ConfigurationError, V2BudgetError)) else failure_reason(exc)
        result.update(decision_status="failed", decision_error=reason)
        diagnostic.update(status="failed" if invoked else "blocked", reason=reason,
                          seconds=round(time.monotonic() - started, 2), projected_cost_usd=projected)
        if invoked:
            # Actual failed-request billing is unknown. Reserve the projected cost
            # rather than treating retries as free.
            diagnostic.update(estimated_cost_usd=projected, token_counts_estimated=True,
                              usage_note="Failed decision usage unavailable; projected cost reserved for retry budgeting.")
            result["estimated_model_cost_usd"] = round(float(result.get("estimated_model_cost_usd") or 0) + projected, 6)
        result.setdefault("diagnostics", []).append(diagnostic)
    return result
