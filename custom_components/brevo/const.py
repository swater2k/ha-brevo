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

# Ereignisse, die eine Zustellung verhindert oder gefährdet haben.
# Brevo liefert CamelCase; Home Assistant erlaubt als Übersetzungsschlüssel
# nur Kleinbuchstaben, deshalb die Zuordnung auf eigene Typen.
PROBLEM_EVENT_MAP: Final = {
    "hardBounces": "hard_bounce",
    "hardBounce": "hard_bounce",
    "softBounces": "soft_bounce",
    "softBounce": "soft_bounce",
    "blocked": "blocked",
    "spam": "spam",
    "invalid": "invalid",
    "deferred": "deferred",
    "error": "error",
}
EVENT_TYPES: Final = (
    "hard_bounce",
    "soft_bounce",
    "blocked",
    "spam",
    "invalid",
    "deferred",
    "error",
)
