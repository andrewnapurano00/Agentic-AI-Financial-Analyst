from __future__ import annotations

import json
import re
import uuid
from typing import Dict, Optional

import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage

from langgraphagenticai.LLMS.openaillm import OpenAILLM
from langgraphagenticai.graph.graph_builder import GraphBuilder
from langgraphagenticai.prompts.system_prompts import get_system_prompt
from langgraphagenticai.tools.finance_tool_registry import get_finance_tools
from langgraphagenticai.ui.equity_report_tab import render_equity_report_tab
from langgraphagenticai.ui.portfolio_optimizer_tab import render_portfolio_optimizer_tab
from langgraphagenticai.ui.stock_screener_tab import render_stock_screener_tab
from langgraphagenticai.ui.ai_portfolio_manager_tab import render_ai_portfolio_manager_tab
from langgraphagenticai.ui.streamlitui.loadui import LoadStreamlitUI
from langgraphagenticai.utils.app_health import validate_runtime_config
from langgraphagenticai.utils.logging_utils import log_error, log_event, timed_event
from langgraphagenticai.utils.response_cleaner import clean_financial_text


TABLE_HINT_PATTERNS = [
    r"\btable\b",
    r"\btabular\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bscorecard\b",
    r"\bmatrix\b",
    r"\brank(?:ed|ing)?\b",
    r"\bsummary table\b",
]


def is_table_request(user_text: str) -> bool:
    text = (user_text or "").lower()
    return any(re.search(pattern, text) for pattern in TABLE_HINT_PATTERNS)


