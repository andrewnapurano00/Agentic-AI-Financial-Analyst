"""Streamlit interaction/state regressions, fully offline."""
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui import portfolio_architect_tab as ui
from langgraphagenticai.portfolio_architect import committee

PAGE="""
from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect
render_portfolio_architect()
"""


def prepared():
    a=AppTest.from_string(PAGE,default_timeout=30).run()
    a.button(key="architect_interpret").click().run()
    assert not a.exception
    return a


def build_app(a):
    next(b for b in a.button if b.label == "Build portfolio").click().run()
    assert not a.exception
    return a


def test_mocked_live_build_save_rerun_no_extra_calls(monkeypatch):
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.mandate import default_mandate
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    m,_=default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    provider=Mock(return_value=demo_snapshot(eligible_names(m),m.benchmark))
    monkeypatch.setattr(ui,"collect",provider)
    a=AppTest.from_string(PAGE.replace("render_portfolio_architect()", "render_portfolio_architect(fmp_api_key='fixture-key')"),default_timeout=30).run()
    a.button(key="architect_interpret").click().run(); build_app(a)
    result=a.session_state["architect_result"]
    assert len(result["holdings"]) == 10 and len(a.get("download_button")) == 3
    a.button(key="architect_save").click().run(); a.run()
    assert result == a.session_state["architect_result"]
    provider.assert_called_once()


def test_live_missing_credentials_does_not_collect(monkeypatch):
    provider=Mock(side_effect=AssertionError("No call"));monkeypatch.setattr(ui,"collect",provider)
    a=build_app(prepared())
    assert a.error and "Configure FMP" in a.error[0].value
    provider.assert_not_called()


def test_revised_prompt_requires_interpret_and_editor_validates():
    a=prepared()
    a.text_area(key="architect_prompt").set_value("A revised defensive portfolio question").run()
    assert any("differs" in v.value for v in a.caption)
    a.number_input(key="architect_edit_1_holdings").set_value(5)
    a.number_input(key="architect_edit_1_cap").set_value(5.)
    build_app(a)
    assert a.error and "infeasible" in a.error[0].value


def test_entrypoint_has_no_trader_or_demo_controls():
    from pathlib import Path
    a=AppTest.from_file(Path(__file__).resolve().parents[1]/"portfolio_architect_app.py",default_timeout=30).run()
    assert not a.exception and not a.radio


def test_failed_provider_collection_shows_causes_and_keeps_saved_result(monkeypatch):
    from langgraphagenticai.portfolio_architect.schemas import EvidenceSnapshot
    failed=EvidenceSnapshot(id='fixture-failed',mode='FMP live',retrieved_at='2026-10-19T12:00:00+00:00',
        securities=[],benchmark=None,warnings=['FMP batch-quote: HTTP 402: endpoint access unavailable for the configured FMP plan.'],
        excluded={'MSFT':'Unique quote unavailable; check provider access or collection warnings.'},universe_version='fixture')
    loader=Mock(return_value=failed);monkeypatch.setattr(ui,'collect',loader)
    a=AppTest.from_string("from langgraphagenticai.ui.portfolio_architect_tab import render_portfolio_architect; render_portfolio_architect(fmp_api_key='fixture-key')",default_timeout=30).run()
    a.button(key='architect_interpret').click().run();build_app(a)
    assert a.error and 'provider validation' in a.error[0].value
    assert any(e.label=='Latest collection diagnostics' for e in a.expander)
    assert any('HTTP 402' in m.value for m in a.markdown)
    assert any('Unique quote unavailable' in str(d.value) for d in a.dataframe)
    a.run();loader.assert_called_once()


