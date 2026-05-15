"""
actions/auth_actions.py
========================
Business Action Layer for Authentication endpoints.
"""

from __future__ import annotations

import allure

from api.client import APIClient, APIResponse
from api.endpoints import endpoints
from utils.logger import get_logger

logger = get_logger(__name__)


class AuthActions:
    """High-level operations for login / register flows."""

    def __init__(self, client: APIClient) -> None:
        self._client = client

    @allure.step("Register | email={email}")
    def register(self, email: str, password: str) -> APIResponse:
        logger.info("Action: register | email=%s", email)
        return self._client.post(
            endpoints.auth.register,
            payload={"email": email, "password": password},
        )

    @allure.step("Login | email={email}")
    def login(self, email: str, password: str) -> APIResponse:
        logger.info("Action: login | email=%s", email)
        return self._client.post(
            endpoints.auth.login,
            payload={"email": email, "password": password},
        )

    @allure.step("Register without password | email={email}")
    def register_without_password(self, email: str) -> APIResponse:
        return self._client.post(endpoints.auth.register, payload={"email": email})

    @allure.step("Login without password | email={email}")
    def login_without_password(self, email: str) -> APIResponse:
        return self._client.post(endpoints.auth.login, payload={"email": email})
