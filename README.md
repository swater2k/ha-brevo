<p align="center">
  <img src="custom_components/brevo/brand/icon@2x.png" alt="Brevo integration icon" width="128">
</p>

<h1 align="center">Brevo for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/swater2k/ha-brevo/releases"><img src="https://img.shields.io/github/v/release/swater2k/ha-brevo" alt="Release"></a>
</p>

A custom integration that monitors your [Brevo](https://www.brevo.com) transactional e-mail account in Home Assistant: remaining credits, delivery rate, bounces, blocked recipients and spam reports — so you notice when the mails your services rely on stop arriving.

Useful whenever Brevo is the SMTP relay behind something important: password resets, two-factor codes, alerting or order confirmations.

> [!NOTE]
> Community project, not affiliated with Brevo.

## Features

- **Credits**: remaining e-mail and SMS credits, plan type, warning before they run out
- **Delivery**: e-mails sent, delivery rate, hard and soft bounces, blocked recipients, spam reports and invalid addresses over 24 hours and 7 days
- **Event entity**: fires per new bounce, block or spam report with recipient, subject and reason — ready as an automation trigger
- **Repair issues** when credits run low or mails were rejected
- Read-only: the integration only calls `GET` endpoints and never sends mail

## Requirements

- Home Assistant **2026.2** or newer
- A Brevo account and an **API key v3**

## Create an API key

In Brevo: avatar menu → **SMTP & API** → **API keys** → **Generate a new API key**. Copy it right away, it is shown only once.

The integration only reads: `/account`, `/smtp/statistics/aggregatedReport` and `/smtp/statistics/events`.

## Installation

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/swater2k/ha-brevo`, type **Integration**
2. Download **Brevo** and restart Home Assistant
3. **Settings → Devices & services → Add integration → Brevo**, then paste the API key

Manual alternative: copy `custom_components/brevo` into your `custom_components` folder and restart.

If Brevo ever rejects the key, Home Assistant asks for a new one through the usual re-authentication dialog.

### Options

| Option | Default | Description |
|---|---|---|
| Polling interval | `15 min` | The data changes slowly; 5–120 minutes are possible |
| Warn below credits | `50` | Creates a repair issue when fewer e-mail credits are left |

## Entities

Entities marked ✗ are disabled by default and can be enabled in the entity settings.

| Entity | Type | Default |
|---|---|---|
| E-mail credits (plan as attribute) | sensor | ✓ |
| SMS credits | sensor | ✗ |
| E-mails sent (24 h) / (7 days) | sensor | ✓ |
| Delivery rate (24 h) | sensor (%) | ✓ |
| Delivery rate (7 days), delivery problems (7 days) | sensor | ✗ |
| Delivery problems (24 h) — bounces, blocked and invalid combined | sensor | ✓ |
| Hard bounces (24 h), blocked (24 h), spam reports (24 h) | sensor | ✓ |
| Soft bounces, invalid addresses, unsubscribes, opens, clicks (24 h) | sensor | ✗ |
| Delivered (24 h) | sensor | ✗ |
| Last delivery problem (recipient, subject, reason as attributes) | sensor (timestamp) | ✓ |
| Delivery event | event | ✓ |
| Delivery problem | binary sensor (problem) | ✓ |
| API reachable, SMTP relay active | binary sensor (diagnostic) | ✓ |
| Plan | sensor (diagnostic) | ✓ |
| SMTP relay | sensor (diagnostic) | ✗ |

## Delivery events

The event entity fires once per new problem event since the last poll.

| Event type | Meaning |
|---|---|
| `hard_bounce` | Permanently rejected, e.g. the address does not exist |
| `soft_bounce` | Temporarily rejected, e.g. mailbox full |
| `blocked` | Recipient is on the blocked list, often after an earlier hard bounce |
| `spam` | Recipient marked the mail as spam |
| `invalid` | Address is not valid |
| `deferred` | Delivery postponed by the receiving server |
| `error` | Brevo reported an error |

Each event carries `email`, `subject`, `reason`, `date` and `tag`.

### Example automation

```yaml
automation:
  - alias: "Brevo: notify on delivery problems"
    triggers:
      - trigger: event.received
        target:
          entity_id: event.brevo_delivery_event
        options:
          event_type: [hard_bounce, blocked, spam]
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "Brevo"
          message: >
            {% set a = state_attr('event.brevo_delivery_event', 'reason') %}
            {{ state_attr('event.brevo_delivery_event', 'email') }}
            could not be reached{% if a %}: {{ a }}{% endif %}
```

## Repair issues

| Issue | When |
|---|---|
| E-mail credits running low | Fewer credits left than the configured threshold |
| Brevo could not deliver e-mails | Hard bounces or blocked recipients in the last 24 hours |

Both disappear on their own once the cause is gone.

## Notes

- **Hard bounces stay blocked.** Brevo keeps rejecting an address until you remove it from the blocked contacts list, so a single typo keeps showing up.
- **Aggregated values come from Brevo**, not from Home Assistant. They are therefore correct even after a restart.
- **The 24 h and 7 day windows** are calendar based on Brevo's side (`days=1`, `days=7`).
- **Rate limits**: one poll makes four API calls. The default interval of 15 minutes stays far below Brevo's limits.

## Removal

1. **Settings → Devices & services → Brevo → ⋮ → Delete**
2. Remove the repository in HACS and restart Home Assistant
3. Optionally delete the API key in Brevo

## Troubleshooting

- **"API key rejected by Brevo"**: the key was deleted or copied incompletely. Generate a new one and re-authenticate.
- **Credits sensor is empty**: the account has no plan with e-mail credits, e.g. some pay-as-you-go setups.
- **No events**: `/smtp/statistics/events` only returns the last 24 hours by default, and only if mails were actually sent.
- **Diagnostics**: Settings → Devices & services → Brevo → ⋮ → Download diagnostics. The API key and the recipient address are redacted.

```yaml
logger:
  logs:
    custom_components.brevo: debug
```

## License

[MIT](LICENSE)