def _bootstrap_session_state() -> None:
    defaults = {
        "chat_history": [],
        "thread_id": str(uuid.uuid4()),
        "last_result_messages": [],
        "app_ready": False,
        "config_fingerprint": None,
        "request_counter": 0,
        "equity_report_payload": None,
        "equity_report_tickers": [],
        "equity_report_ticker_text": "AAPL, MSFT, NVDA, GOOGL",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _maybe_reset_thread_for_config_change(model_name: str, usecase: str) -> None:
    fingerprint = f"{model_name}::{usecase}"
    if st.session_state.get("config_fingerprint") != fingerprint:
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.session_state.last_result_messages = []
        st.session_state.config_fingerprint = fingerprint


@st.cache_resource(show_spinner=False)
def _build_cached_graph(
    openai_api_key: str,
    model_name: str,
    fmp_api_key: str,
    usecase: str,
    marketaux_api_key: str = "",
):
    llm = OpenAILLM(
        user_controls_input={
            "OPENAI_API_KEY": openai_api_key,
            "selected_model": model_name,
        }
    ).get_llm_model()

    tools = get_finance_tools(
        fmp_api_key=fmp_api_key,
        openai_api_key=openai_api_key,
        marketaux_api_key=marketaux_api_key,
    )

    system_prompt = get_system_prompt(usecase)
    graph = GraphBuilder(
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
    ).build_finance_graph()

    return graph


@st.cache_resource(show_spinner=False)
def _build_repair_llm(openai_api_key: str, model_name: str):
    return OpenAILLM(
        user_controls_input={
            "OPENAI_API_KEY": openai_api_key,
            "selected_model": model_name,
        }
    ).get_llm_model()


def _render_prior_chat() -> None:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _finance_input_hint(selected_usecase: str) -> str:
    hints = {
        "Basic Finance Chat": "Ask a finance question...",
        "Single Company Analysis": "Example: Analyze AAPL across business, financials, price action, and risks.",
        "Compare Companies": "Example: Compare AAPL, MSFT, and GOOG on profitability and valuation.",
        "News and Earnings Review": "Example: Summarize recent news and transcript takeaways for NVDA.",
        "Full Company Research Report": "Example: Build a structured research report on AMZN.",
    }
    return hints.get(selected_usecase, "Ask about a company or compare companies...")


def _extract_text_from_message(message) -> str:
    content = getattr(message, "content", None)
    if not content:
        return ""

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        return "\n".join([p for p in parts if p]).strip()

    return str(content).strip()


def _extract_final_text(result_messages) -> str:
    for msg in reversed(result_messages):
        text = _extract_text_from_message(msg)
        if text:
            return text
    return "I was unable to generate a response."


def _strip_code_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _try_parse_table_response(text: str) -> Optional[Dict[str, object]]:
    cleaned = _strip_code_fences(text)
    if not cleaned:
        return None

    try:
        data = json.loads(cleaned)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    if data.get("response_type") != "table":
        return None

    title = str(data.get("title", "Table")).strip() or "Table"
    columns = data.get("columns", [])
    rows = data.get("rows", [])
    takeaways = data.get("takeaways", [])

    if not isinstance(columns, list) or not columns:
        return None
    if not isinstance(rows, list):
        return None
    if not isinstance(takeaways, list):
        takeaways = []

    try:
        df = pd.DataFrame(rows, columns=columns)
    except Exception:
        return None

    return {
        "title": title,
        "df": df,
        "takeaways": takeaways,
    }


def _repair_table_response(final_text: str, llm) -> Optional[Dict[str, object]]:
    repair_prompt = f"""
Convert the following finance answer into valid JSON only.

Use this exact schema:
{{
  "response_type": "table",
  "title": "Short title",
  "columns": ["Column 1", "Column 2", "Column 3"],
  "rows": [
    ["row1col1", "row1col2", "row1col3"]
  ],
  "takeaways": [
    "Short takeaway 1",
    "Short takeaway 2"
  ]
}}

Rules:
- Do not use markdown fences.
- Do not include prose outside the JSON.
- Use "N/A" if a value is missing.
- Keep rows rectangular.
- If companies are being compared, include Ticker as the first column.
- Keep the table concise and useful.

Answer to convert:
\"\"\"{final_text}\"\"\"
"""
    try:
        repaired = llm.invoke(repair_prompt)
        repaired_text = getattr(repaired, "content", str(repaired))
        return _try_parse_table_response(repaired_text)
    except Exception:
        return None


def _render_table_payload(parsed_table: Dict[str, object]) -> None:
    st.markdown(f"### {parsed_table['title']}")
    st.dataframe(parsed_table["df"], use_container_width=True)

    takeaways = parsed_table.get("takeaways") or []
    if takeaways:
        st.markdown("**Takeaways**")
        for item in takeaways:
            st.markdown(f"- {item}")


def _render_assistant_response(final_text: str, user_input: str, repair_llm=None) -> None:
    parsed_table = _try_parse_table_response(final_text)
    cleaned_text = clean_financial_text(final_text)

    with st.chat_message("assistant"):
        if parsed_table:
            _render_table_payload(parsed_table)
            return

        if is_table_request(user_input) and repair_llm is not None:
            repaired_table = _repair_table_response(final_text, repair_llm)
            if repaired_table:
                _render_table_payload(repaired_table)
                return

        st.markdown(cleaned_text)

        if is_table_request(user_input):
            st.caption("The model returned prose instead of structured table JSON.")


def _render_debug_trace(result_messages) -> None:
    with st.expander("Debug trace", expanded=False):
        for idx, msg in enumerate(result_messages, start=1):
            msg_type = msg.__class__.__name__
            tool_name = getattr(msg, "name", None)
            label = f"{idx}. {msg_type}"
            if tool_name:
                label += f" · {tool_name}"
            st.markdown(f"**{label}**")
            st.code(_extract_text_from_message(msg) or str(msg))


def _render_status_panel(warnings):
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Runtime status")
        if warnings:
            for warning in warnings:
                st.warning(warning)
        else:
            st.success("All configured capabilities look ready.")


def load_langgraph_agenticai_app() -> None:
    _bootstrap_session_state()

    ui = LoadStreamlitUI()
    user_controls = ui.load_streamlit_ui()

    selected_usecase = user_controls.get("selected_usecase", "Basic Finance Chat")
    openai_api_key = user_controls.get("OPENAI_API_KEY", "").strip()
    fmp_api_key = user_controls.get("FMP_API_KEY", "").strip()
    model_name = user_controls.get("selected_model", "gpt-5")
    debug_mode = bool(user_controls.get("debug_mode", False))
    marketaux_api_key = user_controls.get("MARKETAUX_API_KEY", "").strip()

    health = validate_runtime_config(
        openai_api_key=openai_api_key,
        fmp_api_key=fmp_api_key,
        marketaux_api_key=marketaux_api_key,
        selected_model=model_name,
    )

    if health["errors"]:
        for err in health["errors"]:
            st.error(err)
        return

    _render_status_panel(health["warnings"])
    _maybe_reset_thread_for_config_change(model_name, selected_usecase)

    try:
        with timed_event(
            "graph_initialize",
            model_name=model_name,
            selected_usecase=selected_usecase,
        ):
            graph = _build_cached_graph(
                openai_api_key=openai_api_key,
                model_name=model_name,
                fmp_api_key=fmp_api_key,
                usecase=selected_usecase,
                marketaux_api_key=marketaux_api_key,
            )
            repair_llm = _build_repair_llm(
                openai_api_key=openai_api_key,
                model_name=model_name,
            )
        st.session_state.app_ready = True
    except Exception as exc:
        st.session_state.app_ready = False
        log_error("app_init_failed", error=str(exc), model_name=model_name, selected_usecase=selected_usecase)
        st.error(f"Failed to initialize app: {exc}")
        return

    chat_tab, report_tab, optimizer_tab, screener_tab, ai_pm_tab = st.tabs(
        ["Agent Chat", "Equity Comparison Report", "Portfolio Optimizer", "Stock Screener", "AI Portfolio Manager"]
    )

    with report_tab:
        render_equity_report_tab(
            fmp_api_key=fmp_api_key,
            openai_api_key=openai_api_key,
            model_name=model_name,
        )

    with optimizer_tab:
        render_portfolio_optimizer_tab()

    with screener_tab:
        render_stock_screener_tab(fmp_api_key=fmp_api_key)

    with ai_pm_tab:
        render_ai_portfolio_manager_tab(
            openai_api_key=openai_api_key,
            model_name=model_name,
            marketaux_api_key=marketaux_api_key,
            fmp_api_key=fmp_api_key,
        )

    with chat_tab:
        _render_prior_chat()

        user_input = st.chat_input(_finance_input_hint(selected_usecase))
        if not user_input:
            return

        st.session_state.request_counter += 1
        request_id = f"req-{st.session_state.request_counter}"
        thread_id = st.session_state.thread_id

        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        log_event(
            "user_prompt_received",
            request_id=request_id,
            thread_id=thread_id,
            selected_usecase=selected_usecase,
            model_name=model_name,
            user_input=user_input[:500],
        )

        try:
            with timed_event(
                "graph_invoke",
                request_id=request_id,
                thread_id=thread_id,
                selected_usecase=selected_usecase,
                model_name=model_name,
            ):
                result = graph.invoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config={"configurable": {"thread_id": thread_id}},
                )
        except Exception as exc:
            log_error(
                "graph_execution_failed",
                request_id=request_id,
                thread_id=thread_id,
                error=str(exc),
            )
            with st.chat_message("assistant"):
                st.error(f"Graph execution failed: {exc}")
            return

        result_messages = result.get("messages", [])
        st.session_state.last_result_messages = result_messages

        final_text = _extract_final_text(result_messages)
        cleaned_final_text = clean_financial_text(final_text)

        log_event(
            "assistant_response_ready",
            request_id=request_id,
            thread_id=thread_id,
            response_length=len(cleaned_final_text),
            message_count=len(result_messages),
        )

        st.session_state.chat_history.append({"role": "assistant", "content": cleaned_final_text})
        _render_assistant_response(final_text, user_input, repair_llm=repair_llm)

        if debug_mode and result_messages:
            _render_debug_trace(result_messages)