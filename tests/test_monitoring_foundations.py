"""AX-08 disabled activation and durable OFFLINE queue/arithmetic oracles."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.monitoring import activate_monitoring
from langgraphagenticai.monitoring.models import snapshot_model,PriceEvent,Quote,concentration_advisory
from langgraphagenticai.monitoring.ledger import RehearsalLedger
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.portfolio_architect.research import demo_snapshot
from langgraphagenticai.portfolio_architect.universe import eligible_names
from langgraphagenticai.portfolio_architect.workflow import build

NOW='2026-10-24T12:00:00+00:00'
SCOPE='a'*64


def fixture():
    m=InvestorMandate(objective='Build a diversified research portfolio',method='equal')
    result=build(demo_snapshot(eligible_names(m),m.benchmark),m)
    model=snapshot_model(result,reference_time=NOW)
    quotes=tuple(Quote(ticker=p.ticker,price=p.price*(10 if i==0 else 1),currency='USD',provider=p.source,
        as_of=NOW,retrieved_at=NOW,share_basis='verified_same_share_basis',adjustment_evidence_id='synthetic-basis') for i,p in enumerate(model.positions))
    event=PriceEvent(event_id='event-1',credential_scope=SCOPE,quotes=quotes)
    return result,model,event


def ledger(tmp_path):
    result,model,event=fixture()
    path=tmp_path/'offline.db'
    store=RehearsalLedger(path)
    plan=store.register('owner-a',model,SCOPE,'2026-10-25T00:00:00+00:00')
    store.set_rehearsal_enabled('owner-a',plan,True)
    return store,path,plan,model,event


def test_activation_hard_disabled_and_immutable_baseline():
    with pytest.raises(ValueError,match='disabled'):activate_monitoring()
    result,model,event=fixture(); original=result.model_dump()
    with pytest.raises(ValueError):model.cash=.5
    answer=concentration_advisory(model,event,NOW)
    assert answer['new_weights'][model.positions[0].ticker]==pytest.approx(.9/1.81)
    assert sum(answer['new_weights'].values())+answer['new_cash']==pytest.approx(1)
    assert sum(answer['proposed_target_weights'].values())==pytest.approx(1)
    assert all(w<=model.position_cap+1e-9 for t,w in answer['proposed_target_weights'].items() if t!='CASH')
    assert answer['model_calls']==0 and answer['execution']=='unavailable'
    assert result.model_dump()==original


def test_restart_duplicates_collisions_approval_and_isolation(tmp_path):
    store,path,plan,model,event=ledger(tmp_path)
    assert store.submit('owner-a',plan,event,NOW)=='queued'
    assert store.submit('owner-a',plan,event,NOW)=='queued'
    claim=store.claim('owner-a',NOW)
    restarted=RehearsalLedger(path)
    assert restarted.claim('owner-a',NOW) is None
    later='2026-10-24T12:01:01+00:00'
    second=restarted.claim('owner-a',later)
    assert restarted.finish(claim,later)=='lease_lost'
    assert restarted.finish(second,later)=='done'
    assert restarted.submit('owner-a',plan,event,later)=='done'
    assert len(restarted.advisories('owner-a',plan))==1
    assert restarted.advisories('owner-b',plan)==[]
    with pytest.raises(ValueError): restarted.decide('owner-b',plan,event.event_id,'approved')
    assert restarted.decide('owner-a',plan,event.event_id,'approved')=='advisory_only_no_portfolio_change'
    assert restarted.decide('owner-a',plan,event.event_id,'approved')=='advisory_only_no_portfolio_change'
    with pytest.raises(ValueError):restarted.decide('owner-a',plan,event.event_id,'rejected')
    with pytest.raises(ValueError):restarted.submit('owner-a',plan,event.model_copy(update={'quotes':event.quotes[:-1]}),later)


@pytest.mark.parametrize('change',['partial','stale','failed','unknown_basis','delayed','provider'])
def test_failed_refresh_does_not_invent_signal(tmp_path,change):
    store,path,plan,model,event=ledger(tmp_path)
    quotes=list(event.quotes)
    if change=='partial':quotes.pop()
    if change=='stale':quotes[0]=quotes[0].model_copy(update={'retrieved_at':'2026-10-23T12:00:00+00:00','as_of':'2026-10-23T11:00:00+00:00'})
    if change=='failed':quotes[0]=quotes[0].model_copy(update={'status':'failed'})
    if change=='unknown_basis':quotes[0]=quotes[0].model_copy(update={'share_basis':'unknown'})
    if change=='delayed':quotes[0]=quotes[0].model_copy(update={'as_of':'2026-10-18T12:00:00+00:00'})
    if change=='provider':quotes[0]=quotes[0].model_copy(update={'provider':'Other'})
    event=event.model_copy(update={'quotes':tuple(quotes)})
    assert store.submit('owner-a',plan,event,NOW)=='queued'
    assert store.process_next('owner-a',NOW)=='blocked'
    assert not store.advisories('owner-a',plan)


def test_disable_stops_claim_and_inflight_commit(tmp_path,monkeypatch):
    store,path,plan,model,event=ledger(tmp_path)
    store.submit('owner-a',plan,event,NOW)
    claim=store.claim('owner-a',NOW)
    store.set_rehearsal_enabled('owner-a',plan,False)
    analysis=Mock(side_effect=AssertionError('No analysis after disable'))
    monkeypatch.setattr('langgraphagenticai.monitoring.ledger.concentration_advisory',analysis)
    assert store.finish(claim,NOW)=='lease_lost'
    assert store.claim('owner-a',NOW) is None
    assert store.submit('owner-a',plan,event.model_copy(update={'event_id':'new'}),NOW)=='disabled'
    assert not store.advisories('owner-a',plan)
    analysis.assert_not_called()


def test_bounded_timeout_retries_expiry_scope_and_event_budget(tmp_path):
    store,path,plan,model,event=ledger(tmp_path)
    assert store.submit('owner-a',plan,event.model_copy(update={'credential_scope':'b'*64}),NOW)=='credential_expired_or_changed'
    assert store.submit('owner-a',plan,event,'2026-10-26T12:00:00+00:00')=='credential_expired_or_changed'
    store.submit('owner-a',plan,event,NOW)
    for expected in ['queued','queued','dead_letter']:
        claim=store.claim('owner-a',NOW)
        assert store.finish(claim,NOW,transient_failure=True)==expected
    assert not store.advisories('owner-a',plan) and store.claim('owner-a',NOW) is None
    other=RehearsalLedger(tmp_path/'budget.db')
    key=other.register('owner-a',model,SCOPE,'2026-10-25T00:00:00Z',max_events=1)
    other.set_rehearsal_enabled('owner-a',key,True)
    assert other.submit('owner-a',key,event,NOW)=='queued'
    assert other.submit('owner-a',key,event.model_copy(update={'event_id':'new'}),NOW)=='budget_exhausted'


def test_no_change_rejection_and_tampered_claim_payload(tmp_path):
    store,path,plan,model,event=ledger(tmp_path)
    unchanged=event.model_copy(update={'event_id':'flat','quotes':tuple(q.model_copy(update={'price':p.price}) for q,p in zip(event.quotes,model.positions))})
    store.submit('owner-a',plan,unchanged,NOW)
    claim=store.claim('owner-a',NOW)
    claim['evidence']=event # Caller alteration cannot replace canonical stored evidence.
    assert store.finish(claim,NOW)=='done'
    assert not store.advisories('owner-a',plan)
    store.submit('owner-a',plan,event,NOW);store.process_next('owner-a',NOW)
    assert store.decide('owner-a',plan,event.event_id,'rejected')=='advisory_only_no_portfolio_change'
    assert store.advisories('owner-a',plan)[0]['decision']=='rejected'


def test_owner_namespaces_plan_integrity_and_expiry_after_claim(tmp_path):
    store,path,plan,model,event=ledger(tmp_path)
    with pytest.raises(ValueError):
        store.register('owner-a',model.model_copy(update={'cash':.5}),SCOPE,'2026-10-25T00:00:00Z')
    store.register('owner-b',model,'b'*64,'2026-10-25T00:00:00Z')
    store.set_rehearsal_enabled('owner-b',plan,True)
    store.submit('owner-a',plan,event,NOW)
    assert store.claim('owner-b',NOW) is None
    store.submit('owner-b',plan,event.model_copy(update={'credential_scope':'b'*64}),NOW)
    assert store.process_next('owner-b',NOW)=='done'
    assert store.advisories('owner-a',plan)==[]

    assert len(store.advisories('owner-b',plan))==1
    # Expiry is rechecked during claim, not just submission.
    assert store.claim('owner-a','2026-10-26T00:00:00Z') is None
    assert store.advisories('owner-a',plan)==[]


def test_extreme_prices_do_not_create_nonfinite_weights():
    result,model,event=fixture()
    first=model.positions[0].model_copy(update={'price':1e-300})
    model=model.model_copy(update={'positions':(first,)+model.positions[1:]})
    event=event.model_copy(update={'quotes':(event.quotes[0].model_copy(update={'price':1e300}),)+event.quotes[1:]})
    with pytest.raises(ValueError,match='valuation'):concentration_advisory(model,event,NOW)


def test_ui_requires_explicit_saved_result_and_never_enables_monitoring(monkeypatch):
    result,model,event=fixture()
    import langgraphagenticai.ui.monitoring_plan as ui
    monkeypatch.setattr(ui,'snapshot_model',lambda *args,**kwargs:model)
    monkeypatch.setattr('requests.sessions.Session.request',Mock(side_effect=AssertionError('No HTTP')))
    app=AppTest.from_string("import streamlit as st\nfrom langgraphagenticai.portfolio_architect.schemas import PortfolioRecommendation\nfrom langgraphagenticai.ui.monitoring_plan import render_monitoring_plan\nrender_monitoring_plan(PortfolioRecommendation.model_validate(st.session_state['fixture']))",default_timeout=30)
    app.session_state['fixture']=result.model_dump()
    app.run();assert not app.exception
    assert next(b for b in app.button if b.label=='Prepare monitoring plan').disabled
    app.session_state['architect_saved']={result.id:result.model_dump()}
    app.run()
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label=='Prepare monitoring plan').click().run()
    assert not app.exception
    assert app.session_state['monitoring_disabled_plans'][model.fingerprint]==model
    assert next(b for b in app.button if b.label=='Enable monitoring').disabled
    assert not any('ledger' in k for k in app.session_state.filtered_state)
