"""
utils/logger.py
===============
Enterprise-grade logging configuration.

Features
--------
- Rich colourised console (degrades gracefully)
- JSON-structured output mode (for log aggregation: ELK / Splunk / Datadog)
- Rotating file handler (10 MB × 5 backups)
- Single setup call from conftest; get_logger() everywhere else
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

try:
    from rich.logging import RichHandler
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_FRAMEWORK_LOGGER = "api_framework"
_configured = False


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line for structured log pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":     record.levelname,
            "logger":    record.name,
            "line":      record.lineno,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    log_level: str       = "DEBUG",
    log_to_file: bool    = True,
    log_file_path: Optional[Path] = None,
    log_json: bool       = False,
) -> None:
    """
    Initialise all logging handlers.  Safe to call multiple times (idempotent).
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger(_FRAMEWORK_LOGGER)
    root.setLevel(getattr(logging, log_level, logging.DEBUG))
    root.handlers.clear()

    # ── Console ───────────────────────────────────────────────────────────────
    if log_json:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(_JSONFormatter())
    elif _RICH_AVAILABLE:
        console_handler = RichHandler(
            level=log_level,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        console_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    root.addHandler(console_handler)

    # ── File ──────────────────────────────────────────────────────────────────
    if log_to_file and log_file_path:
        log_file_path = Path(log_file_path)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = _JSONFormatter() if log_json else logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
        root.info("File logging → %s", log_file_path)

    root.info(
        "Logging ready | level=%s | json=%s | file=%s | rich=%s",
        log_level, log_json, log_to_file, _RICH_AVAILABLE,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the framework namespace."""
    return logging.getLogger(f"{_FRAMEWORK_LOGGER}.{name}")


# Alias for backwards compatibility
setup_logger = get_logger
