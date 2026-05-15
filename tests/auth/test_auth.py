"""
tests/auth/test_auth.py
=======================
Test suite for authentication endpoints: login and register.
"""

from __future__ import annotations

import allure
import pytest

from actions.auth_actions import AuthActions
from schemas.user_schemas import LOGIN_RESPONSE_SCHEMA, validate_schema
from utils.logger import get_logger

logger = get_logger(__name__)

VALID_EMAIL    = "eve.holt@reqres.in"
VALID_PASSWORD = "cityslicka"


@allure.epic("Authentication API")
@allure.feature("POST /api/login")
class TestLogin:

    @allure.story("Positive — Valid credentials return token")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-AUTH-001 | POST /api/login returns 200 + token")
    @pytest.mark.smoke
    @pytest.mark.positive
    def test_login_success(self, auth_actions: AuthActions) -> None:
        resp = auth_actions.login(VALID_EMAIL, VALID_PASSWORD)
        body = resp.assert_status(200).json()
        assert "token" in body and body["token"]
        validate_schema(body, LOGIN_RESPONSE_SCHEMA, "LoginResponse")

    @allure.story("Negative — Missing password returns 400")
    @allure.title("TC-AUTH-002 | POST /api/login without password → 400")
    @pytest.mark.negative
    def test_login_missing_password(self, auth_actions: AuthActions) -> None:
        resp = auth_actions.login_without_password(VALID_EMAIL)
        resp.assert_status(400)
        assert "error" in resp.json()

    @allure.story("Negative — Non-existent user returns 400")
    @allure.title("TC-AUTH-003 | POST /api/login unknown email → 400")
    @pytest.mark.negative
    def test_login_unknown_user(self, auth_actions: AuthActions) -> None:
        resp = auth_actions.login("nonexistent@example.com", "wrongpass")
        resp.assert_status(400)


@allure.epic("Authentication API")
@allure.feature("POST /api/register")
class TestRegister:

    @allure.story("Positive — Valid registration returns token")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-AUTH-004 | POST /api/register returns 200 + token")
    @pytest.mark.positive
    def test_register_success(self, auth_actions: AuthActions) -> None:
        resp = auth_actions.register(VALID_EMAIL, VALID_PASSWORD)
        body = resp.assert_status(200).json()
        assert "token" in body or "id" in body

    @allure.story("Negative — Missing password returns 400")
    @allure.title("TC-AUTH-005 | POST /api/register without password → 400")
    @pytest.mark.negative
    def test_register_missing_password(self, auth_actions: AuthActions) -> None:
        resp = auth_actions.register_without_password("sydney@fife.com")
        resp.assert_status(400)
        assert "error" in resp.json()
