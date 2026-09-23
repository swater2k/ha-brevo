"""Binary-Sensoren."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BrevoConfigEntry
from .coordinator import BrevoCoordinator
from .entity import BrevoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrevoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            BrevoApiReachable(coordinator, entry),
            BrevoDeliveryProblem(coordinator, entry),
            BrevoRelayEnabled(coordinator, entry),
        ]
    )


class BrevoApiReachable(BrevoEntity, BinarySensorEntity):
    """Ob die Brevo-API antwortet."""

    _attr_translation_key = "api_reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BrevoCoordinator, entry: BrevoConfigEntry) -> None:
        super().__init__(coordinator, entry, "api_reachable")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success


class BrevoDeliveryProblem(BrevoEntity, BinarySensorEntity):
    """An, wenn in 24 h Mails hart abgewiesen oder blockiert wurden."""

    _attr_translation_key = "delivery_problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: BrevoCoordinator, entry: BrevoConfigEntry) -> None:
        super().__init__(coordinator, entry, "delivery_problem")

    @property
    def is_on(self) -> bool:
        values = self.coordinator.data.values
        return bool((values.get("hard_bounces_24h") or 0) or (values.get("blocked_24h") or 0))


class BrevoRelayEnabled(BrevoEntity, BinarySensorEntity):
    """Ob der SMTP-Relay des Kontos aktiv ist."""

    _attr_translation_key = "relay_enabled"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BrevoCoordinator, entry: BrevoConfigEntry) -> None:
        super().__init__(coordinator, entry, "relay_enabled")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.values.get("relay_enabled")
