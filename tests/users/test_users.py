"""
tests/users/test_users.py
=========================
Enterprise test suite for the /users resource.

Test categories (pytest marks)
-------------------------------
smoke       → fastest, run on every commit
positive    → happy-path functional tests
negative    → error-handling and boundary conditions
schema      → JSON-schema contract tests (API drift detection)
performance → SLA enforcement tests
regression  → full regression sweep

Coverage map
------------
TC-001  GET  /users/{id}         → 200 + status
TC-002  GET  /users/{id}         → schema contract
TC-003  GET  /users/{id}         → data values
TC-004  GET  /users/{id}         → response-time SLA
TC-005  GET  /users/9999         → 404 not found
TC-006  POST /users              → 201 created
TC-007  POST /users              → factory-generated payload
TC-008  PUT  /users/{id}         → 200 full replace
TC-009  PATCH /users/{id}        → 200 partial update
TC-010  DELETE /users/{id}       → 204 no content
TC-011  GET  /users?page=2       → list pagination
TC-012  GET  /users              → list schema contract
TC-013  POST /users (boundary)   → parametrised invalid payloads
TC-014  GET  /users/{id}         → concurrent requests (thread safety)
"""

from __future__ import annotations

import threading
from typing import Any

import allure
import pytest

from actions.user_actions import UserActions
from api.client import APIClient
from config.settings import Settings
from data.factories.user_factory import UserFactory
from schemas.user_schemas import (
    CREATE_USER_RESPONSE_SCHEMA,
    SINGLE_USER_RESPONSE_SCHEMA,
    UPDATE_USER_RESPONSE_SCHEMA,
    USER_LIST_RESPONSE_SCHEMA,
    validate_schema,
)
from utils.logger import get_logger

logger = get_logger(__name__)

TARGET_USER_ID  = 2
MISSING_USER_ID = 9999


# ════════════════════════════════════════════════════════════════════════════
# GET /api/users/{id}
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("GET /api/users/{id}")
class TestGetSingleUser:

    @allure.story("Positive — 200 status and non-empty body")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-001 | GET /users/2 returns 200")
    @pytest.mark.smoke
    @pytest.mark.positive
    def test_status_200(self, user_actions: UserActions) -> None:
        resp = user_actions.get_user(TARGET_USER_ID)
        resp.assert_status(200).attach_to_allure("Get User")

    @allure.story("Contract — JSON schema never drifts")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-002 | GET /users/2 response matches schema contract")
    @pytest.mark.schema
    def test_schema_contract(self, user_actions: UserActions) -> None:
        resp = user_actions.get_user(TARGET_USER_ID)
        resp.assert_status(200)
        validate_schema(resp.json(), SINGLE_USER_RESPONSE_SCHEMA, "SingleUserResponse")

    @allure.story("Positive — Exact data values")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-003 | User ID=2 has expected identity data")
    @pytest.mark.positive
    @pytest.mark.regression
    def test_data_values(self, user_actions: UserActions) -> None:
        resp = user_actions.get_user(TARGET_USER_ID)
        user = resp.assert_status(200).json()["data"]

        with allure.step("Assert user ID"):
            assert user["id"] == TARGET_USER_ID

        with allure.step("Assert first_name is 'Janet'"):
            assert user["first_name"] == "Janet"

        with allure.step("Assert last_name is 'Weaver'"):
            assert user["last_name"] == "Weaver"

        with allure.step("Assert email"):
            assert user["email"] == "janet.weaver@reqres.in"

        with allure.step("Assert avatar is a non-empty URL"):
            assert user["avatar"] and user["avatar"].startswith("http")

    @allure.story("Performance — Response time within SLA")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("TC-004 | GET /users/2 responds within SLA")
    @pytest.mark.performance
    def test_response_time_sla(
        self, api_client: APIClient, user_actions: UserActions, settings: Settings
    ) -> None:
        resp = user_actions.get_user(TARGET_USER_ID)
        resp.assert_response_time(settings.sla_read_ms)
        allure.attach(
            f"Elapsed: {resp.elapsed_ms:.1f}ms  Budget: {settings.sla_read_ms}ms",
            "Performance",
            allure.attachment_type.TEXT,
        )

    @allure.story("Negative — 404 for missing user")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-005 | GET /users/9999 returns 404")
    @pytest.mark.negative
    @pytest.mark.smoke
    def test_not_found_404(self, user_actions: UserActions) -> None:
        user_actions.get_user(MISSING_USER_ID).assert_status(404)


