"""Calendar horizons, combined news coverage and executive rendering; offline."""
import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.analysis.market_dashboard import dashboard_metrics
from langgraphagenticai.analysis import market_brief_ai, market_news_ai
from langgraphagenticai.providers import market_brief_news


def records():
    rows=[{"date":str(d.date()),"close":110,"adj_close":110} for d in pd.bdate_range("2026-06-01","2026-10-23")]
    for row in rows:
        if row["date"] == "2026-09-23": row["adj_close"]=100
        if row["date"] == "2026-07-23": row["adj_close"]=80
    rows[-1]["close"]=120
    return rows


def test_calendar_months_are_not_thirty_or_sixty_sessions():
    data=dashboard_metrics(records(),"2026-10-24T12:00:00Z")
    assert data["1M"] == pytest.approx(20)
    assert data["3M"] == pytest.approx(50)
    assert data["30D"] == pytest.approx((120/110-1)*100)
    assert data["inputs"]["1M"]["date"] == "2026-09-23"
    assert data["inputs"]["3M"]["date"] == "2026-07-23"


def test_month_weekend_anchor_zero_and_missing_do_not_fill():
    rows=records()
    # Month anniversary is a Sunday; use Friday and preserve a true zero.
    data=dashboard_metrics(rows,"2026-10-28T20:00:00Z",{"price":110,"as_of":"2026-10-27T15:00:00Z"})
    assert data["1M"] == 0
    assert data["inputs"]["1M"]["target_date"] == "2026-09-27"
    duplicate=records()+[{"date":"2026-09-23","adj_close":100}]
    assert dashboard_metrics(duplicate,"2026-10-24T12:00:00Z")["1M"] is None
    sparse=[r for r in records() if not "2026-09-10" <= r["date"] <= "2026-09-23"]
    assert dashboard_metrics(sparse,"2026-10-24T12:00:00Z")["1M"] is None


def test_executive_market_prompt_includes_month_bases_and_no_news(monkeypatch):
    create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content="Market stance."))]))
    monkeypatch.setattr(market_brief_ai,"build_openai_client",lambda *a,**k:SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    metrics=dashboard_metrics(records(),"2026-10-24T12:00:00Z")
    packet={"rows":[{"Ticker":"SPY","Instrument":"S&P proxy","1M %":metrics["1M"],"3M %":metrics["3M"],"evidence":metrics}]}
    market_brief_ai.interpret_market(packet,{"articles":[{"title":"Excluded from metrics brief"}]},"fixture","gpt-5")
    messages=create.call_args.kwargs["messages"]
    evidence=json.loads(messages[1]["content"].split("\n",1)[1])
    assert "news" not in evidence
    assert evidence["calendar_month_inputs"]["SPY"]["1M"]["date"] == "2026-09-23"
    assert all(term in messages[0]["content"] for term in ("350-500", "Past 5 trading days", "Past month", "Past 3 months", "What to watch"))
    assert create.call_count == 1


def test_every_configured_news_source_and_query_reaches_packet(monkeypatch):
    searches=[]
    def search(self,query,**kwargs):
        searches.append(query)
        return {"ok":True,"results":[{"title":query,"url":"https://example.com/search/"+str(len(searches)),"snippet":"Search detail"}]}
    monkeypatch.setattr(market_brief_news.SerperClient,"search",search)
    monkeypatch.setattr(market_brief_news.requests,"get",lambda *a,**k:SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:{"data":[{"title":"Marketaux credit", "url":"https://example.com/credit","description":"Credit spreads"}]}))
    routes=[]
    def fmp(url,**kwargs):
        routes.append(url)
        if url.endswith("fmp-articles"):
            return [{"title":"FMP analysis","link":"https://example.com/analysis","content":"<p>Rates and earnings analysis</p>"}]
        return [{"title":"FMP energy","url":"https://example.com/energy","text":"Oil and energy"}]
    monkeypatch.setattr(market_brief_news,"get_fmp_json",fmp)
    news=market_brief_news.load_market_news.__wrapped__("search-fixture","marketaux-fixture","fmp-fixture")
    evidence=market_news_ai.news_evidence(news)
    assert len(searches)==3 and len(routes)==2
    assert len(evidence["articles"])==6
    assert {p for article in evidence["articles"] for p in article["providers"]} == {"Serper","Marketaux","FMP"}
    assert news["coverage"]["FMP"]["retained_stories"]==2
    assert any("Rates and earnings analysis" in a["article_text"] for a in evidence["articles"])


def test_news_packet_keeps_all_bounded_stories_with_long_previews_and_bodies():
    articles=[{"title":"T"*500,"url":f"https://example.com/{i}","snippet":"S"*2000,"publisher":"P"*200,"published":"2026-10-24","providers":["FMP"],"article_text":"B"*10000 if i<5 else ""} for i in range(48)]
    packet=market_news_ai.news_evidence({"articles":articles})
    assert len(packet["articles"])==48
    assert packet["omitted_story_count"]==0
    assert sum(bool(a["article_text"]) for a in packet["articles"])==5
    assert len(json.dumps({k:v for k,v in packet.items() if k!="fingerprint"},sort_keys=True,ensure_ascii=False)) <= 100000


def test_news_paragraphs_are_primary_and_theme_audit_is_collapsed(monkeypatch):
    from test_market_updates import sample_news,summary_response
    from langgraphagenticai.ui import market_news_summary as ui
    news=sample_news();evidence=market_news_ai.news_evidence(news);result=summary_response(evidence)
    result["overview"]="Rates and earnings are shaping market leadership.\n\nCredit and energy remain the key crosscurrents to watch."
    result["claims"][0]["interpretation"]="Audit theme detail"
    generate=Mock(return_value={"result":result,"evidence":evidence,"model":"gpt-5"})
    monkeypatch.setattr(ui,"summarize_news",generate)
    monkeypatch.setitem(sys.modules,"executive_news_fixture",SimpleNamespace(news=news))
    app=AppTest.from_string('from executive_news_fixture import news\nfrom langgraphagenticai.ui.market_news_summary import render_news_summary\nrender_news_summary(news,"fixture")',default_timeout=30).run()
    app.button(key="market_news_summarize").click().run()
    assert not app.exception
    assert any("Rates and earnings" in m.value and "Credit and energy" in m.value for m in app.markdown)
    audit=next(e for e in app.expander if e.label=="Briefing evidence & coverage")
    assert audit.proto.expanded is False
    assert any("Audit theme detail" in t.value for t in audit.text)
    app.run();assert generate.call_count==1
