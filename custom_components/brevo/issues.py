"""Repair-Hinweise."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import CONF_CREDITS_THRESHOLD, DEFAULT_CREDITS_THRESHOLD, DOMAIN
from .coordinator import BrevoCoordinator

ISSUE_CREDITS_LOW = "credits_low"
ISSUE_DELIVERY_PROBLEMS = "delivery_problems"
ALL_ISSUES = (ISSUE_CREDITS_LOW, ISSUE_DELIVERY_PROBLEMS)


def _issue_id(entry: ConfigEntry, key: str) -> str:
    return f"{key}_{entry.entry_id}"


def _set(
    hass: HomeAssistant,
    entry: ConfigEntry,
    key: str,
    active: bool,
    severity: ir.IssueSeverity,
    placeholders: dict[str, str],
) -> None:
    issue_id = _issue_id(entry, key)
    if not active:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=False,
        severity=severity,
        translation_key=key,
        translation_placeholders={"title": entry.title, **placeholders},
    )


@callback
def async_update_issues(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: BrevoCoordinator
) -> None:
    data = coordinator.data
    if data is None or not coordinator.last_update_success:
        return

    threshold = entry.options.get(CONF_CREDITS_THRESHOLD, DEFAULT_CREDITS_THRESHOLD)
    credits_left = data.values.get("email_credits")
    _set(
        hass,
        entry,
        ISSUE_CREDITS_LOW,
        credits_left is not None and credits_left < threshold,
        ir.IssueSeverity.WARNING,
        {"credits": str(int(credits_left or 0)), "threshold": str(threshold)},
    )

    problems = data.values.get("problems_24h") or 0
    _set(
        hass,
        entry,
        ISSUE_DELIVERY_PROBLEMS,
        bool(data.values.get("hard_bounces_24h") or data.values.get("blocked_24h")),
        ir.IssueSeverity.WARNING,
        {"problems": str(int(problems))},
    )


@callback
def async_remove_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    for key in ALL_ISSUES:
        ir.async_delete_issue(hass, DOMAIN, _issue_id(entry, key))
