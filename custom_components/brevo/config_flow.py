"""Config-, Reauth- und Options-Flow."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import Account, BrevoAuthError, BrevoClient, BrevoConnectionError, BrevoError
from .const import (
    CONF_CREDITS_THRESHOLD,
    CONF_SCAN_INTERVAL,
    DEFAULT_CREDITS_THRESHOLD,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


async def validate_key(hass: HomeAssistant, api_key: str) -> tuple[Account | None, str | None]:
    """Gibt (Account, Fehlercode) zurück."""
    client = BrevoClient(async_get_clientsession(hass), api_key)
    try:
        return await client.account(), None
    except BrevoAuthError:
        return None, "invalid_auth"
    except BrevoConnectionError:
        return None, "cannot_connect"
    except BrevoError:
        return None, "unknown_response"
    except Exception:
        _LOGGER.exception("Unerwarteter Fehler bei der Validierung")
        return None, "unknown"


class BrevoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            account, error = await validate_key(self.hass, api_key)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(account.organization_id or api_key[-8:])
                self._abort_if_unique_id_configured()
                title = f"Brevo ({account.company})" if account.company else "Brevo"
                return self.async_create_entry(title=title, data={CONF_API_KEY: api_key})
        return self.async_show_form(step_id="user", data_schema=_KEY_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            _, error = await validate_key(self.hass, api_key)
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_API_KEY: api_key}
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=_KEY_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BrevoOptionsFlow:
        return BrevoOptionsFlow()


class BrevoOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_CREDITS_THRESHOLD: int(user_input[CONF_CREDITS_THRESHOLD]),
                }
            )
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=5,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CREDITS_THRESHOLD,
                    default=opts.get(CONF_CREDITS_THRESHOLD, DEFAULT_CREDITS_THRESHOLD),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=100000, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
