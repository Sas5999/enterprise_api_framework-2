"""
conftest.py
===========
Root Pytest configuration — enterprise edition.

Fixture hierarchy
-----------------
session  → settings, api_client
function → user_actions, auth_actions  (lightweight, no state leak between tests)

Extra features
--------------
- Allure environment.properties written at session start
- Per-test request metrics attached to Allure on teardown
- Test name injected into APIClient for metric tagging
- Performance summary printed at session end
"""

from __future__ import annotations

import os
from pathlib import Path

import allure
import pytest

from actions.auth_actions import AuthActions
from actions.user_actions import UserActions
from api.client import APIClient, metrics_store
from config.settings import Settings
from utils.logger import get_logger, setup_logging


# ── Bootstrap logging before anything else ───────────────────────────────────
def pytest_configure(config: pytest.Config) -> None:
    cfg = Settings()
    setup_logging(
        log_level=cfg.log_level,
        log_to_file=cfg.log_to_file,
        log_file_path=cfg.log_file_path,
        log_json=cfg.log_json,
    )
    _write_allure_env(cfg)


def _write_allure_env(cfg: Settings) -> None:
    """Write Allure environment.properties so the report shows runtime config."""
    allure_dir: Path = cfg.allure_results_dir
    allure_dir.mkdir(parents=True, exist_ok=True)
    env_file = allure_dir / "environment.properties"
    env_file.write_text(
        f"Environment={cfg.env}\n"
        f"BaseURL={cfg.base_url}\n"
        f"Timeout={cfg.request_timeout}s\n"
        f"MaxRetries={cfg.max_retries}\n"
        f"PythonVersion={os.popen('python --version').read().strip()}\n",
        encoding="utf-8",
    )


logger = get_logger(__name__)


# ── Session-scoped fixtures ───────────────────────────────────────────────────
@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def api_client(settings: Settings) -> APIClient:
    logger.info("Creating session-scoped APIClient | env=%s", settings.env)
    client = APIClient(base_url=settings.base_url)
    allure.dynamic.label("environment", settings.env)
    yield client
    logger.info("Tearing down APIClient | metrics=%s", metrics_store.summary())
    client.close()


# ── Function-scoped action fixtures (no cross-test state) ─────────────────────
@pytest.fixture
def user_actions(api_client: APIClient) -> UserActions:
    return UserActions(api_client)


@pytest.fixture
def auth_actions(api_client: APIClient) -> AuthActions:
    return AuthActions(api_client)


# ── Test name injection for metrics ──────────────────────────────────────────
@pytest.fixture(autouse=True)
def _inject_test_name(request: pytest.FixtureRequest, api_client: APIClient) -> None:
    api_client.set_test_name(request.node.nodeid)


# ── Allure failure enrichment ─────────────────────────────────────────────────
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report  = outcome.get_result()

    if report.when == "call" and report.failed:
        logger.error("FAILED: %s", item.nodeid)
        allure.attach(
            body=str(report.longrepr),
            name="Failure Details",
            attachment_type=allure.attachment_type.TEXT,
        )

    if report.when == "call":
        summary = metrics_store.summary()
        allure.attach(
            body=str(summary),
            name="Request Metrics",
            attachment_type=allure.attachment_type.TEXT,
        )


# ── Session-end summary ───────────────────────────────────────────────────────
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    summary = metrics_store.summary()
    if summary:
        logger.info(
            "=== METRICS SUMMARY === total=%d avg=%.0fms max=%.0fms failed=%d",
            summary.get("total_requests", 0),
            summary.get("avg_ms", 0),
            summary.get("max_ms", 0),
            summary.get("failed", 0),
        )
