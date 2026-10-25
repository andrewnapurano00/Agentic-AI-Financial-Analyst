"""Offline AX-10 adversarial access, storage, telemetry and transport contracts."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import importlib.util
import json
import logging
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest
import requests
from urllib3.exceptions import MaxRetryError

from langgraphagenticai.security.checkpoints import CheckpointStore, CheckpointDenied
from langgraphagenticai.security.provider_limits import ProviderLimits, ProviderLimited
from langgraphagenticai.security.runtime import runtime_block_reason
from langgraphagenticai.utils import logging_utils as logs
from langgraphagenticai.providers import fmp_http as fmp


def packet():
    return {"kind": "research_report", "status": "partial", "report": "Saved private thesis < 0, -12 USD",
            "value": 0, "api_key": "secret-plain", "prompt": "private system prompt"}


@pytest.fixture
def vault(tmp_path):
    clock = [1000]
    key = bytes(range(32))
    return CheckpointStore(tmp_path/"vault", key, clock=lambda: clock[0]), key, clock


def test_checkpoint_restart_encryption_redaction_and_explicit_export(vault):
    store, key, clock = vault
    grant = store.issue_for_authenticated_owner("alice")
    run, revision = store.save(grant, packet())
    assert revision == 1
    raw = store.path.read_bytes()
    for private in (b"alice", b"private thesis", b"secret-plain", b"private system prompt"):
        assert private not in raw
    restarted = CheckpointStore(store.path.parent, key, clock=lambda: clock[0])
    rev, saved = restarted.read(grant, run)
    assert rev == 1 and saved["status"] == "partial" and saved["value"] == 0
    assert "-12 USD" in saved["report"] and "api_key" not in saved and "prompt" not in saved
    assert json.loads(restarted.export(grant, run))["saved"] == saved


def test_owner_separation_same_run_id_and_no_read_export_delete_escalation(vault):
    store, _, _ = vault
    alice = store.issue_for_authenticated_owner("alice")
    bob = store.issue_for_authenticated_owner("bob")
    run, _ = store.save(alice, packet())
    for action in (lambda: store.read(bob, run), lambda: store.export(bob, run),
                   lambda: store.delete(bob, run, expected_revision=1)):
        with pytest.raises(CheckpointDenied): action()
    other = {**packet(), "report": "Bob's distinct record"}
    store.save(bob, other, run_id=run)
    assert store.read(bob, run)[1]["report"] != store.read(alice, run)[1]["report"]
    forged = replace(bob, owner="alice")
    with pytest.raises(CheckpointDenied): store.read(forged, run)
    readonly = store.issue_for_authenticated_owner("alice", scopes=("read",))
    assert store.read(readonly, run)[0] == 1
    for action in (lambda: store.save(readonly, packet()), lambda: store.export(readonly, run)):
        with pytest.raises(CheckpointDenied): action()


def test_grant_expiry_and_scope_tampering_and_key_rotation_fail_closed(vault):
    store, _, clock = vault
    grant = store.issue_for_authenticated_owner("alice", scopes=("read", "write"), ttl=10)
    run, _ = store.save(grant, packet())
    with pytest.raises(CheckpointDenied): store.export(replace(grant, scopes=(*grant.scopes, "export")), run)
    clock[0] = 1010
    for action in (lambda: store.read(grant, run), lambda: store.save(grant, packet(), run_id=run, expected_revision=1)):
        with pytest.raises(CheckpointDenied): action()
    rotated = CheckpointStore(store.path.parent, b"x"*32, clock=lambda: 1001)
    with pytest.raises(CheckpointDenied): rotated.read(grant, run)
    with pytest.raises(CheckpointDenied): rotated.read(rotated.issue_for_authenticated_owner("alice"), run)


def test_simultaneous_updates_are_cas_not_last_writer_wins(vault):
    store, _, _ = vault
    grant = store.issue_for_authenticated_owner("alice")
    run, _ = store.save(grant, packet())
    def update(text):
        try:
            return store.save(grant, {**packet(), "report": text}, run_id=run, expected_revision=1)[1]
        except CheckpointDenied:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, ["first", "second"]))
    assert sorted(map(str, outcomes)) == ["2", "conflict"]
    assert store.read(grant, run)[0] == 2


@pytest.mark.parametrize("column", ["payload", "revision", "nonce"])
def test_ciphertext_and_metadata_tampering_is_detected(vault, column):
    store, _, _ = vault
    grant = store.issue_for_authenticated_owner("alice")
    run, _ = store.save(grant, packet())
    with sqlite3.connect(store.path) as db:
        db.execute({"payload": "UPDATE checkpoints SET payload=zeroblob(length(payload))",
                    "nonce": "UPDATE checkpoints SET nonce=zeroblob(12)",
                    "revision": "UPDATE checkpoints SET revision=99"}[column])
    with pytest.raises(CheckpointDenied, match="integrity"):
        store.read(grant, run)


def test_storage_quota_and_hostile_run_id_do_not_touch_files(vault):
    store, _, _ = vault
    grant = store.issue_for_authenticated_owner("alice")
    for hostile in ("../outside", "/etc/passwd", "title.pdf", "A"*32):
        with pytest.raises(CheckpointDenied): store.save(grant, packet(), run_id=hostile)
    for _ in range(20): store.save(grant, packet())
    with pytest.raises(ValueError, match="quota"): store.save(grant, packet())
    with pytest.raises(ValueError, match="megabyte"): store.save(grant, {**packet(), "report": "x"*1_000_000})
    assert not (store.path.parent.parent/"outside").exists()


def test_local_encrypted_backup_restore_preserves_partial_result(vault, tmp_path):
    store, key, clock = vault
    grant = store.issue_for_authenticated_owner("alice")
    run, _ = store.save(grant, packet())
    restored = CheckpointStore(tmp_path/"restored", key, clock=lambda: clock[0])
    with sqlite3.connect(store.path) as source, sqlite3.connect(restored.path) as target:
        source.backup(target)
    assert restored.read(grant, run) == store.read(grant, run)
    assert b"private thesis" not in restored.path.read_bytes()
    restored.delete(grant, run, expected_revision=1)
    with pytest.raises(CheckpointDenied): restored.read(grant, run)
    assert store.read(grant, run)[0] == 1


def test_unknown_and_hosted_modes_fail_closed_before_controls(monkeypatch):
    assert runtime_block_reason({}) is None
    assert runtime_block_reason({"AXIOM_RUNTIME_MODE": ""}) is None
    assert runtime_block_reason({"AXIOM_RUNTIME_MODE": "typo"})
    monkeypatch.setenv("AXIOM_RUNTIME_MODE", "hosted")
    from langgraphagenticai import main
    from streamlit.testing.v1 import AppTest
    controls = Mock(side_effect=AssertionError("Credentials/controls must not load"))
    monkeypatch.setattr(main, "LoadStreamlitUI", controls)
    app = AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()", default_timeout=45).run()
    assert not app.exception and app.error and "Hosted access is disabled" in app.error[0].value
    controls.assert_not_called()
    assert "chat_history" not in app.session_state


def record(message="provider_request", **fields):
    result = logging.LogRecord("untrusted", logging.INFO, "", 1, message, (), None)
    result.extra_fields = fields
    return result


def test_strict_logs_drop_secrets_prompts_holdings_and_exception_trace():
    secret = "private-bare-secret-12345"
    event = record(secret, error=secret, prompt=secret, holdings=[secret], timestamp=secret,
                   provider=secret, page={"secret": secret}, model_name=secret, source_ids=[secret],
                   estimated_cost_usd=.02, actual_cost_usd=float("nan"))
    try:
        raise RuntimeError(secret)
    except RuntimeError:
        event.exc_info = sys.exc_info()
    raw = logs.JsonFormatter().format(event)
    assert secret not in raw and "traceback" not in raw.lower() and "NaN" not in raw
    data = json.loads(raw)
    assert data["message"] == "unclassified_event" and data["estimated_cost_usd"] == .02
    assert "actual_cost_usd" not in data and "error" not in data and len(data["source_ids"][0]) == 64


def test_trace_scopes_do_not_cross_threads_or_survive_exception():
    def work(_):
        with logs.run_scope(page="Research", stage="graph_invoke") as identity:
            first = json.loads(logs.JsonFormatter().format(record()))
            with logs.run_scope(page="Deep Research"):
                second = json.loads(logs.JsonFormatter().format(record()))
            assert first["run_id"] == second["run_id"] == identity
            return identity
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert len(set(pool.map(work, range(2)))) == 2
    with pytest.raises(RuntimeError):
        with logs.run_scope(): raise RuntimeError("private")
    assert logs._TRACE.get() is None


def test_sensitive_fields_are_removed_before_any_logging_handler(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(logs, "get_logger", lambda: logger)
    logs.log_error("private-bare-secret", prompt="private-bare-secret", error="private-bare-secret", model_name="gpt-5", tool_calls=2)
    assert "private-bare-secret" not in str(logger.mock_calls)
    assert logger.error.call_args.args[0] == "unclassified_event"
    assert logger.error.call_args.kwargs["extra"]["extra_fields"]["tool_calls"] == 2


def test_provider_quota_credentials_and_concurrent_permits_are_isolated():
    clock = [0]
    guard = ProviderLimits(clock=lambda: clock[0], per_minute=1, concurrent=1)
    with guard.request("private-a"):
        with pytest.raises(ProviderLimited):
            with guard.request("private-a"): pass
        with guard.request("private-b"): pass
    with pytest.raises(ProviderLimited):
        with guard.request("private-a"): pass
    assert "private-a" not in repr(guard._buckets)
    clock[0] = 60
    with guard.request("private-a"): pass


def test_transient_circuit_single_probe_and_recovery():
    clock = [0]
    guard = ProviderLimits(clock=lambda: clock[0], failures=2, cooldown=30)
    for _ in range(2):
        with guard.request("key") as outcome: outcome["transient_failure"] = True
    with pytest.raises(ProviderLimited, match="circuit"):
        with guard.request("key"): pass
    clock[0] = 30
    with guard.request("key"):
        with pytest.raises(ProviderLimited):
            with guard.request("key"): pass
    with guard.request("key"): pass


def test_failed_half_open_probe_reopens_and_guard_registry_is_bounded():
    clock = [0]
    guard = ProviderLimits(clock=lambda: clock[0], failures=1, cooldown=30, capacity=1)
    with guard.request("key") as outcome: outcome["transient_failure"] = True
    clock[0] = 30
    with guard.request("key") as outcome: outcome["transient_failure"] = True
    clock[0] = 31
    with pytest.raises(ProviderLimited):
        with guard.request("key"): pass
    with pytest.raises(ProviderLimited, match="capacity"):
        with guard.request("other"): pass
    clock[0] = 4000
    with guard.request("other"): pass


def test_global_concurrency_is_bounded_across_credentials():
    guard = ProviderLimits(global_concurrent=1)
    with guard.request("first"):
        with pytest.raises(ProviderLimited, match="concurrency"):
            with guard.request("second"): pass
    with guard.request("second"): pass


@pytest.fixture
def transport(monkeypatch):
    session = Mock()
    session.get.return_value = SimpleNamespace(status_code=200, json=lambda: [{"price": 0}])
    monkeypatch.setattr(fmp, "_session", lambda: session)
    monkeypatch.setattr(fmp, "FMP_LIMITS", ProviderLimits())
    return session


def test_fmp_timeout_redirect_and_successful_zero_contract(transport):
    assert fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key="fixture", timeout=(100, 100)) == [{"price": 0}]
    assert transport.get.call_args.kwargs["timeout"] == (5., 30.)
    assert transport.get.call_args.kwargs["allow_redirects"] is False
    transport.get.return_value.status_code = 302
    with pytest.raises(fmp.ProviderRequestError, match="302"):
        fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key="fixture")


@pytest.mark.parametrize("url", ["http://financialmodelingprep.com/x", "https://evil.test/x", "https://financialmodelingprep.com@evil.test/x", "https://financialmodelingprep.com/x?apikey=fixture", "https://financialmodelingprep.com:22/x"])
def test_fmp_never_sends_key_to_unsafe_destination(transport, url):
    with pytest.raises(fmp.ProviderRequestError, match="rejected"):
        fmp.get_fmp_json(url, api_key="fixture")
    transport.get.assert_not_called()


@pytest.mark.parametrize("timeout", [None, float("nan"), 0, True, (5, -1), (1, 2, 3)])
def test_fmp_invalid_timeouts_fail_before_network(transport, timeout):
    with pytest.raises(fmp.ProviderRequestError):
        fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key="fixture", timeout=timeout)
    transport.get.assert_not_called()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_provider_failure_opens_circuit_and_limits_network_attempts(transport, status):
    transport.get.return_value.status_code = status
    for _ in range(5):
        with pytest.raises(fmp.ProviderRequestError):
            fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key="fixture")
    with pytest.raises(fmp.ProviderRequestError, match="circuit"):
        fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key="fixture")
    assert transport.get.call_count == 5


def test_timeout_error_never_echoes_bare_credential(transport):
    credential = "fixture-private-secret"; transport.get.side_effect = requests.ConnectionError(credential)
    with pytest.raises(fmp.ProviderRequestError) as error:
        fmp.get_fmp_json("https://financialmodelingprep.com/stable/quote", api_key=credential)
    assert "fixture-private-secret" not in str(error.value)
    import traceback
    assert "fixture-private-secret" not in "".join(traceback.format_exception(error.value))


def test_retry_after_sleep_and_actual_retry_count_are_bounded():
    retry = fmp.BoundedRetry(total=2, status=2, allowed_methods={"GET"}, status_forcelist={503})
    response = SimpleNamespace(status=503, headers={"Retry-After": "9999999"}, get_redirect_location=lambda: None)
    assert retry.get_retry_after(response) == 2
    retry = retry.increment("GET", "/route", response=response)
    retry = retry.increment("GET", "/route", response=response)
    with pytest.raises(MaxRetryError): retry.increment("GET", "/route", response=response)


def test_release_manifest_cannot_activate_hosted_mode():
    path = Path(__file__).resolve().parents[1]/"scripts/release_gate.py"
    spec = importlib.util.spec_from_file_location("release_gate", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    all_pass = {gate: "passed" for gate in module.GATES}
    result = module.report(all_pass)
    assert not result["production_ready"] and "hosted_identity_adapter" in result["blocking_gates"]
    with pytest.raises(ValueError): module.report({"offline_tests": "passed"})


def test_graph_resource_memory_is_session_scoped_with_identical_credentials(monkeypatch):
    from langgraphagenticai import main
    from streamlit.testing.v1 import AppTest
    import streamlit as st
    from streamlit.runtime.caching import cache_resource_api
    # AppTest hardcodes every runner's ID to "test session id". Model actual
    # browser sessions' distinct IDs while retaining each test session on rerun.
    monkeypatch.setattr(cache_resource_api, "get_session_id_or_throw",
                        lambda: st.session_state.setdefault("_test_session_id", uuid.uuid4().hex))
    built = []
    def build_graph(**kwargs):
        built.append(len(built)+1)
        return SimpleNamespace(build_finance_graph=lambda: {"memory_id": built[-1]})
    monkeypatch.setattr(main, "OpenAILLM", lambda **kw: SimpleNamespace(get_llm_model=lambda: None))
    monkeypatch.setattr(main, "get_finance_tools", lambda **kw: [])
    monkeypatch.setattr(main, "GraphBuilder", build_graph)
    page = '''
import streamlit as st
from langgraphagenticai.main import _build_cached_graph
graph = _build_cached_graph("same-fixture", "same-model", "same-fmp", "Basic Finance Chat")
st.session_state["memory_id"] = graph["memory_id"]
'''
    one = AppTest.from_string(page, default_timeout=30).run()
    one.run()
    two = AppTest.from_string(page, default_timeout=30).run()
    assert not one.exception and not two.exception
    assert one.session_state["memory_id"] != two.session_state["memory_id"]
    assert len(built) == 2


def test_chat_invocation_bounds_loops_and_reruns_do_not_invoke(monkeypatch, market_dashboard_stub):
    from langgraphagenticai import main
    from langgraphagenticai.ui.streamlitui import loadui
    from streamlit.testing.v1 import AppTest
    from langgraph.errors import GraphRecursionError
    calls = []
    class LoopingGraph:
        def invoke(self, packet, config):
            calls.append(config)
            assert config["recursion_limit"] == 12
            raise GraphRecursionError("Synthetic runaway loop")
    monkeypatch.setattr(loadui, "_resolve_secret", lambda *a: "fixture")
    monkeypatch.setattr(main, "_build_cached_graph", lambda **k: LoopingGraph())
    monkeypatch.setattr(main, "_build_repair_llm", lambda **k: None)
    app = AppTest.from_string("from langgraphagenticai.main import load_langgraph_agenticai_app; load_langgraph_agenticai_app()", default_timeout=45)
    app.session_state["active_workspace"] = "Research"
    app.run()
    app.text_area(key="research_request_draft").set_value("Run a fixture")
    app.button(key="research_submit").click().run()
    assert not app.exception and len(calls) == 1 and app.error
    assert app.session_state["chat_history"][-1]["content"] == "Run a fixture"
    app.run()
    assert len(calls) == 1
