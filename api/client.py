"""
api/client.py
=============
Enterprise-grade HTTP client.

Architecture
------------
Layer 1 – Transport     : requests.Session + urllib3 retry adapter
Layer 2 – Middleware    : pluggable request/response hooks (auth, masking, metrics)
Layer 3 – Observability : structured logging, response-time tracking, Allure attachment
Layer 4 – Assertions    : fluent response object wrapping requests.Response

Features
--------
- Connection pooling with configurable pool size
- Automatic token refresh (OAuth2 client-credentials stub)
- Sensitive field masking in logs (passwords, tokens, secrets)
- Per-request performance metrics collected to a thread-safe store
- Context-manager support
- Proxy + mTLS support
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

import allure
import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import Settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Sensitive keys that must never appear in logs ────────────────────────────
_MASKED_KEYS = frozenset(
    {
        "password", "passwd", "secret", "token", "access_token",
        "refresh_token", "api_key", "authorization", "x-api-key",
        "client_secret", "ssn", "credit_card",
    }
)


def _mask(data: Any, depth: int = 0) -> Any:
    """Recursively mask sensitive fields in dicts/lists for safe logging."""
    if depth > 10:
        return data
    if isinstance(data, dict):
        return {
            k: "***MASKED***" if k.lower() in _MASKED_KEYS else _mask(v, depth + 1)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask(item, depth + 1) for item in data]
    return data


# ── Metrics store ─────────────────────────────────────────────────────────────
@dataclass
class RequestMetric:
    method: str
    url: str
    status_code: int
    elapsed_ms: float
    test_name: str = ""


class MetricsStore:
    """Thread-safe collection of per-request performance metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[RequestMetric] = []

    def record(self, metric: RequestMetric) -> None:
        with self._lock:
            self._records.append(metric)

    @property
    def all(self) -> List[RequestMetric]:
        with self._lock:
            return list(self._records)

    def summary(self) -> dict:
        data = self.all
        if not data:
            return {}
        times = [r.elapsed_ms for r in data]
        return {
            "total_requests": len(data),
            "avg_ms": sum(times) / len(times),
            "max_ms": max(times),
            "min_ms": min(times),
            "failed": sum(1 for r in data if r.status_code >= 400),
        }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


# Module-level singleton store — shared across all client instances in a process
metrics_store = MetricsStore()


# ── Fluent response wrapper ───────────────────────────────────────────────────
class APIResponse:
    """
    Thin wrapper around requests.Response that adds fluent assertion helpers
    and Allure auto-attachment.
    """

    def __init__(self, response: Response, elapsed_ms: float) -> None:
        self._r = response
        self.elapsed_ms = elapsed_ms

    # Delegate attribute access to the underlying response
    def __getattr__(self, name: str) -> Any:
        return getattr(self._r, name)

    # ── Assertions ────────────────────────────────────────────────────────────
    def assert_status(self, expected: int) -> "APIResponse":
        assert self._r.status_code == expected, (
            f"Expected HTTP {expected}, got {self._r.status_code}.\n"
            f"Body: {self._r.text[:1000]}"
        )
        return self

    def assert_status_in(self, *codes: int) -> "APIResponse":
        assert self._r.status_code in codes, (
            f"Expected one of {codes}, got {self._r.status_code}."
        )
        return self

    def assert_json_key(self, key: str) -> "APIResponse":
        body = self._r.json()
        assert key in body, f"Key '{key}' not found in response body: {list(body.keys())}"
        return self

    def assert_json_value(self, key: str, expected: Any) -> "APIResponse":
        body = self._r.json()
        actual = body.get(key)
        assert actual == expected, f"Expected body['{key}']={expected!r}, got {actual!r}"
        return self

    def assert_response_time(self, budget_ms: float) -> "APIResponse":
        assert self.elapsed_ms <= budget_ms, (
            f"SLA breach: {self.elapsed_ms:.1f}ms > budget {budget_ms}ms"
        )
        return self

    def assert_content_type(self, expected: str = "application/json") -> "APIResponse":
        ct = self._r.headers.get("Content-Type", "")
        assert expected in ct, f"Expected Content-Type '{expected}', got '{ct}'"
        return self

    def json(self) -> Any:
        return self._r.json()

    def attach_to_allure(self, name: str = "Response") -> "APIResponse":
        try:
            body = self._r.json()
            allure.attach(
                str(body),
                name=f"{name} (JSON)",
                attachment_type=allure.attachment_type.JSON,
            )
        except Exception:
            allure.attach(
                self._r.text[:5000],
                name=f"{name} (text)",
                attachment_type=allure.attachment_type.TEXT,
            )
        return self


