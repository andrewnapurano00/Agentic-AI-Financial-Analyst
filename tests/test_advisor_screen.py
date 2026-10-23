"""Independent sector ranks, membership, freshness and fallback contracts; no network."""
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
import pytest
from langgraphagenticai.portfolio_architect.screening import rank_rows, metric_facts, shortlist, macro_assessment, applicable
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate
from langgraphagenticai.providers import advisor_screen as provider


@pytest.fixture(autouse=True)
def no_real_batch_wait(monkeypatch):
    from langgraphagenticai.providers import advisor_batches
    monkeypatch.setattr(advisor_batches, "PAUSE_SECONDS", 0)


def row(symbol, value, sector="Industrials"):
    return {"symbol": symbol, "sector": sector, "values": {
        "margin_ttm": value, "operating_margin_ttm": value, "roa_ttm": value,
        "roe_ttm": value, "roic_ttm": value, "fcf_yield_ttm": value,
        "pe_ttm": 30/value, "pb_ttm": 5/value, "debt_assets_ttm": 1/value,
        "debt_equity_ttm": 2/value, "gross_margin_ttm":value, "ebitda_margin_ttm":value,
        "ps_ttm":10/value, "pfcf_ttm":20/value, "debt_capital_ttm":1/value,
        "debt_service_ttm":value, "dividend_yield_ttm":value}}


def test_sector_percentiles_are_independently_reproducible():
    ranked = rank_rows([row("AAA", 1), row("BBB", 2), row("CCC", 3)])
    assert [r["symbol"] for r in ranked] == ["CCC", "BBB", "AAA"]
    assert [r["score"] for r in ranked] == pytest.approx([100, 50, 0])
    assert ranked[0]["coverage"] == 1 and not ranked[0]["exclusion"]
    assert ranked[0]["components"]["pe_ttm"]["percentile"] == 1


def test_ties_missing_nonpositive_and_specialists_do_not_get_favorable_ranks():
    rows = [row("AAA", 1), row("BBB", 1), row("CCC", 1)]
    assert [r["score"] for r in rank_rows(rows)] == pytest.approx([50]*3)
    bad = row("BAD", 2); bad["values"] = {"margin_ttm": 0, "pe_ttm": -1}
    bad = next(r for r in rank_rows(rows+[bad]) if r["symbol"] == "BAD")
    assert bad["exclusion"] and "pe_ttm" not in bad["components"]
    assert rank_rows([row("REIT", 1, "Real Estate")])[0]["exclusion"]
    assert "debt_equity_ttm" not in applicable("Financial Services")[1]


def test_minimum_peer_count_and_forbidden_shortlist():
    assert all(r["exclusion"] for r in rank_rows([row("AAA", 1),row("BBB", 2)]))
    ranked = rank_rows([row("AAA", 1), row("BBB", 2), row("CCC", 3)])
    mandate = InvestorMandate(objective="Diversified portfolio", forbidden=["CCC"])
    assert shortlist(ranked, mandate) == ("BBB", "AAA")


def test_zero_and_invalid_provider_facts():
    fs = metric_facts("AAA", {"netProfitMarginTTM": 0, "debtToEquityRatioTTM": "nan"},
                      {"returnOnAssetsTTM": .1}, "2026-10-20T00:00:00+00:00", "-bulk")
    assert {f.field:f.value for f in fs} == {"margin_ttm": 0, "roa_ttm": .1}
    assert all(f.as_of is None and "fiscal end unavailable" in f.basis for f in fs)


def test_macro_rejects_stale_future_missing_and_preserves_zero():
    now = datetime(2026,10,20,12,tzinfo=timezone.utc)
    def obs(name, stamp, level=0, trend=0):
        return {"Instrument":name,"Group":"Macro","Level":level,"vs SMA 200 %":trend,
                "evidence":{"as_of":stamp.isoformat(),"stale":False,"indicator_date":stamp.date().isoformat()}}
    packet={"retrieved_at":now.isoformat(),"rows":[obs("S&P 500",now),obs("VIX",now,30),
            obs("Oil",now-timedelta(days=9),99),obs("US Dollar",now+timedelta(days=1),99)]}
    result=macro_assessment(packet,now)
    assert len(result["observations"]) == 2 and result["status"] == "partial"
    assert "VIX 30.0" in result["risks"][0] and "+0.0%" in result["upside"][0]


def test_duplicate_members_and_bad_symbols_rejected():
    assert provider.unique_rows([{"symbol":"AAA"},{"symbol":"AAA"},{"symbol":"http://bad"},{"symbol":"BBB"}]) == {"BBB":{"symbol":"BBB"}}


def test_membership_failure_never_substitutes_curated_names(monkeypatch):
    provider.load_screen.clear()
    request=Mock(return_value=[{"symbol":"AAA","sector":"Technology"}])
    monkeypatch.setattr(provider,"get_fmp_json",request)
    with pytest.raises(ValueError,match="membership incomplete"):
        provider.load_screen("fixture-key")
    request.assert_called_once()


