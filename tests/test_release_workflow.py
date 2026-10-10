"""P05 D01-D07: actual routes with synthetic services and independent saved evidence."""
from copy import deepcopy
import pytest
from test_workspace_handoffs import routing, app_at
from test_guided_research import stub, tools
from test_investment_brief import eligible_result, REFERENCE


def test_discovery_guided_saved_brief(monkeypatch, routing):
    from langgraphagenticai.ui import guided_research_tab as guided, investment_brief as shared
    from langgraphagenticai.research.guided_workflow import prepare, run
    from langgraphagenticai.ui.streamlitui import loadui
    counts = {'model': 0, 'provider': 0}
    def model(*args):
        counts['model'] += 1
        return stub(*args)
    def provider(*args):
        counts['provider'] += 1
        return tools(*args)
    monkeypatch.setattr(loadui, '_resolve_secret', lambda *args: 'synthetic')
    monkeypatch.setattr(guided, 'prepare', lambda cfg, **kw: prepare(cfg, model_call=model))
    monkeypatch.setattr(guided, 'run', lambda plan, cfg, **kw: run(plan, cfg, model_call=model, tool_call=provider))
    original = shared.saved_inputs
    monkeypatch.setattr(shared, 'saved_inputs', lambda result, ticker, ref: original(result, ticker, REFERENCE))
    app = app_at('Introduction')
    app.button(key='intro_handoff_Research').click().run()
    app.radio(key='research_mode').set_value('Guided research').run()
    assert app.text_input(key='guided_symbol').value == 'AAPL'
    app.checkbox(key='guided_unknown_ack').check().run()
    assert counts == {'model': 0, 'provider': 0}
    app.button(key='guided_prepare').click().run()
    app.button(key='guided_run').click().run()
    assert not app.exception
    assert counts == {'model': 2, 'provider': 3}
    guided_saved = deepcopy(app.session_state['guided_result'])
    assert guided_saved['steps'][-1]['status'] == 'failed'
    assert guided_saved['answer']['facts'][0]['basis'] == 'annual FY'
    # D03/D07: this separate saved TTM audit has explicit synthetic USD quote currency.
    saved = eligible_result()
    app.session_state['dr_history'] = [deepcopy(saved)]
    app.session_state['dr_result_tabs_audit-test'] = 'Investment brief & scenarios'
    app.sidebar.radio[0].set_value('Deep Research').run()
    assert not app.exception
    next(n for n in app.number_input if n.label == 'Bear earnings change (%)').set_value(-100).run()
    app.run()
    assert app.session_state['dr_history'] == [saved]
    assert app.session_state['guided_result'] == guided_saved
    assert counts == {'model': 2, 'provider': 3}
    other = app_at('Research')
    assert 'guided_result' not in other.session_state
    assert 'dr_history' not in other.session_state or not other.session_state['dr_history']


@pytest.mark.parametrize('workspace', ['Introduction', 'Top Movers', 'Research', 'Equity Report', 'Stock Screener', 'Portfolio Lab', 'Deep Research', 'Deep Research V2'])
def test_eight_route_readiness_render_only(routing, workspace):
    app = app_at(workspace)
    app.run()
    assert not app.exception
    assert routing['model'] == 0
