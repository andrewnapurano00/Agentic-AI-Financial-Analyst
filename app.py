from pathlib import Path
import importlib
import sys
import threading

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
ENV_FILE = ROOT / ".env"

# Local development keys load automatically. Deployed environment variables and
# Streamlit secrets retain precedence when they are present.
load_dotenv(dotenv_path=ENV_FILE, override=False)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import langgraphagenticai.main as app_main


def _load_current_deep_research() -> None:
    """Refresh this feature after source edits without discarding Streamlit sessions."""
    source_files = (
        SRC / "langgraphagenticai" / "LLMS" / "openaillm.py",
        SRC / "langgraphagenticai" / "tools" / "fmp_mcp_client.py",
        SRC / "langgraphagenticai" / "deep_research" / "prompt_context.py",
        SRC / "langgraphagenticai" / "deep_research" / "data.py",
        SRC / "langgraphagenticai" / "deep_research" / "crew_committee.py",
        SRC / "langgraphagenticai" / "deep_research" / "manager.py",
        SRC / "langgraphagenticai" / "deep_research" / "v2.py",
        SRC / "langgraphagenticai" / "deep_research" / "v2_workflow.py",
        SRC / "langgraphagenticai" / "deep_research" / "quarterly_ttm.py",
        SRC / "langgraphagenticai" / "deep_research" / "v2_data.py",
        SRC / "langgraphagenticai" / "deep_research" / "quarterly_data.py",
        SRC / "langgraphagenticai" / "deep_research" / "research_metrics.py",
        SRC / "langgraphagenticai" / "deep_research" / "model_packets.py",
        SRC / "langgraphagenticai" / "deep_research" / "research_workflow.py",
        SRC / "langgraphagenticai" / "deep_research" / "presentation.py",
        SRC / "langgraphagenticai" / "deep_research" / "summary_text.py",
        SRC / "langgraphagenticai" / "deep_research" / "executive.py",
        SRC / "langgraphagenticai" / "deep_research" / "delivery.py",
        SRC / "langgraphagenticai" / "deep_research" / "report_structure.py",
        SRC / "langgraphagenticai" / "deep_research" / "committee_export.py",
        SRC / "langgraphagenticai" / "providers" / "company_evidence.py",
        SRC / "langgraphagenticai" / "providers" / "valuation.py",
        SRC / "langgraphagenticai" / "valuation" / "framework.py",
        SRC / "langgraphagenticai" / "valuation" / "book_value.py",
        SRC / "langgraphagenticai" / "valuation" / "model.py",
        SRC / "langgraphagenticai" / "valuation" / "projection.py",
        SRC / "langgraphagenticai" / "valuation" / "metrics.py",
        SRC / "langgraphagenticai" / "valuation" / "citations.py",
        SRC / "langgraphagenticai" / "valuation" / "coverage.py",
        SRC / "langgraphagenticai" / "valuation" / "ai.py",
        SRC / "langgraphagenticai" / "ui" / "equity_report_tab.py",
        SRC / "langgraphagenticai" / "ui" / "ai_valuation_tab.py",
        SRC / "langgraphagenticai" / "ui" / "deep_research_tab.py",
        SRC / "langgraphagenticai" / "ui" / "deep_research_v2_tab.py",
    )
    stamp = tuple(path.stat().st_mtime_ns for path in source_files)
    lock = getattr(app_main, "_deep_research_reload_lock", None)
    if lock is None:
        lock = threading.Lock()
        app_main._deep_research_reload_lock = lock
    with lock:
        # A fresh process has already imported the current modules above. Reloading
        # the full research stack here delays the first paint and can reconnect
        # external clients unnecessarily. Only reload after an actual source edit.
        if getattr(app_main, "_deep_research_source_stamp", None) is None:
            app_main._deep_research_source_stamp = stamp
            return
        if getattr(app_main, "_deep_research_source_stamp", None) == stamp:
            return
        importlib.invalidate_caches()
        for name in (
            "langgraphagenticai.LLMS.openaillm",
            "langgraphagenticai.tools.fmp_mcp_client",
            "langgraphagenticai.deep_research.prompt_context",
            "langgraphagenticai.deep_research.data",
            "langgraphagenticai.deep_research.crew_committee",
            "langgraphagenticai.deep_research.manager",
            "langgraphagenticai.deep_research.summary_text",
            "langgraphagenticai.deep_research.report_structure",
            "langgraphagenticai.deep_research.committee_export",
            "langgraphagenticai.deep_research.presentation",
            "langgraphagenticai.deep_research.executive",
            "langgraphagenticai.deep_research.delivery",
            "langgraphagenticai.deep_research.quarterly_ttm",
            "langgraphagenticai.deep_research.research_metrics",
            "langgraphagenticai.deep_research.model_packets",
            "langgraphagenticai.deep_research.quarterly_data",
            "langgraphagenticai.deep_research.research_workflow",
            "langgraphagenticai.deep_research.v2_data",
            "langgraphagenticai.deep_research.v2",
            "langgraphagenticai.deep_research.v2_workflow",
            "langgraphagenticai.providers.company_evidence",
            "langgraphagenticai.providers.valuation",
            "langgraphagenticai.valuation.framework",
            "langgraphagenticai.valuation.book_value",
            "langgraphagenticai.valuation.model",
            "langgraphagenticai.valuation.projection",
            "langgraphagenticai.valuation.metrics",
            "langgraphagenticai.valuation.citations",
            "langgraphagenticai.valuation.coverage",
            "langgraphagenticai.valuation.ai",
            "langgraphagenticai.ui.equity_report_tab",
            "langgraphagenticai.ui.ai_valuation_tab",
            "langgraphagenticai.ui.deep_research_tab",
            "langgraphagenticai.ui.deep_research_v2_tab",
        ):
            importlib.reload(importlib.import_module(name))
        deep_research_ui = importlib.import_module("langgraphagenticai.ui.deep_research_tab")
        app_main.render_deep_research_tab = deep_research_ui.render_deep_research_tab
        deep_research_v2_ui = importlib.import_module("langgraphagenticai.ui.deep_research_v2_tab")
        app_main.render_deep_research_v2_tab = deep_research_v2_ui.render_deep_research_v2_tab
        app_main.render_equity_report_tab = importlib.import_module("langgraphagenticai.ui.equity_report_tab").render_equity_report_tab
        app_main._deep_research_source_stamp = stamp


if __name__ == "__main__":
    _load_current_deep_research()
    app_main.load_langgraph_agenticai_app()
