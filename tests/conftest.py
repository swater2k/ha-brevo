"""Fixtures mit Beispielantworten der Brevo-API v3."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.brevo.const import DOMAIN

API = "https://api.brevo.com/v3"
API_KEY = "xkeysib-testkey-0000"

ACCOUNT = {
    "organization_id": "5fa2b8c123456789abcdef01",
    "user_id": 1234567,
    "enterprise": False,
    "companyName": "robben.tech",
    "email": "user@example.com",
    "plan": [
        {"credits": 273, "creditsType": "sendLimit", "type": "free"},
        {"credits": 15, "creditsType": "sendLimit", "type": "sms"},
    ],
    "relay": {
        "data": {"port": 587, "relay": "smtp-relay.brevo.com", "userName": "user@example.com"},
        "enabled": True,
    },
}

REPORT_24H = {
    "range": "2026-09-16|2026-09-17",
    "requests": 12,
    "delivered": 10,
    "hardBounces": 1,
    "softBounces": 0,
    "blocked": 1,
    "spamReports": 0,
    "invalid": 0,
    "unsubscribed": 0,
    "opens": 4,
    "clicks": 1,
}

REPORT_7D = {**REPORT_24H, "requests": 64, "delivered": 61, "hardBounces": 2, "blocked": 1}

EVENTS = {
    "events": [
        {
            "email": "bounce@example.com",
            "date": "2026-09-17T21:14:02.000+02:00",
            "subject": "Authelia – Passwort zurücksetzen",
            "messageId": "<202609172114.1@smtp-relay.brevo.com>",
            "event": "hardBounces",
            "reason": "unknown user",
            "tag": "authelia",
        },
        {
            "email": "ok@example.com",
            "date": "2026-09-17T20:02:00.000+02:00",
            "subject": "Test",
            "messageId": "<202609172002.2@smtp-relay.brevo.com>",
            "event": "delivered",
        },
    ]
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_brevo(aioclient_mock):
    aioclient_mock.get(f"{API}/account", json=ACCOUNT)
    aioclient_mock.get(f"{API}/smtp/statistics/aggregatedReport", json=REPORT_24H)
    aioclient_mock.get(f"{API}/smtp/statistics/events", json=EVENTS)
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Brevo (robben.tech)",
        data={"api_key": API_KEY},
        unique_id=ACCOUNT["organization_id"],
        options={"scan_interval": 15, "credits_threshold": 50},
    )
