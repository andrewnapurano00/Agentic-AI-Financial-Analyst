import json
from datetime import datetime,timezone
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.ui import portfolio_ideas_tab as ui
from langgraphagenticai.portfolio_ideas.contracts import PERSONAS,fingerprint

PAGE='''
from langgraphagenticai.ui.portfolio_ideas_tab import render_portfolio_ideas
render_portfolio_ideas(fmp_api_key="fake",openai_api_key="fake",model_name="chosen")
'''


def evidence():
    return dict(provider="FMP",retrieved_at=datetime.now(timezone.utc).isoformat(),warnings=[],news_basis="synthetic headlines",rows={s:dict(symbol=s,company=s,sector="Technology",price=100.,as_of="2026-10-16T20:00:00+00:00",currency="USD",currency_basis="synthetic",fundamentals={"pe_ttm":20.,"net_margin_ttm":.2},technicals={},news=[],sources={},evidence_refs={},gaps=["News"]) for s in ("AAPL","MSFT","NVDA","AMZN")})


def recommend(prompt,names,data,key,model):
    picks=[dict(symbol=s,weight_pct=100/3,thesis="Thesis",risk="Risk",monitor="Trigger") for s in list(data["rows"])[:3]]
    return dict(schema_version=2,ai_status="complete",model_calls=1,prompt=prompt,universe=names,evidence=data,perspectives={p:dict(summary="Summary",picks=picks) for p in PERSONAS},warnings=[],generated_at=datetime.now(timezone.utc).isoformat(),model=model,prompt_tokens=100,completion_tokens=100,fingerprint=fingerprint(prompt,names,data,model))


def test_generate_once_same_inputs_reruns_and_downloads_reuse(monkeypatch):
    load=Mock(return_value=evidence());load.clear=Mock();ai=Mock(side_effect=recommend)
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30).run()
    assert not app.exception and load.call_count==ai.call_count==0
    app.button(key="ideas_generate").click().run()
    assert not app.exception and load.call_count==ai.call_count==1 and len(app.tabs)==4
    assert len(app.get("download_button"))==2
    original=json.dumps(app.session_state["portfolio_ideas_result_v1"],sort_keys=True)
    app.run();assert ai.call_count==1 and load.call_count==1
    app.button(key="ideas_generate").click().run()
    assert ai.call_count==1 and json.dumps(app.session_state["portfolio_ideas_result_v1"],sort_keys=True)==original
    app.text_area(key="ideas_prompt").set_value("Different research request for quality stocks").run()
    assert ai.call_count==1 and any("earlier prompt" in i.value for i in app.info)
    app.button(key="ideas_generate").click().run()
    assert ai.call_count==2


def test_failure_preserves_result_and_evidence_and_invalid_input_is_free(monkeypatch):
    load=Mock(return_value=evidence());load.clear=Mock();ai=Mock(side_effect=recommend)
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30).run()
    app.button(key="ideas_generate").click().run()
    saved=json.dumps(app.session_state["portfolio_ideas_result_v1"],sort_keys=True)
    app.text_input(key="ideas_universe").set_value("AAPL,../bad").run()
    app.button(key="ideas_generate").click().run()
    assert load.call_count==1 and ai.call_count==1 and not app.exception
    app.text_input(key="ideas_universe").set_value("AAPL,MSFT,NVDA,AMZN").run()
    ai.side_effect=RuntimeError("apikey=private")
    app.button(key="ideas_generate").click().run()
    assert app.session_state["portfolio_ideas_result_v1"]["ai_status"]=="failed"
    assert all(v["picks"] for v in app.session_state["portfolio_ideas_result_v1"]["perspectives"].values())
    assert "private" not in str([w.value for w in app.warning])


def test_prompt_and_universe_survive_workspace_widget_cleanup(monkeypatch):
    load=Mock(side_effect=AssertionError("No provider"));ai=Mock(side_effect=AssertionError("No AI"))
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    page='''
import streamlit as st
from langgraphagenticai.ui.portfolio_ideas_tab import render_portfolio_ideas
if st.radio("Workspace",["Ideas","Other"],key="test_page")=="Ideas":render_portfolio_ideas("fake","fake","chosen")
'''
    app=AppTest.from_string(page,default_timeout=30).run()
    app.text_area(key="ideas_prompt").set_value("My custom quality research prompt").run()
    app.text_input(key="ideas_universe").set_value("AAPL, MSFT, JPM, XOM").run()
    app.checkbox(key="ideas_add_ai").set_value(False).run()
    app.radio(key="test_page").set_value("Other").run()
    app.radio(key="test_page").set_value("Ideas").run()
    assert app.text_area(key="ideas_prompt").value=="My custom quality research prompt"
    assert app.text_input(key="ideas_universe").value=="AAPL, MSFT, JPM, XOM"
    assert not app.checkbox(key="ideas_add_ai").value
    load.assert_not_called();ai.assert_not_called()


