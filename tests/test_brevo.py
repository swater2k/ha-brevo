"""Setup, Entitäten, Ereignisse, Repairs und Flows."""

from __future__ import annotations

import copy

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.brevo.api import Report
from custom_components.brevo.const import DOMAIN

from .conftest import ACCOUNT, API, API_KEY, EVENTS, REPORT_24H


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def test_report_derived_values() -> None:
    report = Report.from_json(REPORT_24H)
    assert report.problems == 2  # hard bounce + blocked
    assert report.delivery_rate == 83.3
    assert Report().delivery_rate is None


async def test_entities(hass: HomeAssistant, mock_brevo, config_entry) -> None:
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    # API-Schlüssel wird als Header gesendet
    assert mock_brevo.mock_calls[0][3]["api-key"] == API_KEY

    credits = hass.states.get("sensor.brevo_e_mail_credits")
    assert credits.state == "273.0" and credits.attributes["plan"] == "free"
    assert hass.states.get("sensor.brevo_e_mails_sent_24_h").state == "12.0"
    assert hass.states.get("sensor.brevo_delivery_rate_24_h").state == "83.3"
    assert hass.states.get("sensor.brevo_delivery_problems_24_h").state == "2.0"
    assert hass.states.get("sensor.brevo_hard_bounces_24_h").state == "1.0"
    assert hass.states.get("sensor.brevo_plan").state == "free"

    problem = hass.states.get("sensor.brevo_last_delivery_problem")
    assert problem.state.startswith("2026-09-17T19:14")  # in UTC umgerechnet
    assert problem.attributes["reason"] == "unknown user"
    assert problem.attributes["email"] == "bounce@example.com"

    assert hass.states.get("binary_sensor.brevo_delivery_problem").state == "on"
    assert hass.states.get("binary_sensor.brevo_api_reachable").state == "on"
    assert hass.states.get("binary_sensor.brevo_smtp_relay_active").state == "on"

    reg = er.async_get(hass)
    assert reg.async_get("sensor.brevo_opens_24_h").disabled_by is not None


async def test_new_problem_fires_event(hass: HomeAssistant, mock_brevo, config_entry) -> None:
    await _setup(hass, config_entry)
    seen: list[dict] = []

    @callback
    def _listener(event) -> None:
        new = event.data["new_state"]
        if new and new.entity_id == "event.brevo_delivery_event" and "event_type" in new.attributes:
            seen.append(dict(new.attributes))

    hass.bus.async_listen("state_changed", _listener)

    events = copy.deepcopy(EVENTS)
    events["events"].insert(
        0,
        {
            "email": "neu@example.com",
            "date": "2026-09-17T22:00:00.000+02:00",
            "subject": "Authelia – Anmeldung",
            "messageId": "<202609172200.3@smtp-relay.brevo.com>",
            "event": "blocked",
            "reason": "blocked contact",
        },
    )
    mock_brevo.clear_requests()
    mock_brevo.get(f"{API}/account", json=ACCOUNT)
    mock_brevo.get(f"{API}/smtp/statistics/aggregatedReport", json=REPORT_24H)
    mock_brevo.get(f"{API}/smtp/statistics/events", json=events)

    await config_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    assert [e["event_type"] for e in seen] == ["blocked"]
    assert seen[0]["email"] == "neu@example.com"
    assert seen[0]["reason"] == "blocked contact"


async def test_repairs(hass: HomeAssistant, mock_brevo, config_entry) -> None:
    await _setup(hass, config_entry)
    issues = ir.async_get(hass)
    eid = config_entry.entry_id

    # Guthaben 273 liegt über der Schwelle 50
    assert issues.async_get_issue(DOMAIN, f"credits_low_{eid}") is None
    problems = issues.async_get_issue(DOMAIN, f"delivery_problems_{eid}")
    assert problems is not None and problems.translation_placeholders["problems"] == "2"

    low = copy.deepcopy(ACCOUNT)
    low["plan"][0]["credits"] = 12
    clean = {**REPORT_24H, "hardBounces": 0, "blocked": 0}
    mock_brevo.clear_requests()
    mock_brevo.get(f"{API}/account", json=low)
    mock_brevo.get(f"{API}/smtp/statistics/aggregatedReport", json=clean)
    mock_brevo.get(f"{API}/smtp/statistics/events", json={"events": []})

    await config_entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()

    credits_issue = issues.async_get_issue(DOMAIN, f"credits_low_{eid}")
    assert credits_issue is not None
    assert credits_issue.translation_placeholders == {
        "title": config_entry.title,
        "credits": "12",
        "threshold": "50",
    }
    assert issues.async_get_issue(DOMAIN, f"delivery_problems_{eid}") is None

    assert await hass.config_entries.async_unload(eid)
    assert issues.async_get_issue(DOMAIN, f"credits_low_{eid}") is None


async def test_config_flow(hass: HomeAssistant, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    aioclient_mock.get(f"{API}/account", status=401, json={"code": "unauthorized"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"api_key": "falsch"})
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{API}/account", json=ACCOUNT)
    aioclient_mock.get(f"{API}/smtp/statistics/aggregatedReport", json=REPORT_24H)
    aioclient_mock.get(f"{API}/smtp/statistics/events", json=EVENTS)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"api_key": f"  {API_KEY}  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["api_key"] == API_KEY
    assert result["title"] == "Brevo (robben.tech)"
    assert result["result"].unique_id == ACCOUNT["organization_id"]


async def test_reauth_on_invalid_key(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    aioclient_mock.get(f"{API}/account", status=401, json={"code": "unauthorized"})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = [f for f in hass.config_entries.flow.async_progress() if f["context"]["source"] == "reauth"]
    assert len(flows) == 1

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{API}/account", json=ACCOUNT)
    aioclient_mock.get(f"{API}/smtp/statistics/aggregatedReport", json=REPORT_24H)
    aioclient_mock.get(f"{API}/smtp/statistics/events", json=EVENTS)
    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {"api_key": "xkeysib-neuer-schluessel"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["api_key"] == "xkeysib-neuer-schluessel"


async def test_options_and_diagnostics(hass: HomeAssistant, mock_brevo, config_entry) -> None:
    from custom_components.brevo.diagnostics import async_get_config_entry_diagnostics

    await _setup(hass, config_entry)
    flow = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"], {"scan_interval": 30, "credits_threshold": 300}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {"scan_interval": 30, "credits_threshold": 300}
    # Schwelle 300 > 273 Guthaben -> Hinweis erscheint nach dem Reload
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"credits_low_{config_entry.entry_id}")

    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diag["entry"]["data"]["api_key"] == "**REDACTED**"
    assert "bounce@example.com" not in str(diag)
