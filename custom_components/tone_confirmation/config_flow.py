"""Config flow for Tone Confirmation Conversation."""

from __future__ import annotations

from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.config_entries import (
    OptionsFlow as HomeAssistantOptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    CONF_LEGACY_ENTITY_ID,
    CONF_TARGET_AGENT,
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
        }
    )


def _entry_title(flow: ConfigFlow | OptionsFlow, target_agent: str) -> str:
    """Build a readable entry and entity name from the target agent."""
    target_state = flow.hass.states.get(target_agent)
    target_name = target_state.name if target_state else target_agent
    return f"Tone Confirmation: {target_name}"


class ToneConfirmationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Tone Confirmation Conversation config flow."""

    VERSION = 3

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
        if user_input is not None:
            target_agent = user_input[CONF_TARGET_AGENT]
            await self.async_set_unique_id(target_agent)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_entry_title(self, target_agent), data=user_input
            )

        return self.async_show_form(step_id="user", data_schema=_schema())

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import configuration from YAML."""
        target_agent = import_data.get(CONF_TARGET_AGENT, DEFAULT_TARGET_AGENT)
        await self.async_set_unique_id(target_agent)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=NAME,
            data={
                CONF_TARGET_AGENT: target_agent,
                CONF_LEGACY_ENTITY_ID: True,
            },
        )


class OptionsFlow(HomeAssistantOptionsFlow):
    """Handle Tone Confirmation Conversation options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit the wrapped conversation agent."""
        errors: dict[str, str] = {}
        if user_input is not None:
            target_agent = user_input[CONF_TARGET_AGENT]
            if any(
                entry.entry_id != self.config_entry.entry_id
                and entry.data.get(CONF_TARGET_AGENT) == target_agent
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ):
                errors["base"] = "already_configured"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        CONF_TARGET_AGENT: target_agent,
                    },
                    title=_entry_title(self, target_agent),
                    unique_id=target_agent,
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or dict(self.config_entry.data)),
            errors=errors,
        )