# ════════════════════════════════════════════════════════════════════════════
# POST /api/users
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("POST /api/users")
class TestCreateUser:

    @allure.story("Positive — 201 with echoed payload and generated ID")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TC-006 | POST /users creates user and returns 201")
    @pytest.mark.smoke
    @pytest.mark.positive
    def test_create_returns_201(self, user_actions: UserActions) -> None:
        payload = UserFactory.create(name="Eve", job="QA Engineer")
        resp = user_actions.create_user_from_payload(payload)
        body = resp.assert_status(201).json()

        with allure.step("Echoed name and job"):
            assert body.get("name") == payload["name"]
            assert body.get("job")  == payload["job"]

        with allure.step("Response contains id and createdAt"):
            assert "id"        in body
            assert "createdAt" in body

        resp.attach_to_allure("Created User")

    @allure.story("Positive — Factory-generated random payload")
    @allure.title("TC-007 | POST /users with factory data returns 201")
    @pytest.mark.positive
    @pytest.mark.regression
    def test_create_factory_payload(self, user_actions: UserActions) -> None:
        payload = UserFactory.create()
        resp = user_actions.create_user_from_payload(payload)
        resp.assert_status(201)
        validate_schema(resp.json(), CREATE_USER_RESPONSE_SCHEMA, "CreateUserResponse")

    @allure.story("Contract — Create response matches schema")
    @allure.title("TC-007b | Create user response schema")
    @pytest.mark.schema
    def test_create_schema(self, user_actions: UserActions) -> None:
        resp = user_actions.create_user("Schema Test", "Tester")
        resp.assert_status(201)
        validate_schema(resp.json(), CREATE_USER_RESPONSE_SCHEMA, "CreateUserResponse")

    @allure.story("Negative — Boundary / invalid payloads")
    @allure.title("TC-013 | POST /users with invalid payloads handled gracefully")
    @pytest.mark.negative
    @pytest.mark.parametrize("label,payload", [
        ("missing_name",  UserFactory.missing_name()),
        ("missing_job",   UserFactory.missing_job()),
        ("empty_strings", UserFactory.empty_strings()),
        ("unicode",       UserFactory.unicode_fields()),
        ("xss_attempt",   UserFactory.special_characters()),
    ])
    def test_invalid_payloads(
        self, user_actions: UserActions, label: str, payload: dict
    ) -> None:
        allure.dynamic.title(f"TC-013 | Invalid payload: {label}")
        resp = user_actions.create_user_from_payload(payload)
        # reqres.in accepts most inputs; in production assert 400 or 422
        resp.assert_status_in(201, 400, 422)
        logger.info("Boundary test '%s': status=%d", label, resp.status_code)


# ════════════════════════════════════════════════════════════════════════════
# PUT + PATCH /api/users/{id}
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("PUT + PATCH /api/users/{id}")
class TestUpdateUser:

    @allure.story("Positive — PUT full replace")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-008 | PUT /users/2 returns 200 + updatedAt")
    @pytest.mark.positive
    @pytest.mark.regression
    def test_put_update(self, user_actions: UserActions) -> None:
        payload = UserFactory.update(name="Janet Weaver", job="Principal Engineer")
        resp = user_actions.update_user(TARGET_USER_ID, payload["name"], payload["job"])
        body = resp.assert_status(200).json()
        assert "updatedAt" in body
        validate_schema(body, UPDATE_USER_RESPONSE_SCHEMA, "UpdateUserResponse")

    @allure.story("Positive — PATCH partial update")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-009 | PATCH /users/2 updates only supplied fields")
    @pytest.mark.positive
    def test_patch_update(self, user_actions: UserActions) -> None:
        resp = user_actions.patch_user(TARGET_USER_ID, job="Staff Engineer")
        body = resp.assert_status(200).json()
        assert "updatedAt" in body
        assert body.get("job") == "Staff Engineer"


# ════════════════════════════════════════════════════════════════════════════
# DELETE /api/users/{id}
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("DELETE /api/users/{id}")
class TestDeleteUser:

    @allure.story("Positive — 204 No Content")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TC-010 | DELETE /users/2 returns 204")
    @pytest.mark.smoke
    @pytest.mark.positive
    def test_delete_204(self, user_actions: UserActions) -> None:
        resp = user_actions.delete_user(TARGET_USER_ID)
        resp.assert_status(204)
        assert len(resp.content) == 0, "Body must be empty on 204"


# ════════════════════════════════════════════════════════════════════════════
# GET /api/users (list)
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("GET /api/users (list)")
class TestListUsers:

    @allure.story("Positive — Pagination page 2")
    @allure.title("TC-011 | GET /users?page=2 returns expected structure")
    @pytest.mark.positive
    @pytest.mark.regression
    def test_list_page_2(self, user_actions: UserActions) -> None:
        resp = user_actions.list_users(page=2)
        body = resp.assert_status(200).json()
        assert body.get("page") == 2
        assert isinstance(body.get("data"), list)
        assert len(body["data"]) > 0

    @allure.story("Contract — List schema")
    @allure.title("TC-012 | GET /users list matches schema contract")
    @pytest.mark.schema
    def test_list_schema(self, user_actions: UserActions) -> None:
        resp = user_actions.list_users()
        resp.assert_status(200)
        validate_schema(resp.json(), USER_LIST_RESPONSE_SCHEMA, "UserListResponse")

    @allure.story("Positive — Each user in list has required fields")
    @allure.title("TC-012b | Every user in list has id, email, first_name, last_name, avatar")
    @pytest.mark.positive
    def test_list_user_fields(self, user_actions: UserActions) -> None:
        resp = user_actions.list_users(page=1)
        users = resp.assert_status(200).json()["data"]
        for u in users:
            for field in ("id", "email", "first_name", "last_name", "avatar"):
                assert field in u, f"User missing field '{field}': {u}"


# ════════════════════════════════════════════════════════════════════════════
# Thread-safety / concurrency
# ════════════════════════════════════════════════════════════════════════════
@allure.epic("User Management API")
@allure.feature("Concurrency")
class TestConcurrency:

    @allure.story("Thread-safety — Shared client under concurrent load")
    @allure.title("TC-014 | 10 concurrent GET /users/2 requests all succeed")
    @pytest.mark.performance
    def test_concurrent_get(self, api_client: APIClient) -> None:
        from actions.user_actions import UserActions
        actions = UserActions(api_client)
        errors: list = []
        results: list = []

        def worker() -> None:
            try:
                resp = actions.get_user(TARGET_USER_ID)
                results.append(resp.status_code)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent errors: {errors}"
        assert all(s == 200 for s in results), f"Non-200 responses: {results}"
        allure.attach(
            f"10 concurrent requests: {results}",
            "Concurrency Results",
            allure.attachment_type.TEXT,
        )
