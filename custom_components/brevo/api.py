"""Async-Client für die Brevo-API v3.

Genutzt werden ausschließlich lesende Endpunkte:

* ``GET /v3/account`` – Plan und verbleibende Credits
* ``GET /v3/smtp/statistics/aggregatedReport`` – Kennzahlen über einen Zeitraum
* ``GET /v3/smtp/statistics/events`` – einzelne Ereignisse (Bounces, Blocks, ...)

Der API-Schlüssel wird im Header ``api-key`` übertragen.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
from typing import Any

import aiohttp

from .const import API_BASE, EVENT_LIMIT, REQUEST_TIMEOUT


class BrevoError(Exception):
    """Basisfehler."""


class BrevoConnectionError(BrevoError):
    """Brevo nicht erreichbar oder Zeitüberschreitung."""


class BrevoAuthError(BrevoError):
    """API-Schlüssel fehlt, ist ungültig oder hat zu wenig Rechte."""


class BrevoIpNotAuthorizedError(BrevoError):
    """Brevo blockiert die öffentliche IP (Sicherheitsfunktion "Authorized IPs").

    Der Schlüssel ist gültig – ein neuer Schlüssel hilft deshalb nicht.
    Tritt typischerweise auf, wenn sich die öffentliche IP des Anschlusses
    ändert, etwa nach einer Zwangstrennung oder einem Router-Neustart.
    """


class BrevoRateLimitError(BrevoError):
    """Zu viele Anfragen (HTTP 429)."""


@dataclass(frozen=True, slots=True)
class Account:
    """Ausgewertete Antwort von ``/account``."""

    organization_id: str | None
    company: str | None
    email_credits: float | None
    sms_credits: float | None
    plan_type: str | None
    plan_end: str | None
    relay_enabled: bool | None
    relay_host: str | None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Account:
        plans = data.get("plan") or []
        email_plan = next(
            (p for p in plans if p.get("type") != "sms" and p.get("credits") is not None), None
        )
        sms_plan = next((p for p in plans if p.get("type") == "sms"), None)
        relay = data.get("relay") or {}
        return cls(
            organization_id=data.get("organization_id"),
            company=data.get("companyName"),
            email_credits=_float(email_plan.get("credits")) if email_plan else None,
            sms_credits=_float(sms_plan.get("credits")) if sms_plan else None,
            plan_type=email_plan.get("type") if email_plan else None,
            plan_end=email_plan.get("endDate") if email_plan else None,
            relay_enabled=relay.get("enabled"),
            relay_host=(relay.get("data") or {}).get("relay"),
        )


@dataclass(frozen=True, slots=True)
class Report:
    """Aggregierte Kennzahlen eines Zeitraums."""

    requests: float = 0.0
    delivered: float = 0.0
    hard_bounces: float = 0.0
    soft_bounces: float = 0.0
    blocked: float = 0.0
    spam_reports: float = 0.0
    invalid: float = 0.0
    unsubscribed: float = 0.0
    opens: float = 0.0
    clicks: float = 0.0
    range: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Report:
        return cls(
            requests=_float(data.get("requests")) or 0.0,
            delivered=_float(data.get("delivered")) or 0.0,
            hard_bounces=_float(data.get("hardBounces")) or 0.0,
            soft_bounces=_float(data.get("softBounces")) or 0.0,
            blocked=_float(data.get("blocked")) or 0.0,
            spam_reports=_float(data.get("spamReports")) or 0.0,
            invalid=_float(data.get("invalid")) or 0.0,
            unsubscribed=_float(data.get("unsubscribed")) or 0.0,
            opens=_float(data.get("opens")) or 0.0,
            clicks=_float(data.get("clicks")) or 0.0,
            range=data.get("range"),
        )

    @property
    def problems(self) -> float:
        """Alles, was eine Zustellung verhindert hat."""
        return self.hard_bounces + self.soft_bounces + self.blocked + self.invalid

    @property
    def delivery_rate(self) -> float | None:
        if self.requests <= 0:
            return None
        return round(self.delivered / self.requests * 100, 1)


@dataclass(frozen=True, slots=True)
class EmailEvent:
    """Einzelnes Ereignis aus ``/smtp/statistics/events``."""

    event: str
    email: str | None
    date: str | None
    subject: str | None
    reason: str | None
    message_id: str | None
    tag: str | None

    @property
    def key(self) -> str:
        return f"{self.message_id or ''}|{self.event}|{self.date or ''}"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> EmailEvent:
        return cls(
            event=str(data.get("event") or "unknown"),
            email=data.get("email"),
            date=data.get("date"),
            subject=data.get("subject"),
            reason=data.get("reason"),
            message_id=data.get("messageId"),
            tag=data.get("tag"),
        )


@dataclass(slots=True)
class BrevoSnapshot:
    """Ein vollständiger Abruf."""

    account: Account
    report_24h: Report
    report_7d: Report
    events: list[EmailEvent] = field(default_factory=list)


_IP_BLOCK_MARKERS = (
    "ip address",
    "ip not authorized",
    "not verified",
    "unrecognised ip",
    "unrecognized ip",
)


def _is_ip_block(message: str) -> bool:
    text = message.lower()
    return any(marker in text for marker in _IP_BLOCK_MARKERS)


async def _error_message(resp: aiohttp.ClientResponse) -> str:
    """Fehlertext von Brevo auslesen (JSON ``message`` oder Rohtext)."""
    try:
        body = await resp.text()
    except aiohttp.ClientError:
        return ""
    try:
        data = json.loads(body)
    except ValueError:
        return body.strip()[:300]
    if isinstance(data, dict):
        return str(data.get("message") or data.get("code") or "").strip()
    return ""


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BrevoClient:
    """Dünner Wrapper um die lesenden Endpunkte."""

    def __init__(
        self, session: aiohttp.ClientSession, api_key: str, timeout: float = REQUEST_TIMEOUT
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"api-key": self._api_key, "Accept": "application/json"}
        try:
            async with self._session.get(
                f"{API_BASE}{path}", params=params, headers=headers, timeout=self._timeout
            ) as resp:
                if resp.status in (401, 403):
                    message = await _error_message(resp)
                    if _is_ip_block(message):
                        raise BrevoIpNotAuthorizedError(message)
                    raise BrevoAuthError(message or "API-Schlüssel ungültig oder ohne Berechtigung")
                if resp.status == 429:
                    raise BrevoRateLimitError("Brevo-Ratelimit erreicht")
                if resp.status >= 400:
                    raise BrevoError(f"Brevo antwortet mit HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except BrevoError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise BrevoConnectionError(f"Brevo nicht erreichbar: {err}") from err
        except ValueError as err:
            raise BrevoError("Brevo liefert kein JSON") from err
        if not isinstance(data, dict):
            raise BrevoError("Unerwartetes Antwortformat")
        return data

    async def account(self) -> Account:
        return Account.from_json(await self._get("/account"))

    async def report(self, days: int) -> Report:
        return Report.from_json(
            await self._get("/smtp/statistics/aggregatedReport", {"days": days})
        )

    async def events(self, days: int = 1, limit: int = EVENT_LIMIT) -> list[EmailEvent]:
        data = await self._get(
            "/smtp/statistics/events", {"days": days, "limit": limit, "sort": "desc"}
        )
        return [EmailEvent.from_json(item) for item in data.get("events") or []]

    async def snapshot(self) -> BrevoSnapshot:
        """Alle Daten eines Abrufs; Ereignisse sind optional."""
        account, report_24h, report_7d = await asyncio.gather(
            self.account(), self.report(1), self.report(7)
        )
        try:
            events = await self.events()
        except BrevoError:
            events = []
        return BrevoSnapshot(account, report_24h, report_7d, events)