def test_force_refresh_is_explicit_and_bypasses_shared_components(monkeypatch):
    load=Mock(return_value=evidence());load.clear=Mock();ai=Mock(side_effect=recommend)
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    monkeypatch.setattr(ui,"company_inputs",lambda *a:dict(symbol="fake"))
    app=AppTest.from_string(PAGE,default_timeout=30).run()
    app.checkbox(key="ideas_force_refresh").set_value(True).run()
    assert not load.call_count and not ai.call_count
    app.button(key="ideas_generate").click().run()
    assert not app.exception and load.call_count==ai.call_count==1
    assert load.call_args.args[2]=={} and load.clear.call_count==1


def test_sparse_quote_coverage_explained_without_model_call(monkeypatch):
    data=evidence();data["rows"]={};data["warnings"]=["batch-quote: unavailable (HTTP 402)"]
    load=Mock(return_value=data);load.clear=Mock();ai=Mock(side_effect=AssertionError("No paid call"))
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30).run()
    app.button(key="ideas_generate").click().run()
    assert not app.exception and any("Only 0 of 12" in w.value for w in app.warning)
    ai.assert_not_called()


def test_invalid_model_response_not_misreported_as_bad_tickers(monkeypatch):
    load=Mock(return_value=evidence());load.clear=Mock();ai=Mock(side_effect=ValueError("secret-provider-output"))
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30).run()
    app.button(key="ideas_generate").click().run()
    assert not app.exception and any("data-ranked baskets" in i.value for i in app.info)
    assert all(v["picks"] for v in app.session_state["portfolio_ideas_result_v1"]["perspectives"].values())
    assert "secret-provider-output" not in str([w.value for w in app.warning])


def test_entrypoint_does_not_reload_removed_ideas_workflow(monkeypatch):
    import app as entry
    from pathlib import Path
    calls=[]
    loader=Mock()
    monkeypatch.setattr(entry.importlib,"reload",lambda module:calls.append(module.__name__))
    monkeypatch.setattr(entry.app_main,"load_langgraph_agenticai_app",loader)
    app=AppTest.from_file(Path(entry.__file__).resolve(),default_timeout=30).run()
    assert not app.exception
    loader.assert_called_once()
    assert not any("portfolio_ideas" in name for name in calls)


def test_without_openai_key_baskets_still_build(monkeypatch):
    from langgraphagenticai.portfolio_ideas import simple_ai
    forbidden=Mock(side_effect=AssertionError("No model"));monkeypatch.setattr(simple_ai,"build_openai_client",forbidden)
    load=Mock(return_value=evidence());load.clear=Mock();monkeypatch.setattr(ui,"load_ideas_evidence",load)
    app=AppTest.from_string("from langgraphagenticai.ui.portfolio_ideas_tab import render_portfolio_ideas; render_portfolio_ideas('fake','','gpt-5')",default_timeout=30).run()
    assert not app.button(key="ideas_generate").disabled
    app.button(key="ideas_generate").click().run()
    assert not app.exception and all(v["picks"] for v in app.session_state["portfolio_ideas_result_v1"]["perspectives"].values())
    assert app.session_state["portfolio_ideas_result_v1"]["model_calls"]==0
    forbidden.assert_not_called()


def test_use_equity_report_companies_is_metadata_only_and_free(monkeypatch):
    load=Mock(side_effect=AssertionError("No provider"));ai=Mock(side_effect=AssertionError("No model"))
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30)
    app.session_state["equity_report_tickers"]=["JPM","V","JNJ","XOM"]
    app.run();app.button(key="ideas_use_report").click().run()
    assert not app.exception and app.text_input(key="ideas_universe").value=="JPM, V, JNJ, XOM"
    load.assert_not_called();ai.assert_not_called()


def test_complete_fresh_saved_ideas_snapshot_requires_zero_new_provider_calls(monkeypatch):
    from langgraphagenticai.providers.company_evidence import credential_scope
    saved=evidence();saved["credential_scope"]=credential_scope("fake")
    load=Mock(side_effect=AssertionError("Must reuse saved data"));ai=Mock(side_effect=recommend)
    monkeypatch.setattr(ui,"load_ideas_evidence",load);monkeypatch.setattr(ui,"recommend",ai)
    app=AppTest.from_string(PAGE,default_timeout=30)
    app.session_state["portfolio_ideas_evidence_v1"]=saved
    app.session_state["ideas_saved_universe"]="AAPL,MSFT,NVDA,AMZN"
    app.run();app.button(key="ideas_generate").click().run()
    assert not app.exception and ai.call_count==1
    load.assert_not_called()
