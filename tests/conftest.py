"""Offline suite boundary: synthetic services only; reject external sockets."""
import ipaddress
import socket
import pytest
import requests
import httpx


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
