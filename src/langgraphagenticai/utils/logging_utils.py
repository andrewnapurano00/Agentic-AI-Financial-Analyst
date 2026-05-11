from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional


_LOGGER_NAME = "langgraphagenticai"


def _json_default(value: Any):
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": int(time.time()),
        }

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=_json_default, ensure_ascii=False)


def setup_logger(level: Optional[str] = None) -> logging.Logger:
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


def get_logger() -> logging.Logger:
    return setup_logger()


def log_event(message: str, **kwargs) -> None:
    logger = get_logger()
    logger.info(message, extra={"extra_fields": kwargs})


def log_warning(message: str, **kwargs) -> None:
    logger = get_logger()
    logger.warning(message, extra={"extra_fields": kwargs})


def log_error(message: str, **kwargs) -> None:
    logger = get_logger()
    logger.error(message, extra={"extra_fields": kwargs})


@contextmanager
def timed_event(event_name: str, **kwargs):
    start = time.perf_counter()
    try:
        yield
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(event_name, elapsed_ms=elapsed_ms, status="ok", **kwargs)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        log_error(
            event_name,
            elapsed_ms=elapsed_ms,
            status="error",
            error=str(exc),
            **kwargs,
        )
        raise