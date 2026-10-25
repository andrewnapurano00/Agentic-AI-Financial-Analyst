from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
import time
import uuid
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

_LOGGER_NAME = "langgraphagenticai"
_TRACE = ContextVar("axiom_trace", default=None)
_EVENTS = {"graph_initialize", "app_init_failed", "user_prompt_received", "graph_invoke",
           "graph_execution_failed", "assistant_response_ready", "provider_request",
           "checkpoint_save", "checkpoint_read", "checkpoint_export", "checkpoint_delete"}
_CATEGORIES = {"timeout", "auth", "rate_limit", "provider", "model", "schema", "internal", "unknown"}
_PAGES = {"Research", "Deep Research", "AI Robo Advisor", "Equity Report", "AI Valuation",
          "Portfolio Lab", "Introduction", "Top Movers", "Stock Screener", "unknown"}


def _fields(values):
    """Allow metadata, not arbitrary strings, payloads, prompts or exception text."""
    result = {}
    for key, value in values.items():
        if key in {"request_id", "run_id", "thread_id"}:
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", value):
                result[key] = value
        elif key in {"user_input_length", "response_length", "message_count", "tool_calls", "prompt_tokens", "completion_tokens"}:
            if type(value) is int and 0 <= value <= 1_000_000_000:
                result[key] = value
        elif key in {"elapsed_ms", "estimated_cost_usd", "actual_cost_usd"}:
            if type(value) in {int, float} and math.isfinite(value) and 0 <= value <= 1e12:
                result[key] = value
        elif key == "source_ids" and isinstance(value, (list, tuple)):
            result[key] = [hashlib.sha256(v.encode()).hexdigest() for v in value[:20] if isinstance(v, str) and len(v) <= 256]
        elif key == "page" and isinstance(value, str) and value in _PAGES:
            result[key] = value
        elif key == "stage" and isinstance(value, str) and value in _EVENTS | {"unknown"}:
            result[key] = value
        elif key == "provider" and isinstance(value, str) and value in {"fmp", "openai", "groq", "serper", "marketaux", "yahoo", "checkpoint"}:
            result[key] = value
        elif key == "status" and isinstance(value, str) and value in {"ok", "error", "limited", "partial", "unavailable", "blocked"}:
            result[key] = value
        elif key == "verification_status" and isinstance(value, str) and value in {"verified", "unverified", "partial", "unknown"}:
            result[key] = value
        elif key == "error_category" and isinstance(value, str) and value in _CATEGORIES:
            result[key] = value
        elif key == "model_name" and isinstance(value, str):
            result["model_family"] = next((family for family in ("gpt", "o1", "o3", "o4", "llama", "gemini", "claude") if value.lower().startswith(family)), "other")
        elif key == "model_family" and isinstance(value, str) and value in {"gpt", "o1", "o3", "o4", "llama", "gemini", "claude", "other"}:
            result[key] = value
    return result


class JsonFormatter(logging.Formatter):
    def format(self, record):
        event = record.msg if isinstance(record.msg, str) and record.msg in _EVENTS else "unclassified_event"
        payload = {"level": record.levelname if record.levelname in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "UNKNOWN",
                   "logger": _LOGGER_NAME, "message": event, "timestamp": int(time.time())}
        extra = getattr(record, "extra_fields", {})
        payload.update(_fields(extra) if isinstance(extra, dict) else {})
        payload.update(_fields(_TRACE.get() or {}))
        if "request_id" not in payload:
            payload["request_id"] = uuid.uuid4().hex
        if "run_id" not in payload:
            payload["run_id"] = payload["request_id"]
        if record.exc_info:
            payload["error_category"] = "internal"
        return json.dumps(payload, ensure_ascii=True, allow_nan=False)


def setup_logger(level: Optional[str] = None):
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def get_logger():
    return setup_logger()


def log_event(message, **kwargs):
    get_logger().info(message if isinstance(message, str) and message in _EVENTS else "unclassified_event", extra={"extra_fields": _fields(kwargs)})


def log_warning(message, **kwargs):
    get_logger().warning(message if isinstance(message, str) and message in _EVENTS else "unclassified_event", extra={"extra_fields": _fields(kwargs)})


def log_error(message, **kwargs):
    get_logger().error(message if isinstance(message, str) and message in _EVENTS else "unclassified_event", extra={"extra_fields": _fields(kwargs)})


@contextmanager
def run_scope(*, page="unknown", stage="unknown", request_id=None):
    parent = _TRACE.get()
    identity = request_id or uuid.uuid4().hex
    token = _TRACE.set(parent or {"request_id": identity, "run_id": identity, "page": page, "stage": stage})
    try:
        yield (_TRACE.get() or {})["run_id"]
    finally:
        _TRACE.reset(token)


@contextmanager
def timed_event(event_name, **kwargs):
    start = time.perf_counter()
    with run_scope(page=kwargs.get("page", "unknown"), stage=event_name, request_id=kwargs.get("request_id")):
        try:
            yield
        except Exception:
            log_error(event_name, **{**kwargs, "elapsed_ms": round((time.perf_counter()-start)*1000, 2), "status": "error", "error_category": "internal"})
            raise
        else:
            log_event(event_name, **{**kwargs, "elapsed_ms": round((time.perf_counter()-start)*1000, 2), "status": "ok"})
