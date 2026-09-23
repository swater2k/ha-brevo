"""Sensoren."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BrevoConfigEntry
from .coordinator import BrevoCoordinator, BrevoData
from .entity import BrevoEntity

PARALLEL_UPDATES = 0

MEAS = SensorStateClass.MEASUREMENT
DIAG = EntityCategory.DIAGNOSTIC


@dataclass(frozen=True, kw_only=True)
class BrevoSensorDescription(SensorEntityDescription):
    attrs_fn: Callable[[BrevoData], dict[str, Any] | None] | None = None


def _d(key: str, **kw: Any) -> BrevoSensorDescription:
    kw.setdefault("translation_key", key)
    return BrevoSensorDescription(key=key, **kw)


_PERCENT: dict[str, Any] = {
    "native_unit_of_measurement": PERCENTAGE,
    "state_class": MEAS,
    "suggested_display_precision": 1,
}

SENSORS: tuple[BrevoSensorDescription, ...] = (
    # Kontingent
    _d("email_credits", state_class=MEAS, icon="mdi:email-check",
       attrs_fn=lambda d: {"plan": d.values.get("plan_type")}),
    _d("sms_credits", state_class=MEAS, icon="mdi:message-text",
       entity_registry_enabled_default=False),
    # Zustellung, 24 h
    _d("requests_24h", state_class=MEAS, icon="mdi:email-arrow-right"),
    _d("delivered_24h", state_class=MEAS, icon="mdi:email-check",
       entity_registry_enabled_default=False),
    _d("delivery_rate_24h", icon="mdi:chart-donut", **_PERCENT),
    _d("problems_24h", state_class=MEAS, icon="mdi:email-alert"),
    _d("hard_bounces_24h", state_class=MEAS, icon="mdi:email-remove"),
    _d("soft_bounces_24h", state_class=MEAS, icon="mdi:email-sync-outline",
       entity_registry_enabled_default=False),
    _d("blocked_24h", state_class=MEAS, icon="mdi:email-off"),
    _d("spam_reports_24h", state_class=MEAS, icon="mdi:alert-octagon"),
    _d("invalid_24h", state_class=MEAS, icon="mdi:email-remove-outline",
       entity_registry_enabled_default=False),
    _d("unsubscribed_24h", state_class=MEAS, icon="mdi:email-minus",
       entity_registry_enabled_default=False),
    _d("opens_24h", state_class=MEAS, icon="mdi:email-open",
       entity_registry_enabled_default=False),
    _d("clicks_24h", state_class=MEAS, icon="mdi:cursor-default-click",
       entity_registry_enabled_default=False),
    # Zustellung, 7 Tage
    _d("requests_7d", state_class=MEAS, icon="mdi:email-arrow-right"),
    _d("problems_7d", state_class=MEAS, icon="mdi:email-alert",
       entity_registry_enabled_default=False),
    _d("delivery_rate_7d", icon="mdi:chart-donut", entity_registry_enabled_default=False,
       **_PERCENT),
    # Letztes Problem
    _d("last_problem", device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:email-alert",
       attrs_fn=lambda d: d.values.get("last_problem_details")),
    # Diagnose
    _d("plan_type", entity_category=DIAG, icon="mdi:card-account-details-outline"),
    _d("relay_host", entity_category=DIAG, icon="mdi:server-network",
       entity_registry_enabled_default=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrevoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data.coordinator
    async_add_entities(BrevoSensor(coordinator, entry, desc) for desc in SENSORS)


class BrevoSensor(BrevoEntity, SensorEntity):
    entity_description: BrevoSensorDescription

    def __init__(
        self,
        coordinator: BrevoCoordinator,
        entry: BrevoConfigEntry,
        description: BrevoSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.coordinator.data.values.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
