"""
actions/user_actions.py
========================
Layer 3 – Business Action Layer for the User resource.

Separates *what* we do (business semantics) from *how* (HTTP mechanics).
Tests call these methods; the APIClient handles transport.

Every public method:
  1. Has an @allure.step decorator for report visibility
  2. Logs entry / exit at INFO
  3. Returns APIResponse (fluent wrapper, not raw requests.Response)
"""

from __future__ import annotations

from typing import Any, Optional

import allure
from requests import Response

from api.client import APIClient, APIResponse
from api.endpoints import endpoints
from utils.logger import get_logger

logger = get_logger(__name__)


class UserActions:
    """High-level operations for the /users resource."""

    def __init__(self, client: APIClient) -> None:
        self._client = client

    # ── Read ─────────────────────────────────────────────────────────────────
    @allure.step("Get single user | user_id={user_id}")
    def get_user(self, user_id: int) -> APIResponse:
        logger.info("Action: get_user | user_id=%d", user_id)
        return self._client.get(endpoints.users.single(user_id))

    @allure.step("List users | page={page} per_page={per_page}")
    def list_users(self, page: int = 1, per_page: int = 6) -> APIResponse:
        logger.info("Action: list_users | page=%d per_page=%d", page, per_page)
        return self._client.get(
            endpoints.users.list_users,
            params={"page": page, "per_page": per_page},
        )

    # ── Write ─────────────────────────────────────────────────────────────────
    @allure.step("Create user | name={name} job={job}")
    def create_user(self, name: str, job: str) -> APIResponse:
        logger.info("Action: create_user | name=%s job=%s", name, job)
        return self._client.post(
            endpoints.users.create_user,
            payload={"name": name, "job": job},
        )

    @allure.step("Create user from payload")
    def create_user_from_payload(self, payload: dict) -> APIResponse:
        logger.info("Action: create_user_from_payload | payload=%s", payload)
        return self._client.post(endpoints.users.create_user, payload=payload)

    @allure.step("Update user (PUT) | user_id={user_id}")
    def update_user(self, user_id: int, name: str, job: str) -> APIResponse:
        logger.info("Action: update_user | user_id=%d", user_id)
        return self._client.put(
            endpoints.users.update(user_id),
            payload={"name": name, "job": job},
        )

    @allure.step("Patch user | user_id={user_id}")
    def patch_user(self, user_id: int, **fields: Any) -> APIResponse:
        logger.info("Action: patch_user | user_id=%d | fields=%s", user_id, fields)
        return self._client.patch(
            endpoints.users.update(user_id),
            payload=dict(fields),
        )

    @allure.step("Delete user | user_id={user_id}")
    def delete_user(self, user_id: int) -> APIResponse:
        logger.info("Action: delete_user | user_id=%d", user_id)
        return self._client.delete(endpoints.users.delete(user_id))
