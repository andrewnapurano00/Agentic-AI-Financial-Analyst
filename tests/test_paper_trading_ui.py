"""Manual controls preserve accounts and never call models on ordinary reruns."""
import json
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.paper_trading import workflow
from langgraphagenticai.paper_trading.engine import create_experiment
from langgraphagenticai.paper_trading.personas import DEFAULT_UNIVERSE
from langgraphagenticai.ui import paper_trading_tab as ui

PAGE = """
from langgraphagenticai.ui.paper_trading_tab import render_paper_trading_tab
render_paper_trading_tab(fmp_api_key="synthetic",openai_api_key="synthetic",model_name="synthetic")
"""


def create(app, mode="Demo"):
    app.run()
    app.selectbox[0].set_value(mode)
    next(b for b in app.button if b.label == "Create experiment").click().run()
    assert not app.exception
    return app


def active(app):
    return app.session_state["paper_experiments_v1"][app.session_state["paper_active_experiment"]]


def test_demo_round_monitor_and_download_reruns_are_free(monkeypatch):
    forbidden=Mock(side_effect=AssertionError("No provider/model"))
    monkeypatch.setattr(ui,"load_paper_market",forbidden)
    monkeypatch.setattr(workflow,"propose",forbidden)
    app=create(AppTest.from_string(PAGE,default_timeout=30))
    app.button(key="paper_run").click().run()
    assert not app.exception and len(active(app)["rounds"]) == 1
    assert all(a["trades"] for a in active(app)["accounts"].values())
    before=json.dumps(active(app),sort_keys=True)
    app.run()
    assert json.dumps(active(app),sort_keys=True) == before
    assert len(app.get("download_button")) == 2
    forbidden.assert_not_called()
    app.button(key="paper_run").click().run()
    assert not app.exception and len(active(app)["rounds"]) == 2


def test_fmp_round_is_explicit_and_cannot_repeat_success(monkeypatch):
    exp=create_experiment("fixture",DEFAULT_UNIVERSE,mode="FMP + AI")
    packet=workflow.demo_market(exp);packet["mode"]="FMP + AI"
    from langgraphagenticai.paper_trading.engine import snapshot_id
    packet["id"]=snapshot_id(packet)
    loader=Mock(return_value=packet);loader.clear=Mock()
    decider=Mock(side_effect=workflow.demo_proposal)
    monkeypatch.setattr(ui,"load_paper_market",loader)
    monkeypatch.setattr(workflow,"propose",decider)
    app=create(AppTest.from_string(PAGE,default_timeout=30),"FMP + AI")
    assert loader.call_count == 0 and decider.call_count == 0
    assert app.button(key="paper_run").disabled
    app.button(key="paper_refresh").click().run()
    assert not app.exception and loader.call_count == 1 and decider.call_count == 0
    app.button(key="paper_run").click().run()
    assert not app.exception and decider.call_count == 4 and app.button(key="paper_run").disabled
    app.run()
    assert decider.call_count == 4 and loader.call_count == 1
    snapshot=json.dumps(active(app),sort_keys=True)
    loader.side_effect=RuntimeError("apikey=do-not-show")
    app.button(key="paper_refresh").click().run()
    assert not app.exception and json.dumps(active(app),sort_keys=True) == snapshot
    assert "do-not-show" not in str([w.value for w in app.warning])


def test_export_redacts_keys_and_keeps_paper_account_reconciliation():
    exp=create_experiment("apikey=secret",DEFAULT_UNIVERSE)
    exp=workflow.run_round(exp,workflow.demo_market(exp))
    exp["name"]="literal-configured-key"
    exported=ui.export_experiment(exp,("literal-configured-key",))
    assert b"literal-configured-key" not in exported
    data=json.loads(exported)
    assert data["mode"] == "Demo" and set(data["accounts"]) == {"Warren","George","Ray","Cathie"}
    assert all(a["cash"] >= 0 and a["trades"] for a in data["accounts"].values())


def test_allocate_route_preserves_other_tabs_and_passes_shared_settings(monkeypatch):
    from langgraphagenticai import main
    got=[]
    monkeypatch.setattr(main.LoadStreamlitUI,"load_streamlit_ui",lambda self:dict(active_page="Portfolio Lab",FMP_API_KEY="fmp",OPENAI_API_KEY="openai",selected_model="gpt-5"))
    for name in ("render_portfolio_optimizer_tab","render_ai_portfolio_manager_tab","render_market_strip","render_terminal_status","_render_status_panel"):
        monkeypatch.setattr(main,name,lambda *a,**kw:None)
    monkeypatch.setattr(main,"render_command_bar",lambda:"")
    from langgraphagenticai.ui import portfolio_ideas_tab
    ideas=Mock(side_effect=AssertionError("Removed Ideas tab must not render"))
    monkeypatch.setattr(portfolio_ideas_tab,"render_portfolio_ideas",ideas)
    monkeypatch.setattr(main,"render_ai_portfolio_manager_tab",lambda **kwargs:got.append(kwargs))
    app=AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()",default_timeout=30).run()
    assert not app.exception and [tab.label for tab in app.tabs] == ["Optimizer","AI Portfolio Manager"]
    assert got == [dict(fmp_api_key="fmp",openai_api_key="openai",model_name="gpt-5",marketaux_api_key="")]
    ideas.assert_not_called()
