"""Event-Entity für neue Zustellprobleme."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BrevoConfigEntry
from .const import EVENT_TYPES, PROBLEM_EVENT_MAP
from .coordinator import BrevoCoordinator
from .entity import BrevoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrevoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([BrevoDeliveryEvent(entry.runtime_data.coordinator, entry)])


class BrevoDeliveryEvent(BrevoEntity, EventEntity):
    """Feuert pro neuem Bounce, Block oder Spam-Report.

    Die Ereignisse stammen aus ``/smtp/statistics/events`` und tragen
    Empfänger, Betreff und den Grund der Ablehnung.
    """

    _attr_translation_key = "delivery"

    def __init__(self, coordinator: BrevoCoordinator, entry: BrevoConfigEntry) -> None:
        super().__init__(coordinator, entry, "delivery_event")
        self._attr_event_types = list(EVENT_TYPES)

    @property
    def available(self) -> bool:
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None:
            for event in self.coordinator.data.new_problems:
                self._trigger_event(
                    PROBLEM_EVENT_MAP.get(event.event, "error"),
                    {
                        "email": event.email,
                        "subject": event.subject,
                        "reason": event.reason,
                        "date": event.date,
                        "tag": event.tag,
                    },
                )
                self.async_write_ha_state()
        super()._handle_coordinator_update()
