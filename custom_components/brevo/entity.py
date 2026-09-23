"""Basis-Entity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BrevoConfigEntry
from .const import DOMAIN
from .coordinator import BrevoCoordinator


class BrevoEntity(CoordinatorEntity[BrevoCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: BrevoCoordinator, entry: BrevoConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        company = None
        if coordinator.data is not None:
            company = coordinator.data.values.get("company")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Brevo",
            manufacturer="Brevo",
            model=company or "Transactional email",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.brevo.com/",
        )
