"""P02 D01-D09: saved metadata and ordinary rendering remain honest/offline."""
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui.workspace_presentation import evidence_status, snapshot_status, source_link


def test_saved_evidence_range_uses_instants_and_never_generation_clock():
    result = {"report_generated_at": "2026-10-06T12:00:00Z", "evidence": [
        {"status": "ok", "data": {"value": 0}, "retrieved_at": "2026-09-01T10:00:00+09:00", "provider": "FMP"},
        {"status": "ok", "data": [1], "retrieved_at": "2026-09-01T03:00:00Z", "provider": "FMP"},
        {"status": "ok", "data": [1], "retrieved_at": "2026-08-31", "provider": "FMP"},
        {"status": "error", "data": [1]}, {"status": "ok", "data": {}},
    ]}
    row = dict(evidence_status(result))
    assert row["Saved evidence"] == "Partial: 3 usable / 5 records"
    assert row["Evidence retrieved"].startswith("2026-09-01 01:00:00+00:00 to 2026-09-01 03:00:00+00:00")
    assert "timezone unknown" in row["Evidence retrieved"]
    assert "2026-10-06" not in str(row)
    assert dict(evidence_status({}))["Evidence retrieved"] == "Unavailable"


def test_snapshot_missing_is_not_zero_or_configuration_success():
    assert dict(snapshot_status({"fundamentals": {"metadata": {}}, "providers": ["FMP"]}))["Company datasets"] == "Missing"
    row = dict(snapshot_status({"quote": {"price": 0}, "fundamental_basis": {"status": "partial"}}))
    assert row["Company datasets"] == "Partial"
    assert row["Quote as of"] == "Unavailable"
    assert "Unknown" in row["Financial basis"]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://user:pass@example.com", "https://example.com?api_key=secret", "https://example.com?access_token=secret", "https://example.com?signature=secret", "https://example.com#token=secret", "https://example.com/\nunsafe"])
def test_source_links_reject_unsafe_or_credential_urls(url):
    assert source_link(url) == ""


def test_public_source_link_retained():
    assert source_link("https://example.com/company?article=1") == "https://example.com/company?article=1"


def test_shell_escaped_honest_responsive_and_rerun_safe():
    app = AppTest.from_string("""
import streamlit as st
from langgraphagenticai.ui.app_shell import *
st.session_state.setdefault('calls', 0)
inject_app_shell_css()
page=st.selectbox('Workspace', ['Introduction','Research','Deep Research V2'])
render_page_header(page)
render_company_header('AAPL', '<script>provider</script>', 'Unknown currency')
render_executive_cards([('Identity','AAPL','saved'),('Evidence','Partial','missing inputs'),('Action','Submit','explicit'),('Hidden','fourth','not shown')])
render_evidence_row([('Quote as of','2026-09-15'),('Source','<unsafe>')])
with st.expander('Saved details'):
    st.write('Saved evidence remains available')
st.selectbox('Chart range',['1Y','5Y'])
render_terminal_status('fixture',fmp_ready=True,openai_ready=False)
""").run()
    assert not app.exception
    text = " ".join(x.value for x in app.markdown)
    assert 'SYSTEM READY' not in text and 'AS OF:' not in text
    assert 'Page rendered at:' in text and 'CONFIGURED' in text
    assert '&lt;script&gt;' in text and '&lt;unsafe&gt;' in text
    assert 'Hidden' not in text
    app.selectbox[0].set_value('Research').run()
    app.selectbox[1].set_value('5Y').run()
    assert app.session_state['calls'] == 0
    assert not app.exception


def test_actual_saved_intro_controls_preserve_unknown_currency_and_missing_change(monkeypatch):
    from langgraphagenticai.ui import introduction_tab
    calls = []
    monkeypatch.setattr(introduction_tab, "load_symbol_history", lambda *a, **k: {"points": [], "warnings": ["Partial chart fixture"]})
    monkeypatch.setattr(introduction_tab, "generate_company_summary", lambda *a, **k: calls.append("paid"))
    app = AppTest.from_string("""
from langgraphagenticai.ui.introduction_tab import _render_company_snapshot
snapshot = {'symbol':'AAPL','company':'Apple <fixture>','quote':{'price':180,'change_pct':None},'profile':{},'fundamentals':{},'performance':{},'news':[],'fundamental_basis':{'status':'partial'}}
_render_company_snapshot(snapshot,'Saved AI findings')
""").run()
    assert not app.exception
    text = " ".join(item.value for item in app.markdown)
    assert "Unknown currency" in text and "Quote change unavailable" in text
    assert "$180" not in text and "+0.00%" not in text
    app.segmented_control[0].set_value("5Y").run()
    assert not app.exception and calls == []


def test_actual_saved_v2_rerun_keeps_evidence_date_and_zero_paid_calls(monkeypatch):
    from langgraphagenticai.ui import deep_research_v2_tab
    from test_deep_research_ui import sample_result
    calls = []
    def forbidden(*a, **k):
        calls.append("paid")
        raise AssertionError("Ordinary rendering must not call models")
    monkeypatch.setattr(deep_research_v2_tab, "_manager_v2", forbidden)
    monkeypatch.setattr(deep_research_v2_tab, "run_decision", forbidden)
    saved = sample_result()
    saved.update(result_generated_at="2026-10-05T10:00:00Z", diagnostics=[], v2_config={}, v2_runtime={"decision_mode":"None"})
    app = AppTest.from_string("""
from langgraphagenticai.ui.deep_research_v2_tab import render_deep_research_v2_tab
render_deep_research_v2_tab(openai_api_key='',fmp_api_key='')
""", default_timeout=30)
    app.session_state['drv2_history'] = [saved]
    app.run()
    assert not app.exception
    text = " ".join(item.value for item in app.markdown)
    assert "2026-01-02" in text
    assert "2 usable / 2 records" in text
    app.run()
    assert not app.exception and calls == []


@pytest.mark.parametrize("indexes,warnings,expected,count", [
    ({}, [], "Missing", 0),
    ({"A": {"price": None}}, [], "Missing", 0),
    ({"A": {"price": 0}, "B": {"price": 2}}, [], "Retrieval successful", 2),
    ({"A": {"price": 1}}, [], "Partial", 1),
    ({"A": {"price": 1}, "B": {"price": None}}, [], "Partial", 1),
    ({"A": {"price": 1}, "B": {"price": 2}}, ["Coverage warning"], "Partial", 2),
])
def test_market_status_requires_actual_quote_presence(indexes, warnings, expected, count):
    from langgraphagenticai.ui.workspace_presentation import market_status
    result = market_status({"indexes": indexes, "warnings": warnings}, ("A", "B"))
    assert result == {"status": expected, "usable_quotes": count, "requested_quotes": 2}
    assert market_status({"indexes": {}})["status"] == "Missing"
