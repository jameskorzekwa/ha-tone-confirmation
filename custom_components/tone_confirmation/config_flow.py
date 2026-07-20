"""Config flow for Tone Confirmation Conversation."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_TARGET_AGENT,
    DEFAULT_CONFIRMATION_SCRIPT,
    DEFAULT_TARGET_AGENT,
    DOMAIN,
    NAME,
)


def _schema(values: dict[str, Any] | None = None) -> vol.Schema:
    """Build the configuration schema with current values."""
    values = values or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_TARGET_AGENT,
                default=values.get(CONF_TARGET_AGENT, DEFAULT_TARGET_AGENT),
            ): EntitySelector(EntitySelectorConfig(domain="conversation")),
            vol.Required(
                CONF_CONFIRMATION_SCRIPT,
                default=values.get(
                    CONF_CONFIRMATION_SCRIPT, DEFAULT_CONFIRMATION_SCRIPT
                ),
            ): EntitySelector(EntitySelectorConfig(domain="script")),
        }
    )


class ToneConfirmationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Tone Confirmation Conversation config flow."""

    VERSION = 1

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return OptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle setup from the integrations UI."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data={}, options=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema())

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import configuration from YAML."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title=NAME,
            data={},
            options={
                CONF_TARGET_AGENT: import_data.get(
                    CONF_TARGET_AGENT, DEFAULT_TARGET_AGENT
                ),
                CONF_CONFIRMATION_SCRIPT: import_data.get(
                    CONF_CONFIRMATION_SCRIPT, DEFAULT_CONFIRMATION_SCRIPT
                ),
            },
        )


class OptionsFlow(OptionsFlowWithReload):
    """Handle Tone Confirmation Conversation options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the wrapped conversation agent and confirmation script."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(dict(self.config_entry.options)),
        )