@pytest.mark.parametrize("status", [402,403,404])
def test_membership_legacy_fallback_preserves_actual_source(monkeypatch,status):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    members=[{"symbol":"A"+chr(65+i//26)+chr(65+i%26),"sector":"Industrials"} for i in range(503)]
    request=Mock(side_effect=[ProviderRequestError("FMP","fixture-key unsafe URL",status_code=status),members])
    monkeypatch.setattr(provider,"get_fmp_json",request)
    rows,source,warnings=provider.load_membership("fixture-key")
    assert len(rows)==503 and source=="FMP api/v3/sp500_constituent"
    assert len(warnings)==1 and "fixture-key" not in str(warnings)
    assert request.call_count==2 and request.call_args.args[0]==provider.LEGACY_MEMBERSHIP


@pytest.mark.parametrize("status", [401,429,500,None])
def test_membership_does_not_fallback_for_auth_rate_limit_transport(monkeypatch,status):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    request=Mock(side_effect=ProviderRequestError("FMP","fixture-secret",status_code=status))
    monkeypatch.setattr(provider,"get_fmp_json",request)
    with pytest.raises(ValueError) as error:
        provider.load_membership("fixture-secret")
    assert "fixture-secret" not in str(error.value)
    request.assert_called_once()


def test_membership_fallback_must_still_be_complete_and_errors_safe(monkeypatch):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    request=Mock(side_effect=[ProviderRequestError("FMP","fixture",status_code=402),[{"symbol":"AAA"}]])
    monkeypatch.setattr(provider,"get_fmp_json",request)
    with pytest.raises(ValueError,match="membership incomplete"):
        provider.load_membership("fixture-secret")
    request.side_effect=[ProviderRequestError("FMP","fixture",status_code=402),ProviderRequestError("FMP","fixture-secret",status_code=403)]
    with pytest.raises(ValueError,match="Legacy endpoint: HTTP 403") as error:
        provider.load_membership("fixture-secret")
    assert "fixture-secret" not in str(error.value)


@pytest.mark.parametrize("status,expected", [(401,3),(429,2),(403,803)])
def test_fallback_only_on_plan_restriction_and_cache_reuses(monkeypatch,status,expected):
    from langgraphagenticai.providers.fmp_http import ProviderRequestError
    members=[{"symbol":"A"+chr(65+i//26)+chr(65+i%26),"sector":"Industrials"} for i in range(400)]
    calls=[]
    def request(url,**kwargs):
        calls.append(url)
        if url.endswith("sp500-constituent"):
            return members
        if url.endswith("-bulk"):
            raise ProviderRequestError("FMP","fixture failure",status_code=status)
        return [{"symbol":kwargs["params"]["symbol"],"netProfitMarginTTM":.1,"returnOnAssetsTTM":.1}]
    monkeypatch.setattr(provider,"get_fmp_json",request)
    provider.load_screen.clear()
    result=provider.load_screen("fixture-key")
    assert result["membership_count"] == 400 and len(calls)==expected
    assert provider.load_screen("fixture-key") == result and len(calls)==expected
    provider.load_screen.clear()


def test_full_screen_filters_nonmembers_and_keeps_evidence(monkeypatch):
    members=[{"symbol":"A"+chr(65+i//26)+chr(65+i%26),"sector":"Industrials"} for i in range(400)]
    def request(url,**kwargs):
        if url.endswith("sp500-constituent"): return members
        return [{"symbol":r["symbol"],"netProfitMarginTTM":.1,"returnOnAssetsTTM":.1,
                 "returnOnEquityTTM":.2,"returnOnInvestedCapitalTTM":.15,"priceToEarningsRatioTTM":20,
                 "freeCashFlowYieldTTM":.05,"debtToAssetsRatioTTM":.3,"operatingProfitMarginTTM":.12,
                 "ebitdaMarginTTM":.14,"debtToCapitalRatioTTM":.3} for r in members+[{'symbol':'OUTSIDE'}]]
    monkeypatch.setattr(provider,"get_fmp_json",request); provider.load_screen.clear()
    result=provider.load_screen("fixture-key")
    assert len(result["ranked"])==400 and not result["ranked"][0]["exclusion"]
    assert result["ranked"][0]["facts"][0]["source"] == "FMP stable/ratios-ttm-bulk"
    provider.load_screen.clear()


def test_annual_cagr_requires_four_matched_years_and_currency():
    from langgraphagenticai.providers.advisor_research import annual_growth
    rows=[{"symbol":"AAA","date":f"{year}-12-31","fiscalYear":year,"period":"FY",
           "reportedCurrency":"USD","revenue":100*1.1**i} for i,year in enumerate(range(2022,2026))]
    now=datetime(2026,10,20,tzinfo=timezone.utc)
    facts=annual_growth("AAA",rows,now.isoformat(),now.date())
    assert len(facts)==5 and facts[-1]["value"] == pytest.approx(.1)
    assert facts[-1]["as_of"] == "2025-12-31" and "not TTM" in facts[0]["basis"]
    for field,value in (("reportedCurrency","EUR"),("fiscalYear",2022),("period","Q4"),("revenue",0)):
        bad=[dict(r) for r in rows];bad[-1][field]=value
        assert annual_growth("AAA",bad,now.isoformat(),now.date()) == []


def test_fresh_quote_cannot_revive_old_macro_indicators():
    now=datetime(2026,10,20,12,tzinfo=timezone.utc)
    result=macro_assessment({"rows":[{"Instrument":"S&P 500","Group":"Macro","Level":100,
        "vs SMA 200 %":10,"30D %":20,"evidence":{"as_of":now.isoformat(),"stale":False,
        "indicator_date":"2026-01-01"}}]},now)
    assert not result["upside"] and result["observations"][0]["vs_sma200_pct"] is None


def test_position_tradeoffs_reference_measured_weaknesses():
    from langgraphagenticai.portfolio_architect.screening import position_tradeoffs
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    s=demo_snapshot(("MSFT",),"SPY").securities[0]
    s.facts=metric_facts("MSFT",{"priceToEarningsRatioTTM":40,"debtToAssetsRatioTTM":.6},
                         {"freeCashFlowYieldTTM":-.01},s.retrieved_at)
    risks,catalysts=position_tradeoffs(s,{"risks":["Macro stress"],"upside":["Trend improving"]})
    assert any("MSFT:pe_ttm" in r for r in risks) and any("MSFT:fcf_yield_ttm" in r for r in risks)
    assert any("Macro stress" in r for r in risks) and any("Conditional" in c for c in catalysts)


def test_news_safe_dated_deduplicated_sources_without_credentials():
    from langgraphagenticai.providers.advisor_research import news_rows
    rows=[{"symbol":"AAA","title":"Fixture headline","url":"https://example.com/article?apikey=secret",
           "publishedDate":"2026-10-19 10:00:00","publisher":"Fixture"}]
    result=news_rows("AAA",rows*2,"2026-10-20T12:00:00+00:00","secret",datetime(2026,10,20).date())
    assert len(result)==1 and result[0]["url"] == "https://example.com/article"
    for field,value in (("url","javascript:alert(1)"),("publishedDate","2026-10-21"),("symbol","BBB")):
        bad=[{**rows[0],field:value}]
        assert news_rows("AAA",bad,"fixture","secret",datetime(2026,10,20).date()) == []


def test_advisor_pipeline_preserves_screen_macro_and_research_without_curated_limit(monkeypatch):
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.schemas import Fact
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    m=InvestorMandate(objective="Diversified portfolio",assets="stocks",holdings=5)
    snapshot=demo_snapshot(eligible_names(m),"SPY")
    ranked=rank_rows([row("AAA",1),row("BBB",2),row("CCC",3)])
    # Five passers across this fixture's independent sector samples.
    ranked=rank_rows([row(s,i+1) for i,s in enumerate(("MSFT","NVDA","AAPL","AVGO","GOOGL"))])
    for r in ranked:
        r["facts"]=[f.model_dump() for f in metric_facts(r["symbol"],{"netProfitMarginTTM":.1},{},snapshot.retrieved_at)]
    monkeypatch.setattr(provider,"load_screen",Mock(return_value={"ranked":ranked,"retrieved_at":snapshot.retrieved_at,"membership_count":503,"warnings":[]}))
    # Keep profile classifications compatible with synthetic membership.
    for s in snapshot.securities: s.sector="Industrials"
    monkeypatch.setattr(provider,"collect",Mock(return_value=snapshot))
    monkeypatch.setattr(provider,"load_dashboard",Mock(side_effect=RuntimeError("provider unavailable")))
    monkeypatch.setattr(provider,"load_issuer_research",Mock(return_value={}))
    result=provider.collect_advisor(m,"fixture")
    assert result.screening["membership_count"]==503 and len(result.screening["shortlisted"])==5
    assert result.macro["status"]=="unavailable" and result.id != ""
    assert any(f.field=="screen_score" for s in result.securities for f in s.facts)


def test_rate_limit_in_collection_skips_issuer_and_macro_calls(monkeypatch):
    from langgraphagenticai.portfolio_architect.research import demo_snapshot
    from langgraphagenticai.portfolio_architect.universe import eligible_names
    mandate=InvestorMandate(objective="Diversified fund portfolio",assets="etfs")
    snapshot=demo_snapshot(eligible_names(mandate),"SPY")
    def collect(*args,**kwargs):
        kwargs["_budget"].stopped.set()
        return snapshot
    monkeypatch.setattr(provider,"collect",collect)
    research=Mock(side_effect=AssertionError("No issuer call after 429"))
    macro=Mock(side_effect=AssertionError("No macro call after 429"))
    monkeypatch.setattr(provider,"load_issuer_research",research)
    monkeypatch.setattr(provider,"load_dashboard",macro)
    result=provider.collect_advisor(mandate,"fixture")
    assert result.securities and result.macro["status"]=="unavailable"
    assert any("429" in w for w in result.warnings)
    research.assert_not_called();macro.assert_not_called()
