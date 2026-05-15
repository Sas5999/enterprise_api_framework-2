"""
tests/smoke/test_smoke.py
=========================
Smoke suite — runs in < 30 seconds and blocks any deployment.

Rule: each test makes exactly ONE request.  If any smoke test fails,
CI stops immediately.  Coverage is breadth > depth.
"""

from __future__ import annotations

import allure
import pytest

from actions.auth_actions import AuthActions
from actions.user_actions import UserActions
from utils.logger import get_logger

logger = get_logger(__name__)


@allure.epic("Smoke Suite")
@allure.feature("API Health Gate")
class TestSmoke:

    @allure.title("SMOKE-001 | GET /users/2 → 200")
    @pytest.mark.smoke
    def test_get_user(self, user_actions: UserActions) -> None:
        user_actions.get_user(2).assert_status(200)

    @allure.title("SMOKE-002 | GET /users → 200")
    @pytest.mark.smoke
    def test_list_users(self, user_actions: UserActions) -> None:
        user_actions.list_users().assert_status(200)

    @allure.title("SMOKE-003 | POST /users → 201")
    @pytest.mark.smoke
    def test_create_user(self, user_actions: UserActions) -> None:
        user_actions.create_user("Smoke User", "Tester").assert_status(201)

    @allure.title("SMOKE-004 | DELETE /users/2 → 204")
    @pytest.mark.smoke
    def test_delete_user(self, user_actions: UserActions) -> None:
        user_actions.delete_user(2).assert_status(204)

    @allure.title("SMOKE-005 | POST /login → 200")
    @pytest.mark.smoke
    def test_login(self, auth_actions: AuthActions) -> None:
        auth_actions.login("eve.holt@reqres.in", "cityslicka").assert_status(200)

    @allure.title("SMOKE-006 | GET /users/9999 → 404")
    @pytest.mark.smoke
    def test_not_found(self, user_actions: UserActions) -> None:
        user_actions.get_user(9999).assert_status(404)
