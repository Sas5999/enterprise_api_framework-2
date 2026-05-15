"""
api/endpoints.py
================
Single source of truth for every API endpoint.

Pattern  : frozen dataclass group per resource → top-level Endpoints registry
Benefit  : zero hard-coded strings in tests; IDE auto-complete; refactor-safe
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class _UserEndpoints:
    list_users:   str = "/api/users"
    single_user:  str = "/api/users/{user_id}"
    create_user:  str = "/api/users"
    update_user:  str = "/api/users/{user_id}"
    delete_user:  str = "/api/users/{user_id}"

    def single(self, user_id: int) -> str:     return self.single_user.format(user_id=user_id)
    def update(self, user_id: int) -> str:     return self.update_user.format(user_id=user_id)
    def delete(self, user_id: int) -> str:     return self.delete_user.format(user_id=user_id)


@dataclass(frozen=True)
class _AuthEndpoints:
    register: str = "/api/register"
    login:    str = "/api/login"
    logout:   str = "/api/logout"
    refresh:  str = "/api/refresh"


@dataclass(frozen=True)
class _ResourceEndpoints:
    """Generic resource endpoint group — reuse per new resource."""
    base: str

    def list(self) -> str:              return self.base
    def create(self) -> str:            return self.base
    def single(self, _id: int) -> str:  return f"{self.base}/{_id}"
    def update(self, _id: int) -> str:  return f"{self.base}/{_id}"
    def delete(self, _id: int) -> str:  return f"{self.base}/{_id}"


@dataclass(frozen=True)
class Endpoints:
    """
    Top-level endpoint registry.

    Usage::

        from api.endpoints import endpoints
        url = endpoints.users.single(user_id=5)
    """
    users:    _UserEndpoints   = field(default_factory=_UserEndpoints)
    auth:     _AuthEndpoints   = field(default_factory=_AuthEndpoints)
    # Add more resource groups here as the API grows:
    # products: _ResourceEndpoints = field(default_factory=lambda: _ResourceEndpoints("/api/products"))


endpoints = Endpoints()
