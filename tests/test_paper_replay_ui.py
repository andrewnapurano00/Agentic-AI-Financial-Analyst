import json
from unittest.mock import Mock
from streamlit.testing.v1 import AppTest
from langgraphagenticai.paper_trading import replay
from langgraphagenticai.ui import paper_replay_tab as ui

PAGE='''
from langgraphagenticai.ui.paper_trading_tab import render_paper_trading_tab
render_paper_trading_tab(fmp_api_key="fake",openai_api_key="fake",model_name="fake")
'''


def active(app):
    return app.session_state["paper_replays_v1"][app.session_state["replay_active"]]


def create(app,ai=False):
    app.run()
    app.radio(key="paper_workflow").set_value("Historical replay").run()
    if ai:app.selectbox[0].set_value("FMP history + AI")
    next(b for b in app.button if b.label=="Create historical experiment").click().run()
    assert not app.exception
    return app


def test_demo_explicit_loading_advance_decision_log_and_saved_reruns(monkeypatch):
    forbidden=Mock(side_effect=AssertionError("No AI or provider"))
    monkeypatch.setattr(replay,"propose",forbidden)
    monkeypatch.setattr(ui,"load_paper_history",forbidden)
    app=create(AppTest.from_string(PAGE,default_timeout=30))
    assert not active(app)["loaded"]
    app.button(key="replay_load").click().run()
    assert not app.exception and active(app)["loaded"] and active(app)["cursor"]==0
    app.button(key="replay_next").click().run()
    assert not app.exception and active(app)["cursor"]==1
    assert len(next(iter(active(app)["rounds"].values())))==4
    before=json.dumps(active(app),sort_keys=True)
    app.run()
    app.radio(key="paper_workflow").set_value("Manual paper rounds").run()
    app.radio(key="paper_workflow").set_value("Historical replay").run()
    assert json.dumps(active(app),sort_keys=True)==before
    assert len(app.get("download_button"))==3
    forbidden.assert_not_called()


def test_ai_load_free_next_calls_four_and_rerun_free(monkeypatch):
    def history(universe,benchmark,start,end,key):return replay.demo_history(list(universe),benchmark,start,end)
    loader=Mock(side_effect=history);loader.clear=Mock()
    from langgraphagenticai.paper_trading.workflow import demo_proposal
    decider=Mock(side_effect=demo_proposal)
    monkeypatch.setattr(ui,"load_paper_history",loader)
    monkeypatch.setattr(replay,"propose",decider)
    app=create(AppTest.from_string(PAGE,default_timeout=30),True)
    loader.assert_not_called();decider.assert_not_called()
    app.button(key="replay_load").click().run()
    assert not app.exception and loader.call_count==1 and decider.call_count==0
    app.button(key="replay_next").click().run()
    assert not app.exception and decider.call_count==4
    app.run()
    assert decider.call_count==4 and loader.call_count==1


def test_new_experiment_becomes_selected_without_erasing_prior_account():
    app=create(AppTest.from_string(PAGE,default_timeout=30))
    first=active(app)["id"]
    app.button(key="replay_load").click().run()
    app.button(key="replay_next").click().run()
    saved=json.dumps(active(app),sort_keys=True)
    next(b for b in app.button if b.label=="Create historical experiment").click().run()
    assert not app.exception and active(app)["id"]!=first
    assert json.dumps(app.session_state["paper_replays_v1"][first],sort_keys=True)==saved
    assert not active(app)["loaded"]
