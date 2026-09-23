"""Diagnose-Download."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from . import BrevoConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BrevoConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    values = dict(data.values) if data else {}
    # Empfängeradresse des letzten Problems nicht mit ausgeben
    if values.get("last_problem_details"):
        details = dict(values["last_problem_details"])
        details.pop("email", None)
        values["last_problem_details"] = details
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "fetched_at": data.fetched_at.isoformat() if data else None,
        "values": {k: str(v) for k, v in values.items()},
        "event_count": len(data.snapshot.events) if data else None,
    }