def test_oversize_export_preserves_report_other_downloads_and_rerun(monkeypatch):
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.mandate import default_mandate
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    from langgraphagenticai.portfolio_architect.export import ExportSizeError
    m, _ = default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    provider = Mock(return_value=demo_snapshot(eligible_names(m), m.benchmark))
    monkeypatch.setattr(ui, "collect", provider)
    monkeypatch.setattr(ui, "evidence_download", Mock(side_effect=ExportSizeError("Evidence too large; saved report remains available.")))
    a = AppTest.from_string(PAGE.replace("render_portfolio_architect()", "render_portfolio_architect(fmp_api_key='fixture-key')"), default_timeout=60).run()
    a.button(key="architect_interpret").click().run()
    build_app(a)
    before = a.session_state["architect_result"]
    assert any("saved report" in w.value for w in a.warning)
    assert len(a.get("download_button")) == 2
    a.button(key="architect_save").click().run()
    a.run()
    assert not a.exception and a.session_state["architect_result"] == before
    provider.assert_called_once()


@pytest.mark.parametrize("retry",[False,True])
def test_sector_ai_thesis_and_risk_audit_survive_controls_and_reruns(monkeypatch,retry):
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.mandate import default_mandate
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
    m,_ = default_mandate("Build an aggressive five-year growth portfolio focused on AI with diversified risk.")
    provider = Mock(return_value=demo_snapshot(eligible_names(m),m.benchmark))
    monkeypatch.setattr(ui,"collect",provider)
    review_attempts=[]
    def structured(contract,packet,*args,**kwargs):
        usage={"status":"completed","input_tokens":123,"output_tokens":456,"attempts":1}
        if contract is InvestorMandate:
            return m, usage
        review_attempts.append(True)
        if retry and len(review_attempts)==1:
            raise ValueError("Sector research packet cannot fit the 42KB evidence budget.")
        picks=[]
        for row in packet["candidates"]:
            metric=next((f for f in row["facts"] if f["field"] not in {"price","screen_score","revenue_cagr_3y"}),row["facts"][0])
            picks.append({"ticker":row["ticker"],"conviction":"high","reason":"diversification","evidence_ids":[metric["id"]]+[f["id"] for f in row["facts"] if row["asset"]=="stock" and f["field"]=="revenue_cagr_3y"],
                "analysis":{"framework":row["sector_lens"]["framework"],"conviction_summary":"Positive saved sector evidence supports conviction; future growth remains uncertain.","thesis":"Saved sector evidence supports this conditional research thesis.",
                            "risks":["Sector profitability could deteriorate."],"thesis_breaker":"Reassess if the next filing shows sustained margin deterioration.",
                            "portfolio_role":"core","missing_inputs":["Forward estimates remain unavailable."]}})
        return contract.model_validate({"picks":picks,"concerns":["concentration","missing_data","valuation_uncertainty"],"rejected":[]}),usage
    call=Mock(side_effect=structured)
    monkeypatch.setattr(committee,"structured_call",call)
    a=AppTest.from_string(PAGE.replace("render_portfolio_architect()","render_portfolio_architect(fmp_api_key='fixture-key',openai_api_key='fixture-ai')"),default_timeout=60).run()
    assert a.checkbox(key="architect_use_ai").value
    a.button(key="architect_interpret").click().run();build_app(a)
    if retry:
        assert a.session_state["architect_result"]["ai_review_status"]["state"]=="failed"
        assert a.session_state["architect_result"]["usage"][-1]["attempts"]==0
        a.button(key="architect_retry_ai").click().run()
        assert not a.exception
    result=a.session_state["architect_result"]
    assert result["method_used"] == "ai_risk_budget"
    assert result["mandate"]["investment_style"] == "growth"
    assert result["ai_review_status"]["state"] == "completed"
    allocation=next(d.value for d in a.dataframe if "Conviction (subjective)" in d.value.columns)
    assert "Positive saved sector evidence" in allocation.iloc[0]["Conviction (subjective)"]
    assert result["allocation_audit"]["status"] == "available"
    assert all(h["ai_analysis"] for h in result["holdings"])
    assert any("AI investment thesis" in md.value for md in a.markdown)
    a.selectbox(key="architect_edit_1_method").select("min_variance").run()
    a.button(key="architect_save").click().run();a.run()
    assert not a.exception and a.session_state["architect_result"] == result
    assert call.call_count == (3 if retry else 2)
    provider.assert_called_once()
