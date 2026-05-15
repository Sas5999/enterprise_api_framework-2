"""
data/factories/user_factory.py
==============================
Test-data factory for the User resource.

Why factories?
--------------
Hard-coded test data creates brittle tests and collision issues in parallel runs.
Factories generate realistic, unique data on demand using Faker.

Usage::

    from data.factories.user_factory import UserFactory

    # Random valid user
    payload = UserFactory.create()

    # Explicit overrides
    payload = UserFactory.create(name="Alice", job="CTO")

    # Invalid / boundary payloads for negative tests
    payload = UserFactory.missing_name()
    payload = UserFactory.empty_strings()
    payload = UserFactory.max_length_strings()
"""

from __future__ import annotations

import random
import string
from typing import Any, Dict, Optional

try:
    from faker import Faker
    _faker = Faker()
    _FAKER_AVAILABLE = True
except ImportError:
    _FAKER_AVAILABLE = False


class UserFactory:
    """Generates User payloads for positive and negative tests."""

    _JOBS = [
        "Software Engineer", "QA Engineer", "Product Manager", "DevOps Engineer",
        "Data Scientist", "UX Designer", "Backend Developer", "Frontend Developer",
        "Tech Lead", "Principal Engineer", "CTO", "Engineering Manager",
    ]

    # ── Valid payloads ────────────────────────────────────────────────────────
    @classmethod
    def create(
        cls,
        name: Optional[str] = None,
        job: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a valid create-user payload."""
        return {
            "name": name or (
                _faker.name() if _FAKER_AVAILABLE else f"User_{_rand_str(6)}"
            ),
            "job": job or (
                _faker.job() if _FAKER_AVAILABLE else random.choice(cls._JOBS)
            ),
        }

    @classmethod
    def update(
        cls,
        name: Optional[str] = None,
        job: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a valid update-user payload."""
        return cls.create(name=name, job=job)

    @classmethod
    def patch(cls, **overrides: Any) -> Dict[str, Any]:
        """Return a partial update payload (only the supplied fields)."""
        base = cls.create()
        base.update(overrides)
        return base

    # ── Invalid / boundary payloads ───────────────────────────────────────────
    @classmethod
    def missing_name(cls) -> Dict[str, Any]:
        return {"job": random.choice(cls._JOBS)}

    @classmethod
    def missing_job(cls) -> Dict[str, Any]:
        return {"name": _faker.name() if _FAKER_AVAILABLE else "Jane Doe"}

    @classmethod
    def empty_strings(cls) -> Dict[str, Any]:
        return {"name": "", "job": ""}

    @classmethod
    def null_fields(cls) -> Dict[str, Any]:
        return {"name": None, "job": None}

    @classmethod
    def max_length_strings(cls, length: int = 10_000) -> Dict[str, Any]:
        return {"name": "A" * length, "job": "B" * length}

    @classmethod
    def special_characters(cls) -> Dict[str, Any]:
        return {"name": "<script>alert(1)</script>", "job": "'; DROP TABLE users; --"}

    @classmethod
    def unicode_fields(cls) -> Dict[str, Any]:
        return {"name": "张伟 عمر Ödön", "job": "エンジニア المطور"}

    @classmethod
    def numeric_name(cls) -> Dict[str, Any]:
        return {"name": 12345, "job": "engineer"}


def _rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))
