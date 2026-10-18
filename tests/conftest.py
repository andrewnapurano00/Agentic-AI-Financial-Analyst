"""Offline suite boundary: synthetic services only; reject external sockets."""
import ipaddress
import socket
import pytest
import requests
import httpx


@pytest.fixture
def market_dashboard_stub(monkeypatch):
    """Synthetic combined dashboard for page/navigation tests; never transport."""
    from langgraphagenticai.ui import market_dashboard as ui
    import pandas as pd
    record = {"day": 1., "week": 2., "stale": False}
    packet = {"rows": [{"Instrument": "Technology", "Ticker": "XLK", "Group": "Sector", "Level": 100.,
        "1D %": 1., "5D %": 2., "30D %": 3., "60D %": 4., "YTD %": 5., "RSI (14)": 55.,
        "vs SMA 7 %": 1., "evidence": record}], "sectors": {"Technology": record}, "warnings": [], "retrieved_at": "2026-10-16"}
    monkeypatch.setattr(ui, "load_dashboard", lambda *a: packet)
    monkeypatch.setattr(ui, "load_market_news", lambda *a: {"articles": [], "warnings": []})
    monkeypatch.setattr(ui, "load_ribbon", lambda *a: {"rows": [], "warnings": [], "requested": 0, "retrieved_at": "Synthetic"})
    calls = []
    def chart(symbol, key, period):
        calls.append((symbol, period))
        points = list(zip(pd.bdate_range("2026-01-01", periods=220), range(100, 320)))
        return {"symbol": symbol, "points": points, "calculation_points": points, "period": period, "interval": "1d"}
    monkeypatch.setattr(ui, "load_symbol_history", chart)
    monkeypatch.setattr(ui, "interpret_market", lambda *a: (_ for _ in ()).throw(AssertionError("No implicit AI")))
    return ui, packet, calls


def pytest_configure(config):
    # Apply before collection/imports as well as before every test. Some SDKs
    # start telemetry during import; no external traffic is authorized here.
    config._axiom_offline_patch = pytest.MonkeyPatch()
    offline_network.__wrapped__(config._axiom_offline_patch)


def pytest_unconfigure(config):
    patch = getattr(config, '_axiom_offline_patch', None)
    if patch is not None:
        patch.undo()


@pytest.fixture(autouse=True)
def offline_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline tests forbid external provider/model transport')
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    monkeypatch.setattr(httpx.Client, 'send', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, 'send', forbidden)
    try:
        from curl_cffi.requests import Session, AsyncSession
        monkeypatch.setattr(Session, 'request', forbidden)
        monkeypatch.setattr(AsyncSession, 'request', forbidden)
    except ImportError:
        pass
    original = socket.socket.connect
    original_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo
    def resolve(host, *args, **kwargs):
        if host not in (None, 'localhost', '127.0.0.1', '::1'):
            raise AssertionError('Offline tests forbid external DNS resolution')
        return original_resolve(host, *args, **kwargs)
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    def connect(sock, address):
        if isinstance(address, tuple):
            host = address[0]
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == 'localhost'
            if not local:
                raise AssertionError('Offline tests forbid external network connections')
        return original(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', connect)
    def connect_ex(sock, address):
        if isinstance(address, tuple) and address[0] not in ('localhost', '127.0.0.1', '::1'):
            raise AssertionError('Offline tests forbid external network connections')
        return original_ex(sock, address)
    monkeypatch.setattr(socket.socket, 'connect_ex', connect_ex)
