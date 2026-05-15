"""
schemas/user_schemas.py
=======================
JSON Schema contracts for the User resource.

These schemas act as living API contracts.  If the upstream API changes its
response shape without notice, the contract tests will fail immediately —
before any downstream consumer is affected.

Validation is done with the `jsonschema` library (already in requirements).
"""

from __future__ import annotations

from typing import Any, Dict

import jsonschema


# ── Schema definitions ────────────────────────────────────────────────────────

SINGLE_USER_RESPONSE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title":   "SingleUserResponse",
    "type":    "object",
    "required": ["data", "support"],
    "additionalProperties": True,
    "properties": {
        "data": {
            "type": "object",
            "required": ["id", "email", "first_name", "last_name", "avatar"],
            "properties": {
                "id":         {"type": "integer", "minimum": 1},
                "email":      {"type": "string",  "format": "email"},
                "first_name": {"type": "string",  "minLength": 1},
                "last_name":  {"type": "string",  "minLength": 1},
                "avatar":     {"type": "string",  "format": "uri"},
            },
            "additionalProperties": True,
        },
        "support": {
            "type": "object",
            "required": ["url", "text"],
            "properties": {
                "url":  {"type": "string"},
                "text": {"type": "string"},
            },
        },
    },
}

USER_LIST_RESPONSE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title":   "UserListResponse",
    "type":    "object",
    "required": ["page", "per_page", "total", "total_pages", "data"],
    "properties": {
        "page":        {"type": "integer", "minimum": 1},
        "per_page":    {"type": "integer", "minimum": 1},
        "total":       {"type": "integer", "minimum": 0},
        "total_pages": {"type": "integer", "minimum": 0},
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "email", "first_name", "last_name", "avatar"],
            },
        },
    },
}

CREATE_USER_RESPONSE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title":   "CreateUserResponse",
    "type":    "object",
    "required": ["id", "createdAt"],
    "properties": {
        "name":      {"type": "string"},
        "job":       {"type": "string"},
        "id":        {"type": "string"},
        "createdAt": {"type": "string", "format": "date-time"},
    },
}

UPDATE_USER_RESPONSE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title":   "UpdateUserResponse",
    "type":    "object",
    "required": ["updatedAt"],
    "properties": {
        "name":      {"type": "string"},
        "job":       {"type": "string"},
        "updatedAt": {"type": "string", "format": "date-time"},
    },
}

LOGIN_RESPONSE_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title":   "LoginResponse",
    "type":    "object",
    "required": ["token"],
    "properties": {
        "token": {"type": "string", "minLength": 1},
    },
}


# ── Validator helper ─────────────────────────────────────────────────────────

def validate_schema(data: Any, schema: Dict[str, Any], label: str = "response") -> None:
    """
    Validate `data` against `schema`.  Raises AssertionError with a human-readable
    message on failure so pytest shows it cleanly.

    Parameters
    ----------
    data   : Parsed JSON body (dict / list).
    schema : JSON Schema dict.
    label  : Friendly name used in the error message.
    """
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise AssertionError(
            f"Schema validation failed for '{label}':\n"
            f"  Path   : {list(exc.absolute_path)}\n"
            f"  Error  : {exc.message}\n"
            f"  Schema : {exc.schema}\n"
        ) from exc
