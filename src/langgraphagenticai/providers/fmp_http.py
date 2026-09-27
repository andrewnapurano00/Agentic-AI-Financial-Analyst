from __future__ import annotations

import threading
from typing import Any, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from langgraphagenticai.utils.safety import sanitize_error


class ProviderRequestError(RuntimeError):
    """Credential-safe provider failure for display, logging, and recovery."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(sanitize_error(message, fallback=f"{provider} request failed."))


_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_local, "fmp_session", None)
    if session is None:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10))
        _local.fmp_session = session
    return session


def get_fmp_json(
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
        response = _session().get(url, params=request_params, timeout=timeout)
        if response.status_code >= 400:
            raise ProviderRequestError(
                "Financial Modeling Prep",
                f"FMP returned HTTP {response.status_code}.",
                status_code=response.status_code,
            )
        payload = response.json()
    except ProviderRequestError:
        raise
    except requests.Timeout as exc:
        raise ProviderRequestError("Financial Modeling Prep", "FMP request timed out.") from exc
    except requests.RequestException as exc:
        raise ProviderRequestError("Financial Modeling Prep", sanitize_error(exc)) from exc
    except ValueError as exc:
        raise ProviderRequestError("Financial Modeling Prep", "FMP returned invalid JSON.") from exc

    if isinstance(payload, dict):
        provider_error = payload.get("Error Message") or payload.get("error")
        if provider_error:
            raise ProviderRequestError("Financial Modeling Prep", sanitize_error(provider_error))
    return payload