# ── Main client ───────────────────────────────────────────────────────────────
class APIClient:
    """
    Thread-safe, enterprise-grade HTTP client.

    Parameters
    ----------
    base_url      : Override the base URL from Settings.
    extra_headers : Headers merged on every request.
    auth_handler  : Optional callable(session) invoked before each request
                    to inject / refresh auth credentials.
    """

    _RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

    def __init__(
        self,
        base_url: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        auth_handler: Optional[Callable[[Session], None]] = None,
    ) -> None:
        self._settings = Settings()
        self._base_url = (base_url or self._settings.base_url).rstrip("/")
        self._auth_handler = auth_handler
        self._session = self._build_session(extra_headers or {})
        self._last_response: Optional[Response] = None
        self._last_elapsed_ms: float = 0.0
        self._current_test_name: str = ""

        logger.info(
            "APIClient ready | base_url=%s | env=%s | pool=%d",
            self._base_url,
            self._settings.env,
            self._settings.connection_pool_size,
        )

    # ── Session factory ───────────────────────────────────────────────────────
    def _build_session(self, extra_headers: Dict[str, str]) -> Session:
        session = Session()
        session.headers.update(self._settings.default_headers())
        session.headers.update(extra_headers)

        if self._settings.proxies:
            session.proxies.update(self._settings.proxies)

        session.verify = self._settings.ssl_verify
        if self._settings.client_cert:
            session.cert = self._settings.client_cert

        retry_policy = Retry(
            total=self._settings.max_retries,
            backoff_factor=self._settings.retry_backoff,
            status_forcelist=self._RETRY_STATUSES,
            allowed_methods={"GET", "POST", "PUT", "PATCH", "DELETE"},
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        pool = self._settings.connection_pool_size
        adapter = HTTPAdapter(
            max_retries=retry_policy,
            pool_connections=pool,
            pool_maxsize=pool,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ── Core dispatcher ───────────────────────────────────────────────────────
    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params:   Optional[Dict[str, Any]] = None,
        payload:  Optional[Dict[str, Any]] = None,
        headers:  Optional[Dict[str, str]] = None,
        timeout:  Optional[int] = None,
        files:    Optional[Any] = None,
        raw_body: Optional[Any] = None,
    ) -> APIResponse:
        url = f"{self._base_url}{endpoint}"
        effective_timeout = timeout or self._settings.request_timeout

        # Apply auth handler (e.g. token refresh)
        if self._auth_handler:
            self._auth_handler(self._session)

        safe_payload = _mask(payload) if payload else None
        safe_params  = _mask(params)  if params  else None
        logger.info(
            "→ %s %s | params=%s | body=%s",
            method.upper(), url, safe_params, safe_payload,
        )

        t0 = time.perf_counter()
        try:
            kwargs: dict = dict(
                method=method.upper(),
                url=url,
                params=params,
                headers=headers,
                timeout=effective_timeout,
            )
            if files:
                kwargs["files"] = files
            elif raw_body is not None:
                kwargs["data"] = raw_body
            else:
                kwargs["json"] = payload

            response = self._session.request(**kwargs)
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout after %ss on %s %s: %s", effective_timeout, method, url, exc)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error %s %s: %s", method, url, exc)
            raise
        except requests.exceptions.RequestException as exc:
            logger.error("Request error %s %s: %s", method, url, exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._last_elapsed_ms = elapsed_ms

        logger.info(
            "← %s %s | status=%d | %.2fms | %d bytes",
            method.upper(), url, response.status_code, elapsed_ms, len(response.content),
        )
        self._log_body(response)

        # Record metric
        metrics_store.record(RequestMetric(
            method=method.upper(),
            url=url,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            test_name=self._current_test_name,
        ))

        self._last_response = response
        return APIResponse(response, elapsed_ms)

    def _log_body(self, response: Response) -> None:
        try:
            body = _mask(response.json())
            snippet = str(body)[:2000]
            logger.debug("Body: %s%s", snippet, " [TRUNCATED]" if len(str(body)) > 2000 else "")
        except Exception:
            logger.debug("Body (non-JSON): %s", response.text[:500])

    # ── Public HTTP verbs ─────────────────────────────────────────────────────
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> APIResponse:
        return self._request("GET", endpoint, params=params, headers=headers, timeout=timeout)

    def post(self, endpoint: str, payload: Optional[Dict[str, Any]] = None,
             params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
             timeout: Optional[int] = None, files: Optional[Any] = None) -> APIResponse:
        return self._request("POST", endpoint, params=params, payload=payload,
                              headers=headers, timeout=timeout, files=files)

    def put(self, endpoint: str, payload: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None) -> APIResponse:
        return self._request("PUT", endpoint, params=params, payload=payload,
                              headers=headers, timeout=timeout)

    def patch(self, endpoint: str, payload: Optional[Dict[str, Any]] = None,
              params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
              timeout: Optional[int] = None) -> APIResponse:
        return self._request("PATCH", endpoint, params=params, payload=payload,
                              headers=headers, timeout=timeout)

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
               headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> APIResponse:
        return self._request("DELETE", endpoint, params=params, headers=headers, timeout=timeout)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def last_response_time_ms(self) -> float:
        return self._last_elapsed_ms

    def set_test_name(self, name: str) -> None:
        """Called by conftest to tag metrics with the running test name."""
        self._current_test_name = name

    def close(self) -> None:
        self._session.close()
        logger.debug("APIClient session closed.")

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
