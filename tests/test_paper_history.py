"""Recorded/synthetic historical adapter contracts, no live access."""
from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
from langgraphagenticai.providers import paper_history as provider


@pytest.fixture(autouse=True)
def cache():
    provider.load_paper_history.clear()
    yield
    provider.load_paper_history.clear()


def response(url,*,params,**kwargs):
    if url.endswith("profile"):
        return [{"symbol":params["symbol"],"currency":"USD","description":"CURRENT SECRET NEWS NEVER USED"}]
    return [{"symbol":params["symbol"],"date":"2025-01-02","close":100},
            {"date":"2025-01-03","close":110}, {"date":"2025-01-06","close":120},
            {"date":"2025-01-07","close":999}, {"date":"2099-01-01","close":999},
            {"date":"2025-01-02","close":100}, # Any duplicate day excluded, not arbitrarily selected.
            {"date":"2025-01-04","close":True},{"date":"2025-01-05","close":float("nan")}]


def test_bounded_provider_dates_currency_allowlist_and_shared_cache(monkeypatch):
    mock=Mock(side_effect=response)
    monkeypatch.setattr(provider,"get_fmp_json",mock)
    packet=provider.load_paper_history(("SPY","IBIT"),"SPY","2025-01-02","2025-01-06","key")
    assert packet["series"]=={"SPY":{"2025-01-03":110.,"2025-01-06":120.},"IBIT":{"2025-01-03":110.,"2025-01-06":120.}}
    assert "CURRENT SECRET NEWS" not in str(packet) and "key" not in packet
    assert mock.call_count==4
    provider.load_paper_history(("SPY","IBIT"),"SPY","2025-01-02","2025-01-06","key")
    assert mock.call_count==4
    assert all(c.kwargs["timeout"] for c in mock.call_args_list)
    assert all(c.kwargs["params"].get("to","2025-01-06")=="2025-01-06" for c in mock.call_args_list)


def test_partial_failure_and_conflicting_currency_do_not_invent_rows(monkeypatch):
    def fake(url,*,params,**kwargs):
        if params["symbol"]=="IBIT":raise RuntimeError("apikey=private")
        if url.endswith("profile"):return [{"symbol":"SPY","currency":"EUR"}]
        return response(url,params=params)
    monkeypatch.setattr(provider,"get_fmp_json",fake)
    packet=provider.load_paper_history(("SPY","IBIT"),"SPY","2025-01-02","2025-01-06","key")
    assert packet["series"]=={"SPY":{},"IBIT":{}} and "private" not in str(packet)


def test_invalid_symbol_rejected_before_network(monkeypatch):
    mock=Mock(side_effect=AssertionError())
    monkeypatch.setattr(provider,"get_fmp_json",mock)
    with pytest.raises(ValueError):provider.load_paper_history(("../bad",),"SPY","2025-01-02","2025-01-06","key")
    mock.assert_not_called()


def test_single_symbol_and_benchmark_share_requests(monkeypatch):
    mock=Mock(side_effect=response)
    monkeypatch.setattr(provider,"get_fmp_json",mock)
    packet=provider.load_paper_history(("SPY",),"SPY","2025-01-02","2025-01-06","key")
    assert packet["series"]["SPY"] and mock.call_count==2
