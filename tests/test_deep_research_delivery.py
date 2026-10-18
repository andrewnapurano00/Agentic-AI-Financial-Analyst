"""Automatic terminal delivery, clean presentation and forward packet regressions."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import io
import json
import pytest
from pdfminer.high_level import extract_text
from langgraphagenticai.deep_research.manager import ResearchManager
from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research.delivery import finish_saved, saved_report_drafts, executive_saved_result
from langgraphagenticai.deep_research.prompt_context import evidence_context
from langgraphagenticai.deep_research.presentation import build_research_pdf, clean_report_markdown
from langgraphagenticai.tools.serper_tools import SerperClient

ACCEPT='{"corrections": [], "unresolved": []}'
REPORT="## Executive Investment Thesis\nAAPL revenue is USD 5 as of2026 [E001].\n## Risks\nDemand.\n## Thesis invalidation\nMargins weaken."

def manager(replies,**kwargs):
    llm=Mock()
    llm.invoke.side_effect=[SimpleNamespace(content=r) if isinstance(r,str) else r for r in replies]
    source=Mock()
    source.collect.return_value=[Evidence("","AAPL","income","Income","Synthetic",[{"revenue":5}])]
    return ResearchManager(llm,source,SerperClient(""),auto_finish=True,**kwargs)


def test_review_timeout_recovers_automatically_without_recollection():
    m=manager(['{}',REPORT,TimeoutError(),ACCEPT])
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["status"]=="complete" and result["report"]==REPORT
    assert m.llm.invoke.call_count==4 and m.financial_source.collect.call_count==1
    assert len(result["automatic_recovery"])==1


@pytest.mark.parametrize("failure",[TimeoutError(),ValueError("bad review"),RuntimeError("provider unavailable")])
def test_persistent_review_failure_finishes_with_facts_not_failed_recommendation(failure):
    m=manager(['{}',REPORT,failure,failure])
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["status"]=="complete" and result["review_status"]=="evidence_only"
    assert result["delivery_outcome"]=="limited_evidence" and "No rating" in result["report"]
    assert result["delivery_audit"]["report"]==REPORT
    assert "Retry" not in result["report"] and "retry" not in result["report"]
    assert m.llm.invoke.call_count==4 and m.financial_source.collect.call_count==1


def test_unresolved_review_is_rewritten_once_and_checked():
    unresolved=json.dumps(dict(corrections=[],unresolved=["Unsupported claim"]))
    m=manager(['{}',REPORT,unresolved,REPORT,ACCEPT])
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["status"]=="complete" and result.get("delivery_outcome") is None
    assert m.llm.invoke.call_count==5
    assert "Unsupported claim" in str(m.llm.invoke.call_args_list[3])


def test_invalid_citations_are_not_silently_finalized():
    m=manager(['{}',REPORT.replace('E001','E999'),ACCEPT,REPORT.replace('E001','E999'),ACCEPT])
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["delivery_outcome"]=="limited_evidence"
    assert "E999" not in result["report"]


def test_budget_guard_blocks_automatic_model_calls_but_delivers_terminal_overview():
    m=manager([],max_estimated_cost_usd=0.)
    m.llm.model_name='gpt-5'
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["status"]=="complete" and result["delivery_outcome"]=="limited_evidence"
    m.llm.invoke.assert_not_called()
    assert m.financial_source.collect.call_count==1


def test_collection_failure_delivers_terminal_no_rating_without_model():
    m=manager([]);m.financial_source.collect.side_effect=TimeoutError()
    result=m.run(ResearchRequest(["AAPL"],include_news=False))
    assert result["status"]=="complete" and "No rating" in result["report"]
    m.llm.invoke.assert_not_called()


def test_saved_completion_is_pure_and_keeps_failed_draft_and_zero_values():
    original=dict(status='review_pending',report='Unchecked BUY [E999]',draft='Unchecked BUY [E999]',request={'symbols':['AAPL']},comparison=[{'Ticker':'AAPL','Sector':'Technology','RSI 14':0}],evidence=[],warnings=['Internal check failed'])
    snapshot=deepcopy(original)
    final=finish_saved(original)
    assert original==snapshot and final['status']=='complete'
    assert final['delivery_audit']['report']==original['report']
    assert 'Unchecked BUY' not in final['report'] and '0.00' in final['report']
    assert finish_saved(final) is final


def test_legacy_fallback_exposes_original_draft_without_replacing_safe_report():
    final = dict(status="complete", delivery_outcome="limited_evidence", report="No rating",
                 delivery_audit=dict(draft=REPORT, report=REPORT))
    snapshot = deepcopy(final)
    assert saved_report_drafts(final) == [REPORT]
    assert final == snapshot
    assert saved_report_drafts(dict(status="complete", report=REPORT)) == []


def test_failed_rewrite_retains_original_and_replacement_drafts():
    unresolved = json.dumps(dict(corrections=[], unresolved=["Unsupported claim"]))
    replacement = REPORT.replace("Demand.", "Replacement analysis.")
    m = manager(['{}', REPORT, unresolved, replacement, unresolved])
    result = m.run(ResearchRequest(["AAPL"], include_news=False))
    drafts = saved_report_drafts(result)
    assert drafts == [REPORT, replacement]
    assert result["delivery_outcome"] == "limited_evidence"
    assert m.llm.invoke.call_count == 5
    assert m.financial_source.collect.call_count == 1


def test_single_pass_writes_once_without_review_rewrite_or_fallback():
    m = manager(['{}', REPORT], single_pass=True, allow_clarification_retry=False)
    result = m.run(ResearchRequest(["AAPL"], include_news=False))
    assert result["status"] == "complete" and result["report"] == REPORT
    assert result["report_mode"] == "single_pass" and result["review_status"] == "not_performed"
    assert result["delivery_outcome"] == "executive_report"
    assert [d["stage"] for d in m.diagnostics] == ["plan", "draft"]
    assert m.llm.invoke.call_count == 2
    assert m.financial_source.collect.call_count == 1
    assert not result.get("automatic_recovery")


def test_single_pass_mechanical_issues_stay_in_audit_without_triggering_model():
    invalid = REPORT.replace("E001", "E999")
    m = manager(['{}', invalid], single_pass=True,
                deterministic_validator=lambda *_: ["Unknown evidence ID E999"])
    result = m.run(ResearchRequest(["AAPL"], include_news=False))
    assert result["status"] == "complete" and result["report"] == invalid
    assert "Unknown evidence ID E999" in result["report_warnings"]
    assert m.llm.invoke.call_count == 2
    assert not any(d["stage"] == "review" for d in m.diagnostics)


@pytest.mark.parametrize("failure", [TimeoutError(), "Before I proceed, what horizon should I use?"])
def test_single_pass_generation_failure_has_no_automatic_second_attempt(failure):
    m = manager(['{}', failure], single_pass=True, allow_clarification_retry=False)
    result = m.run(ResearchRequest(["AAPL"], include_news=False))
    assert result["status"] == "incomplete"
    assert result["delivery_outcome"] == "incomplete"
    assert m.llm.invoke.call_count == 2
    assert m.financial_source.collect.call_count == 1


def test_legacy_overview_restores_first_full_memo_purely_and_preserves_review_audit():
    legacy = finish_saved(dict(status="needs_review", draft=REPORT, report=REPORT,
                               evidence=[], comparison=[], request={"symbols": ["AAPL"]},
                               report_warnings=["Unsupported sentence"]))
    snapshot = deepcopy(legacy)
    restored = executive_saved_result(legacy)
    assert restored["status"] == "complete" and restored["report"] == REPORT
    assert restored["delivery_outcome"] == "executive_report"
    assert restored["review_status"] == "not_performed"
    assert restored["delivery_audit"] == legacy["delivery_audit"]
    assert legacy == snapshot
    assert executive_saved_result(restored) is restored
    text = clean_report_markdown(restored["report"])
    assert "E001" not in text and "USD 5" in text


def test_standard_ui_factory_enforces_single_pass(monkeypatch):
    from langgraphagenticai.ui import deep_research_tab as ui
    monkeypatch.setattr(ui, "get_finance_tools", lambda *_: [])
    m = ui._manager("synthetic", "test", "", "", "")
    assert m.single_pass and not m.interpretive_review and not m.allow_clarification_retry


def test_estimate_packet_keeps_legacy_numeric_fields_and_multiple_fiscal_years():
    rows=[dict(symbol='AAPL',date=f'{y}-09-30',estimatedEpsAvg=eps,estimatedRevenueAvg=eps*100,numberAnalystEstimatedEps=20) for y,eps in ((2027,10),(2028,12),(2029,14))]
    original=deepcopy(rows)
    packet=evidence_context([Evidence('E001','AAPL','estimates','Consensus','Synthetic',rows)],6000)
    assert len(packet[0]['data'])==3
    assert packet[0]['data'][1]['estimatedEpsAvg']==12
    assert packet[0]['data'][1]['estimatedRevenueAvg']==1200
    assert rows==original


def test_full_reader_report_removes_statement_references_preserves_financial_meaning():
    report='## Executive Investment Thesis\nAccording to the income statement, revenue rose12% [E001].\n## Cash generation\nThe cash flow statement shows free cash flow was USD5B (cash_flow_ttm; E001).\n## News\n[New product](https://example.com/news).'
    clean=clean_report_markdown(report)
    assert 'statement' not in clean.lower() and 'E001' not in clean and 'cash_flow_ttm' not in clean
    assert '12%' in clean and 'USD5B' in clean and 'https://example.com/news' in clean


def test_pdf_is_reader_facing_with_periods_and_raw_audit_unchanged():
    result=dict(status='complete',report=REPORT,request={'symbols':['AAPL'],'horizon':'1-3 years'},comparison=[{'Ticker':'AAPL','Sector':'Technology','Statement date':'2026-06-30','Statement currency':'USD','Revenue (latest period)':5000000.,'Statement period':'FY'}],evidence=[],warnings=[])
    original=deepcopy(result)
    text=extract_text(io.BytesIO(build_research_pdf(result)))
    assert 'REVIEW STATUS' not in text and 'Financial basis & coverage' not in text
    assert 'Sources & Evidence' not in text and 'Retry' not in text
    assert '2026-06-30' in text and 'USD' in text and '5.0M' in text
    assert result==original


def test_explicit_canonical_forecasts_preserve_zero_dates_currency_and_source():
    from langgraphagenticai.deep_research.prompt_context import forward_consensus_context
    row={'Ticker':'AAPL','Estimate period':'2027-09-30','Forward EPS':9.6,'Forward revenue growth (%)':0.,'Metric contracts':{'Forward EPS':dict(unit='currency_per_share',currency='USD',basis='2027-09-30',inputs=[dict(source_id='E005')])}}
    original=deepcopy(row)
    context=forward_consensus_context([row])[0]['forecasts']
    assert context['Forward EPS']==dict(value=9.6,unit='currency_per_share',currency='USD',period='2027-09-30',source_ids=['E005'])
    assert context['Forward revenue growth (%)']['value']==0.
    assert row==original
