"""Dense provider-shaped packets must reach AI without losing mandatory evidence."""
import json
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from langgraphagenticai.portfolio_architect.schemas import InvestorMandate, Fact
from langgraphagenticai.portfolio_architect.research import demo_snapshot, candidates
from langgraphagenticai.portfolio_architect.universe import STOCKS
from langgraphagenticai.portfolio_architect.screening import METRICS
from langgraphagenticai.portfolio_architect.optimizer import select
from langgraphagenticai.portfolio_architect.analyst_packet import research_packet, encode_packet
from langgraphagenticai.portfolio_architect import committee


def dense_evidence(unique_basis=False):
    m=InvestorMandate(objective="Build a growth portfolio focused on AI",investment_style="growth",themes=["AI"],assets="stocks")
    snapshot=demo_snapshot(tuple(STOCKS),m.benchmark)
    for security in snapshot.securities:
        security.facts=[f for f in security.facts if f.field=="revenue_cagr_3y"]
        security.business_summary="Artificial intelligence and semiconductor business context. "*30
        for field,(_,_,unit,_) in METRICS.items():
            basis=(security.ticker+":"+field+" "+"Detailed retained fiscal assumptions. "*20) if unique_basis else "Provider TTM; fiscal end unavailable; not independently audited"
            security.facts.append(Fact(id=security.ticker+":"+field,field=field,value=.2,unit=unit,basis=basis,
                as_of=None,retrieved_at=security.retrieved_at,source="FMP stable/ratios-ttm"))
    securities,scores,_=candidates(snapshot,m)
    required={s.ticker for s in select(securities,scores,m)}
    return m,securities,scores,required


@pytest.mark.parametrize("unique_basis",[False,True])
def test_dense_packet_preserves_local_basket_growth_and_exact_provenance(unique_basis):
    m,securities,scores,required=dense_evidence(unique_basis)
    original={f.id:f for s in securities for f in s.facts}
    packet=research_packet(securities,scores,m,macro={"status":"partial","risks":["Long retained macro context "*2000]},required_tickers=required)
    assert len(encode_packet(packet).encode("utf-8"))<=42000
    assert required <= {r["ticker"] for r in packet["candidates"]}
    assert len(packet["candidates"])>=m.holdings
    if unique_basis:
        assert packet["omitted_candidates"]
        assert not required & set(packet["omitted_candidates"])
    for row in packet["candidates"]:
        assert any(f["field"]=="revenue_cagr_3y" for f in row["facts"])
        assert any(f["field"] in METRICS for f in row["facts"])
        for fact in row["facts"]:
            saved=original[fact["id"]].model_dump()
            assert packet["provenance"][fact["provenance_id"]]=={k:saved[k] for k in ("source","basis","as_of","retrieved_at")}
            assert fact["value"]==saved["value"] and fact["unit"]==saved["unit"]


def test_dense_packet_reaches_single_structured_model_request(monkeypatch):
    m,securities,scores,required=dense_evidence()
    def create(**kwargs):
        wire=kwargs["messages"][1]["content"]
        assert len(wire.encode("utf-8"))<=42000
        packet=json.loads(wire)
        assert "provenance" in packet
        picks=[]
        for row in packet["candidates"]:
            refs=[next(f["id"] for f in row["facts"] if f["field"]=="revenue_cagr_3y"),
                  next(f["id"] for f in row["facts"] if f["field"] in METRICS)]
            picks.append({"ticker":row["ticker"],"conviction":"medium","reason":"diversification","evidence_ids":refs,
                "analysis":{"framework":row["sector_lens"]["framework"],"thesis":"Positive saved annual growth supports this conditional research thesis.",
                            "conviction_summary":"Positive saved growth supports conviction; future execution is uncertain.","risks":["Sector margins may weaken."],
                            "thesis_breaker":"Reassess on sustained deterioration in reported growth.","portfolio_role":"growth","missing_inputs":["Forward estimates unavailable."]}})
        return NS(choices=[NS(finish_reason="stop",message=NS(content=json.dumps({"picks":picks,"concerns":["concentration","missing_data","valuation_uncertainty"],"rejected":[]}),refusal=None))],usage=None)
    request=Mock(side_effect=create)
    monkeypatch.setattr(committee,"build_openai_client",Mock(return_value=NS(chat=NS(completions=NS(create=request)))))
    output,_=committee.review(securities,scores,m,"fixture","fixture-model",macro={"risks":["Large context "*5000]},required_tickers=required)
    assert len(output.picks)>=m.holdings
    request.assert_called_once()
