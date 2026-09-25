"""Brevo-Integration für Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BrevoClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .coordinator import BrevoCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]


@dataclass(slots=True)
class BrevoRuntimeData:
    coordinator: BrevoCoordinator


type BrevoConfigEntry = ConfigEntry[BrevoRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: BrevoConfigEntry) -> bool:
    client = BrevoClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    coordinator = BrevoCoordinator(
        hass, entry, client, entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    from .issues import async_update_issues

    try:
        await coordinator.async_config_entry_first_refresh()
    finally:
        # Auch bei ConfigEntryNotReady: den IP-Hinweis sofort zeigen, statt
        # still in setup_retry zu hängen.
        async_update_issues(hass, entry, coordinator)

    entry.runtime_data = BrevoRuntimeData(coordinator)

    @callback
    def _update_issues() -> None:
        async_update_issues(hass, entry, coordinator)

    entry.async_on_unload(coordinator.async_add_listener(_update_issues))
    _update_issues()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BrevoConfigEntry) -> bool:
    from .issues import async_remove_issues

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        async_remove_issues(hass, entry)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: BrevoConfigEntry) -> None:
    """Hinweise auch dann entfernen, wenn der Eintrag nie geladen war."""
    from .issues import async_remove_issues

    async_remove_issues(hass, entry)
