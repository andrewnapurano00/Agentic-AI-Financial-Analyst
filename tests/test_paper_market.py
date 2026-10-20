"""FMP paper snapshot contracts; no live entitlements or paid services."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import pytest
from langgraphagenticai.providers import paper_market as provider


@pytest.fixture(autouse=True)
def clear():
    cached = provider.load_paper_market
    cached.clear()
    yield
    cached.clear()


def services(url, *, params, **kwargs):
    if url.endswith("batch-quote"):
        return [dict(symbol=s, price=100., timestamp=(datetime.now(timezone.utc)-timedelta(minutes=1)).timestamp(),
                     changePercentage=0., priceAvg50=95., priceAvg200=90.) for s in params["symbols"].split(",")]
    if url.endswith("profile"):
        return [dict(symbol=params["symbol"], currency="USD", companyName=params["symbol"],
                     sector="Technology", description="apikey=never-keep-this")]
    return [dict(symbol=params["symbol"], priceToEarningsRatioTTM=20., netProfitMarginTTM=.2)]


def test_shared_bounded_snapshot_cache_and_provenance(monkeypatch):
    get = Mock(side_effect=services)
    monkeypatch.setattr(provider,"get_fmp_json",get)
    packet = provider.load_paper_market(("AAPL","MSFT"),"SPY","synthetic")
    assert len(packet["rows"]) == 3 and get.call_count == 6
    assert packet == provider.load_paper_market(("AAPL","MSFT"),"SPY","synthetic")
    assert get.call_count == 6 and "never-keep-this" not in str(packet)
    row = packet["rows"]["AAPL"]
    assert row["pe_ttm"] == 20 and row["change_pct"] == 0
    assert "profile listing currency" in row["currency_basis"] and row["as_of"]


def test_partial_profile_currency_failure_does_not_erase_other_quotes(monkeypatch):
    def partial(url, **kwargs):
        if url.endswith("profile") and kwargs["params"]["symbol"] == "AAPL":
            raise RuntimeError("apikey=do-not-retain")
        return services(url, **kwargs)
    monkeypatch.setattr(provider,"get_fmp_json",partial)
    packet=provider.load_paper_market(("AAPL","MSFT"),"SPY","synthetic")
    assert "AAPL" not in packet["rows"] and "MSFT" in packet["rows"]
    assert "do-not-retain" not in str(packet)


@pytest.mark.parametrize("edit", [
    lambda r:r.update(price=0),
    lambda r:r.update(timestamp=(datetime.now(timezone.utc)+timedelta(days=1)).timestamp()),
    lambda r:r.update(currency="EUR"),
    lambda r:r.update(symbol="OTHER"),
])
def test_bad_quotes_are_not_eligible_fills(monkeypatch, edit):
    def invalid(url, **kwargs):
        data=services(url,**kwargs)
        if url.endswith("batch-quote"):edit(data[0])
        return data
    monkeypatch.setattr(provider,"get_fmp_json",invalid)
    assert "AAPL" not in provider.load_paper_market(("AAPL",),"SPY","synthetic")["rows"]


def test_invalid_symbols_fail_before_transport(monkeypatch):
    get=Mock();monkeypatch.setattr(provider,"get_fmp_json",get)
    with pytest.raises(ValueError):provider.load_paper_market(("../bad",),"SPY","synthetic")
    get.assert_not_called()
