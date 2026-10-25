"""Registered endpoint probes, redaction and explicit workspace state; offline."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from streamlit.testing.v1 import AppTest
from langgraphagenticai.providers import data_validation as service
from langgraphagenticai.providers.data_validation_catalog import endpoints,endpoint
from langgraphagenticai.providers.fmp_http import ProviderRequestError

KEYS={"FMP_API_KEY":"fixture-fmp-private","MARKETAUX_API_KEY":"fixture-news-private","SERPER_API_KEY":"fixture-search-private"}


def test_catalog_unique_and_every_retained_mcp_wrapper_is_registered():
    catalog=endpoints()
    assert len({e["id"] for e in catalog})==len(catalog)
    tree=ast.parse(Path("src/langgraphagenticai/tools/fmp_mcp_client.py").read_text(encoding="utf-8"))
    methods={node.name for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and not node.name.startswith("_") and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=="_call_mcp" and len(c.args)>=2 and all(isinstance(x,ast.Constant) and isinstance(x.value,str) for x in c.args[:2]) for c in ast.walk(node))}
    assert methods=={e["method"] for e in catalog if e["provider"]=="FMP MCP"}
    assert len([e for e in catalog if e["provider"]=="FMP REST"])==44
    with pytest.raises(ValueError):endpoint("https://attacker.example")
    catalog[0]["route"]="evil"
    assert endpoint(catalog[0]["id"])["route"]!="evil"


@pytest.mark.parametrize("ticker",["https://evil","AAPL/MSFT","AAPL,MSFT","../x","AAPL?apikey=secret","AAPL\nX"])
def test_invalid_ticker_never_dispatches(monkeypatch,ticker):
    dispatch=Mock();monkeypatch.setattr(service,"_dispatch",dispatch)
    with pytest.raises(ValueError):service.fetch_endpoint("fmp.stable.quote",ticker,credentials=KEYS)
    dispatch.assert_not_called()


@pytest.mark.parametrize("params",[{"apikey":"oops"},{"url":"https://evil"},{"symbol":"MSFT"},{"limit":100000},{"limit":True},{"period":"ttm"},{"from":"2026-10-20","to":"2020-01-01"}])
def test_unapproved_or_invalid_parameters_rejected(params):
    with pytest.raises(ValueError):service.prepare("fmp.stable.income-statement","AAPL",params)


def test_stable_legacy_and_marketwide_routes_are_exact(monkeypatch):
    request=Mock(return_value=[{"symbol":"AAPL","price":0,"eps":None}]);monkeypatch.setattr(service,"get_fmp_json",request)
    result=service.fetch_endpoint("fmp.stable.quote"," aapl ",credentials=KEYS)
    assert request.call_args.args==("https://financialmodelingprep.com/stable/quote",)
    assert request.call_args.kwargs["params"]=={"symbol":"AAPL"}
    assert result["data"][0]["price"]==0 and result["data"][0]["eps"] is None
    service.fetch_endpoint("fmp.v3.quote","AAPL",credentials=KEYS)
    assert request.call_args.args[0].endswith("/api/v3/quote/AAPL")
    result=service.fetch_endpoint("fmp.stable.sp500-constituent","INVALID!",credentials=KEYS)
    assert request.call_args.kwargs["params"]=={} and result["ticker"] is None


@pytest.mark.parametrize("status",[401,402,403,429,500,None])
def test_errors_never_return_provider_exception_urls_or_secrets(monkeypatch,status):
    request=Mock(side_effect=ProviderRequestError("FMP","https://secret.example?apikey=fixture-fmp-private",status_code=status))
    monkeypatch.setattr(service,"get_fmp_json",request)
    result=service.fetch_endpoint("fmp.stable.quote","AAPL",credentials=KEYS)
    assert result["status"]=="error" and result["http_status"]==status
    assert "fixture-fmp-private" not in json.dumps(result) and "secret.example" not in json.dumps(result)
    request.assert_called_once()


def test_redaction_is_recursive_bounded_and_exports_are_safe(monkeypatch):
    raw={"token":"unknown-token","api_key":"unknown-key","records":[{"symbol":"WRONG","price":0,"missing":None,"url":"https://example.com/?apikey=unknown-private","text":"fixture-fmp-private"}]*1500}
    cleaned,truncated=service.sanitize_payload(raw,tuple(KEYS.values()))
    assert truncated and len(cleaned["records"])==1000
    assert cleaned["token"]==cleaned["api_key"]=="[REDACTED]"
    assert all(secret not in json.dumps(cleaned) for secret in ("unknown-token","unknown-key","unknown-private",KEYS["FMP_API_KEY"]))
    monkeypatch.setattr(service,"_dispatch",lambda *a:[{"symbol":"MSFT","price":0}])
    result=service.fetch_endpoint("fmp.stable.quote","AAPL",credentials=KEYS)
    assert result["identity_warning"] and result["data"][0]["symbol"]=="MSFT"


def test_missing_credentials_and_bad_json_types_make_no_call(monkeypatch):
    dispatch=Mock();monkeypatch.setattr(service,"_dispatch",dispatch)
    with pytest.raises(ValueError):service.fetch_endpoint("fmp.stable.quote","AAPL",credentials={})
    with pytest.raises(ValueError):service.fetch_endpoint("fmp.stable.quote","AAPL",parameters=[] ,credentials=KEYS)
    dispatch.assert_not_called()


def test_mcp_dispatch_is_one_registered_method_without_models(monkeypatch):
    from langgraphagenticai.tools import fmp_mcp_client
    method=Mock(return_value={"ok":True,"data":[{"symbol":"AAPL","revenue":0}]})
    constructor=Mock(return_value=SimpleNamespace(income_statement=method))
    monkeypatch.setattr(fmp_mcp_client,"FMPMCPClient",constructor)
    result=service.fetch_endpoint("mcp.income_statement","AAPL",{"limit":4,"period":"quarter"},credentials=KEYS)
    constructor.assert_called_once_with(KEYS["FMP_API_KEY"],retries=0,timeout_seconds=30)
    method.assert_called_once_with(symbol="AAPL",limit=4,period="quarter")
    assert result["status"]=="available"
    assert service.response_rows({"ok":True,"data":{}})==[]
    assert service.response_rows({"ok":True,"data":{"symbol":"AAPL","price":0}})==[{"symbol":"AAPL","price":0}]


def test_marketaux_and_serper_use_existing_credentials_and_timeouts(monkeypatch):
    request=Mock(return_value=SimpleNamespace(status_code=200,json=lambda:{"data":[{"title":"News"}]}))
    monkeypatch.setattr(service.requests,"get",request)
    assert service.fetch_endpoint("marketaux.news","AAPL",credentials=KEYS)["status"]=="available"
    assert request.call_args.kwargs["params"]["api_token"]==KEYS["MARKETAUX_API_KEY"]
    assert request.call_args.kwargs["timeout"]==(5,25)
    assert request.call_args.kwargs["allow_redirects"] is False
    from langgraphagenticai.tools import serper_tools
    search=Mock(return_value={"ok":True,"results":[{"title":"Search"}]})
    monkeypatch.setattr(serper_tools.SerperClient,"search",search)
    service.fetch_endpoint("serper.news","AAPL",{"days":7,"limit":5},credentials=KEYS)
    assert search.call_args.args[0]=="AAPL company financial news"
    assert search.call_args.kwargs["filter_dates"] is True


def test_yahoo_history_is_explicitly_adjusted_and_bounded(monkeypatch):
    import pandas as pd
    import yfinance as yf
    frame=pd.DataFrame({"Close":[1.,2.]},index=pd.date_range("2026-10-01",periods=2))
    download=Mock(return_value=frame)
    monkeypatch.setattr(yf,"download",download)
    result=service.fetch_endpoint("yahoo.history","SPY",{"days":30})
    assert result["status"]=="available" and result["record_count"]==2
    assert download.call_args.kwargs["auto_adjust"] is True and download.call_args.kwargs["timeout"]==15


def test_workspace_fetch_only_and_failure_preserves_result(monkeypatch):
    from langgraphagenticai.ui import data_validation_tab as ui
    def fetch(identifier,ticker,params,query,credentials):
        return {"endpoint_id":identifier,"label":endpoint(identifier)["label"],"provider":"FMP REST","route":endpoint(identifier)["route"],"ticker":ticker,"parameters":{"symbol":ticker},"status":"available","retrieved_at":"2026-10-24T12:00:00Z","elapsed_seconds":0.1,"data":[{"symbol":ticker,"zero":0,"missing":None}],"record_count":1,"basis":"Raw provider response","truncated":False}
    request=Mock(side_effect=fetch);monkeypatch.setattr(ui,"fetch_endpoint",request)
    app=AppTest.from_string('from langgraphagenticai.ui.data_validation_tab import render_data_validation\nrender_data_validation("fixture-fmp-private")',default_timeout=30).run()
    assert not app.exception and not request.called
    next(b for b in app.button if b.label=="Fetch data").click().run()
    assert not app.exception and request.call_count==1
    saved=app.session_state["validation_saved_response"]
    app.run();assert request.call_count==1
    app.text_input(key="validation_field_filter").set_value("zero").run()
    assert request.call_count==1
    app.selectbox(key="validation_endpoint").set_value("fmp.stable.quote").run()
    assert app.warning and request.call_count==1
    request.side_effect=lambda *a:{**saved["response"],"status":"error","message":"HTTP 402: endpoint access denied."}
    next(b for b in app.button if b.label=="Fetch data").click().run()
    assert not app.exception and app.error
    assert app.session_state["validation_saved_response"]==saved
    assert request.call_count==2


def test_main_route_does_not_touch_market_ribbon_or_models(monkeypatch):
    from langgraphagenticai import main
    from langgraphagenticai.ui import data_validation_tab
    renderer=Mock();monkeypatch.setattr(data_validation_tab,"render_data_validation",renderer)
    monkeypatch.setattr(main.LoadStreamlitUI,"load_streamlit_ui",lambda self:{"active_page":"Data Validation","FMP_API_KEY":"fixture","MARKETAUX_API_KEY":"news","SERPER_API_KEY":"search"})
    monkeypatch.setattr(main,"render_market_strip",lambda **k:pytest.fail("No incidental quote calls"))
    monkeypatch.setattr(main,"render_command_bar",lambda:pytest.fail("No model workflow"))
    monkeypatch.setattr(main,"_render_status_panel",lambda *a:None)
    app=AppTest.from_string('from langgraphagenticai.main import load_langgraph_agenticai_app\nload_langgraph_agenticai_app()',default_timeout=30).run()
    assert not app.exception
    renderer.assert_called_once_with(fmp_api_key="fixture",marketaux_api_key="news",serper_api_key="search")


def test_large_result_keeps_required_metadata_and_bounded_download(monkeypatch):
    monkeypatch.setattr(service,"_dispatch",lambda *a:[{f"field{i}":"value" for i in range(100)} for _ in range(1000)])
    result=service.fetch_endpoint("fmp.stable.quote","AAPL",credentials=KEYS)
    assert result["truncated"] and result["basis"] and result["endpoint_id"]
    assert len(json.dumps(result,ensure_ascii=False).encode())<service.MAX_BYTES


def test_credential_change_suppresses_saved_response_without_fetch(monkeypatch):
    from langgraphagenticai.ui import data_validation_tab as ui
    request=Mock();monkeypatch.setattr(ui,"fetch_endpoint",request)
    app=AppTest.from_string('from langgraphagenticai.ui.data_validation_tab import render_data_validation\nrender_data_validation("new-private-key")',default_timeout=30)
    app.session_state["validation_saved_response"]={"scope":"old-credential-scope","response":{"data":[{"private":"old response"}]}}
    app.run()
    assert not app.exception and not request.called
    assert any("different provider settings" in i.value for i in app.info)
    assert not any(b.label == "Download response JSON" for b in app.get("download_button"))


@pytest.mark.parametrize("params",[{"limit":11},{"days":91}])
def test_search_params_do_not_silently_clamp_request_metadata(params):
    with pytest.raises(ValueError):service.prepare("serper.news","AAPL",params)


def test_literal_rest_routes_used_in_source_have_catalog_coverage():
    from urllib.parse import urlsplit
    registered=[e["route"].split("{symbol}")[0].rstrip("/") for e in endpoints() if e["provider"]=="FMP REST"]
    for source in Path("src/langgraphagenticai").rglob("*.py"):
        if source.name.startswith("data_validation"):continue
        tree=ast.parse(source.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node,ast.Constant) or not isinstance(node.value,str) or not node.value.startswith("https://financialmodelingprep.com/"):continue
            path=urlsplit(node.value).path.rstrip("/")
            if path in ("","/mcp","/stable"):continue
            assert any(path.startswith(route) or route.startswith(path) for route in registered),(str(source),path)
