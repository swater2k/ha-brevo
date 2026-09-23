"""Konstanten der Brevo-Integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "brevo"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CREDITS_THRESHOLD: Final = "credits_threshold"

DEFAULT_SCAN_INTERVAL: Final = 15  # Minuten
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 120
DEFAULT_CREDITS_THRESHOLD: Final = 50

API_BASE: Final = "https://api.brevo.com/v3"
REQUEST_TIMEOUT: Final = 20
EVENT_LIMIT: Final = 100

# Ereignisse, die eine Zustellung verhindert oder gefährdet haben
PROBLEM_EVENTS: Final = (
    "hardBounces",
    "softBounces",
    "blocked",
    "spam",
    "invalid",
    "deferred",
    "error",
)
