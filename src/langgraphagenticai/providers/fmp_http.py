from __future__ import annotations

import threading
import math
import time
from urllib.parse import urlsplit
from typing import Any, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from langgraphagenticai.utils.safety import sanitize_error
from langgraphagenticai.security.provider_limits import FMP_LIMITS, ProviderLimited
from langgraphagenticai.utils.logging_utils import log_event


class ProviderRequestError(RuntimeError):
    """Credential-safe provider failure for display, logging, and recovery."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None, transient: bool = False, category: str = "provider"):
        self.provider = provider
        self.status_code = status_code
        self.transient = transient
        self.category = category
        super().__init__(sanitize_error(message, fallback=f"{provider} request failed."))


_local = threading.local()


class BoundedRetry(Retry):
    def get_retry_after(self, response):
        delay = super().get_retry_after(response)
        return min(delay, 2.0) if delay is not None else None


def _session() -> requests.Session:
    session = getattr(_local, "fmp_session", None)
    if session is None:
        session = requests.Session()
        retry = BoundedRetry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.4,
            backoff_max=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10))
        _local.fmp_session = session
    return session


def _fetch_fmp_json(
    url: str,
    *,
    api_key: str,
    params: Mapping[str, Any] | None = None,
    timeout: float | tuple[float, float] = (5.0, 25.0),
) -> Any:
    """Fetch and validate FMP JSON using shared retry, timeout, and safe errors."""
    key = str(api_key or "").strip().strip('"').strip("'")
    if not key:
        raise ProviderRequestError("Financial Modeling Prep", "FMP_API_KEY is not configured.")
    request_params = {key_: value for key_, value in dict(params or {}).items() if value is not None}
    request_params["apikey"] = key
    try:
        response = _session().get(url, params=request_params, timeout=timeout, allow_redirects=False)
        if response.status_code >= 300:
            raise ProviderRequestError(
                "Financial Modeling Prep",
                f"FMP returned HTTP {response.status_code}.",
                status_code=response.status_code,
                transient=response.status_code in {429, 500, 502, 503, 504},
            )
        payload = response.json()
    except ProviderRequestError:
        raise
    except requests.Timeout:
        raise ProviderRequestError("Financial Modeling Prep", "FMP request timed out.", transient=True, category="timeout") from None
    except requests.RequestException:
        raise ProviderRequestError("Financial Modeling Prep", "FMP transport request failed.", transient=True) from None
    except ValueError:
        raise ProviderRequestError("Financial Modeling Prep", "FMP returned invalid JSON.", transient=True, category="schema") from None

    if isinstance(payload, dict):
        provider_error = payload.get("Error Message") or payload.get("error")
        if provider_error:
            raise ProviderRequestError("Financial Modeling Prep", "FMP returned a provider error; check access and request settings.")
    return payload


def get_fmp_json(url, *, api_key, params=None, timeout=(5.0, 25.0)):
    """Allowlisted HTTPS, finite timeouts and process-local credential budgets."""
    try:
        route = urlsplit(url)
        if (route.scheme != "https" or route.hostname not in {"financialmodelingprep.com", "www.financialmodelingprep.com"}
                or route.username or route.password or route.port not in {None, 443} or route.query or route.fragment):
            raise ValueError("Invalid FMP destination")
        durations = tuple(timeout) if isinstance(timeout, (tuple, list)) else (timeout, timeout)
        if len(durations) != 2 or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v <= 0 for v in durations):
            raise ValueError("Invalid timeout")
        bounded = (min(durations[0], 5.0), min(durations[1], 30.0))
    except (ValueError, TypeError, AttributeError):
        raise ProviderRequestError("Financial Modeling Prep", "FMP destination or timeout rejected.") from None
    key = str(api_key or "").strip().strip('"').strip("'")
    if not key:
        raise ProviderRequestError("Financial Modeling Prep", "FMP_API_KEY is not configured.")
    started = time.perf_counter()
    status = "ok"
    category = "unknown"
    try:
        with FMP_LIMITS.request(key) as outcome:
            try:
                return _fetch_fmp_json(url, api_key=key, params=params, timeout=bounded)
            except ProviderRequestError as exc:
                outcome["transient_failure"] = exc.transient
                raise
    except ProviderLimited as exc:
        status = "limited"
        category = "rate_limit"
        raise ProviderRequestError("Financial Modeling Prep", str(exc), status_code=429) from None
    except ProviderRequestError as exc:
        status = "error"
        category = "auth" if exc.status_code in {401, 403} else "rate_limit" if exc.status_code == 429 else exc.category
        raise
    finally:
        log_event("provider_request", provider="fmp", status=status, error_category=category,
                  elapsed_ms=round((time.perf_counter()-started)*1000, 2), tool_calls=1)
