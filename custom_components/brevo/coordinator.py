"""Coordinator: pollt Brevo und leitet neue Zustellprobleme als Ereignisse ab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BrevoAuthError, BrevoClient, BrevoError, BrevoSnapshot, EmailEvent
from .const import DOMAIN, PROBLEM_EVENT_MAP

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BrevoData:
    snapshot: BrevoSnapshot
    values: dict[str, Any]
    new_problems: list[EmailEvent]
    fetched_at: datetime


class BrevoCoordinator(DataUpdateCoordinator[BrevoData]):
    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: BrevoClient, interval_minutes: int
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.client = client
        self._seen: set[str] | None = None

    async def _async_update_data(self) -> BrevoData:
        try:
            snapshot = await self.client.snapshot()
        except BrevoAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BrevoError as err:
            raise UpdateFailed(str(err)) from err
        return self._process(snapshot)

    def _process(self, snapshot: BrevoSnapshot) -> BrevoData:
        account = snapshot.account
        day, week = snapshot.report_24h, snapshot.report_7d

        values: dict[str, Any] = {
            "email_credits": account.email_credits,
            "sms_credits": account.sms_credits,
            "plan_type": account.plan_type,
            "company": account.company,
            "relay_enabled": account.relay_enabled,
            "relay_host": account.relay_host,
            "requests_24h": day.requests,
            "delivered_24h": day.delivered,
            "hard_bounces_24h": day.hard_bounces,
            "soft_bounces_24h": day.soft_bounces,
            "blocked_24h": day.blocked,
            "spam_reports_24h": day.spam_reports,
            "invalid_24h": day.invalid,
            "unsubscribed_24h": day.unsubscribed,
            "opens_24h": day.opens,
            "clicks_24h": day.clicks,
            "problems_24h": day.problems,
            "delivery_rate_24h": day.delivery_rate,
            "requests_7d": week.requests,
            "problems_7d": week.problems,
            "delivery_rate_7d": week.delivery_rate,
        }

        problems = [e for e in snapshot.events if e.event in PROBLEM_EVENT_MAP]
        latest = problems[0] if problems else None
        values["last_problem"] = _parse(latest.date) if latest else None
        values["last_problem_details"] = (
            {
                "event": PROBLEM_EVENT_MAP[latest.event],
                "email": latest.email,
                "subject": latest.subject,
                "reason": latest.reason,
            }
            if latest
            else None
        )

        # Nur Ereignisse melden, die seit dem letzten Abruf dazugekommen sind.
        new_problems: list[EmailEvent] = []
        keys = {event.key for event in problems}
        if self._seen is not None:
            new_problems = [event for event in reversed(problems) if event.key not in self._seen]
        self._seen = keys

        return BrevoData(
            snapshot=snapshot,
            values=values,
            new_problems=new_problems,
            fetched_at=datetime.now(UTC),
        )


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
