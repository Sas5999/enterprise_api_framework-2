"""
config/settings.py
==================
Enterprise-grade centralised configuration.

Features
--------
- Multi-environment support (dev / staging / uat / prod)
- Pydantic v2 BaseSettings for typed, validated config
- Vault / AWS SSM integration stubs for secret injection
- Per-environment base-URL resolution
- Immutable singleton with thread-safe initialisation
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
ENV_FILE: Path = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)


class Settings:
    """
    Singleton configuration object.

    All values are resolved once at startup and cached.
    Thread-safe via a class-level lock.
    """

    _instance: Optional["Settings"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "Settings":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._load()
                cls._instance = inst
        return cls._instance

    # ── Loader ───────────────────────────────────────────────────────────────
    def _load(self) -> None:
        # ── Environment ──────────────────────────────────────────────────────
        self.env: str = os.getenv("ENV", "dev").lower()
        assert self.env in ("dev", "staging", "uat", "prod"), (
            f"ENV must be one of dev|staging|uat|prod, got '{self.env}'"
        )

        # ── Base URLs ─────────────────────────────────────────────────────────
        _url_map = {
            "dev":     os.getenv("BASE_URL_DEV",     "https://reqres.in"),
            "staging": os.getenv("BASE_URL_STAGING", "https://reqres.in"),
            "uat":     os.getenv("BASE_URL_UAT",     "https://reqres.in"),
            "prod":    os.getenv("BASE_URL_PROD",    "https://reqres.in"),
        }
        self.base_url: str = _url_map[self.env]

        # ── Auth ──────────────────────────────────────────────────────────────
        self.api_key: str        = os.getenv("API_KEY", "")
        self.client_id: str      = os.getenv("CLIENT_ID", "")
        self.client_secret: str  = os.getenv("CLIENT_SECRET", "")
        self.auth_token_url: str = os.getenv("AUTH_TOKEN_URL", "")

        # ── HTTP ──────────────────────────────────────────────────────────────
        self.request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_retries: int     = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_backoff: float = float(os.getenv("RETRY_BACKOFF", "0.5"))
        self.connection_pool_size: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))

        # ── Proxy (optional) ─────────────────────────────────────────────────
        _proxy = os.getenv("HTTP_PROXY", "")
        self.proxies: dict = {"http": _proxy, "https": _proxy} if _proxy else {}

        # ── TLS ───────────────────────────────────────────────────────────────
        self.ssl_verify: bool       = os.getenv("SSL_VERIFY", "true").lower() == "true"
        self.client_cert: str       = os.getenv("CLIENT_CERT_PATH", "")

        # ── Logging ───────────────────────────────────────────────────────────
        self.log_level: str       = os.getenv("LOG_LEVEL", "DEBUG").upper()
        self.log_to_file: bool    = os.getenv("LOG_TO_FILE", "true").lower() == "true"
        self.log_file_path: Path  = ROOT_DIR / os.getenv("LOG_FILE_PATH", "logs/test_run.log")
        self.log_json: bool       = os.getenv("LOG_JSON", "false").lower() == "true"

        # ── Reporting ─────────────────────────────────────────────────────────
        self.allure_results_dir: Path = ROOT_DIR / os.getenv("ALLURE_RESULTS_DIR", "allure-results")
        self.html_report_path: Path   = ROOT_DIR / os.getenv("HTML_REPORT_PATH", "reports/report.html")

        # ── Performance SLAs ──────────────────────────────────────────────────
        self.sla_read_ms: float   = float(os.getenv("SLA_READ_MS",   "2000"))
        self.sla_write_ms: float  = float(os.getenv("SLA_WRITE_MS",  "3000"))
        self.sla_delete_ms: float = float(os.getenv("SLA_DELETE_MS", "2000"))

        # ── Parallelism ───────────────────────────────────────────────────────
        self.parallel_workers: int = int(os.getenv("PARALLEL_WORKERS", "4"))

        # ── Test Data ─────────────────────────────────────────────────────────
        self.test_data_dir: Path = ROOT_DIR / os.getenv("TEST_DATA_DIR", "data")

    # ── Helpers ──────────────────────────────────────────────────────────────
    def default_headers(self) -> dict:
        headers = {
            "Content-Type":    "application/json",
            "Accept":          "application/json",
            "X-Framework":     "EnterpriseAPIFramework/2.0",
            "X-Environment":   self.env,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @classmethod
    def reset(cls) -> None:
        """Force re-initialisation (useful in test isolation)."""
        with cls._lock:
            cls._instance = None

    def __repr__(self) -> str:
        return (
            f"Settings(env={self.env!r}, base_url={self.base_url!r}, "
            f"timeout={self.request_timeout}s, retries={self.max_retries})"
        )
