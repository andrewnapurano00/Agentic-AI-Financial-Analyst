"""Offline single-owner access and deployable archive regressions."""
import importlib.util
from pathlib import Path
import zipfile

import pytest
from streamlit.testing.v1 import AppTest

from langgraphagenticai.security import space_owner as owner
from langgraphagenticai.security.runtime import runtime_block_reason


@pytest.fixture
def owner_config(monkeypatch):
    monkeypatch.setenv("AXIOM_RUNTIME_MODE", "huggingface_single_owner")
    monkeypatch.setenv("AXIOM_OWNER_PASSWORD", "synthetic-owner-password-12345")
    owner._ATTEMPTS.clear()
    yield
    owner._ATTEMPTS.clear()


def gate():
    return AppTest.from_string(
        "from langgraphagenticai.security.runtime import enforce_runtime_access\n"
        "enforce_runtime_access()\nimport streamlit as st\nst.success('workspace reached')",
        default_timeout=30,
    ).run()


def sign_in(app, password="synthetic-owner-password-12345"):
    app.text_input[0].set_value(password)
    app.button[0].click().run()
    return app


@pytest.mark.parametrize("password", ["", "short", "x" * 1025])
def test_single_owner_missing_or_invalid_password_blocks(password, monkeypatch, owner_config):
    monkeypatch.setenv("AXIOM_OWNER_PASSWORD", password)
    app = gate()
    assert not app.exception and app.error and not app.success and not app.text_input
    assert runtime_block_reason({"AXIOM_RUNTIME_MODE": "hosted"})


def test_sign_in_does_not_authorize_other_sessions_and_logout_clears_work(owner_config):
    app = gate()
    assert not app.success
    sign_in(app, "incorrect")
    assert app.error and not app.success
    sign_in(app)
    assert not app.exception and app.success
    assert "_axiom_owner_password" not in app.session_state
    app.session_state["saved_report"] = "private synthetic work"
    other = gate()
    assert not other.success and "saved_report" not in other.session_state
    app.button[0].click().run()
    assert not app.exception and not app.success and app.text_input
    assert "saved_report" not in app.session_state


@pytest.mark.parametrize("invalidate", ["rotation", "expiry"])
def test_rotation_and_expiry_require_sign_in(invalidate, monkeypatch, owner_config):
    app = sign_in(gate())
    app.session_state["saved_report"] = "private synthetic work"
    if invalidate == "rotation":
        monkeypatch.setenv("AXIOM_OWNER_PASSWORD", "new-synthetic-owner-password-12345")
    else:
        fingerprint, stamp = app.session_state["_axiom_owner_auth"]
        app.session_state["_axiom_owner_auth"] = (fingerprint, stamp - owner._SESSION_SECONDS - 1)
    app.run()
    assert not app.exception and not app.success and app.text_input
    assert "saved_report" not in app.session_state


def test_attempt_budget_is_shared_and_recovers(owner_config):
    for _ in range(5):
        assert not owner.authenticate("wrong", "correct", now=10)
    assert not owner.authenticate("correct", "correct", now=69)
    assert owner.authenticate("correct", "correct", now=70)


def exporter():
    path = Path(__file__).resolve().parents[1] / "scripts/export_huggingface.py"
    spec = importlib.util.spec_from_file_location("hf_export_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_archive_includes_theme_and_excludes_private_outputs(tmp_path, monkeypatch):
    module = exporter()
    for name in module.REQUIRED + ("src/package.py",):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic runtime file", encoding="utf-8")
    (tmp_path / ".env").write_text("must not export", encoding="utf-8")
    (tmp_path / "private_report.json").write_text("must not export", encoding="utf-8")
    monkeypatch.setattr(module.subprocess, "check_output", lambda *a, **k: b"src/package.py\0")
    target = tmp_path / "exports/runtime.zip"
    module.build_archive(tmp_path, target)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(module.REQUIRED) | {"src/package.py"}
        assert b"sdk: docker" in archive.read("README.md")
        assert ".streamlit/config.toml" in archive.namelist()
    # Missing public configuration must fail instead of emitting another broken ZIP.
    (tmp_path / ".streamlit/config.toml").unlink()
    with pytest.raises(ValueError, match="Missing"):
        module.build_archive(tmp_path, target)


def test_image_copies_the_dark_theme_and_uses_owner_gate():
    import tomllib
    root = Path(__file__).resolve().parents[1]
    docker = (root / "Dockerfile").read_text()
    theme = tomllib.loads((root / ".streamlit/config.toml").read_text())
    assert theme["theme"]["base"] == "dark"
    assert "COPY --chown=1000:1000 .streamlit/config.toml ./.streamlit/config.toml" in docker
    assert "AXIOM_RUNTIME_MODE=huggingface_single_owner" in docker
