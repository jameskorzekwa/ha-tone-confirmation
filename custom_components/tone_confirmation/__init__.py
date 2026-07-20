"""Conversation agent that replaces successful action speech with a tone."""

from dataclasses import replace
from typing import Literal

import voluptuous as vol
from homeassistant.components import conversation
from homeassistant.components.conversation.agent_manager import async_get_agent
from homeassistant.components.conversation.const import (
    DATA_COMPONENT,
    ConversationEntityFeature,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_TARGET_AGENT,
    DEFAULT_CONFIRMATION_SCRIPT,
    DEFAULT_TARGET_AGENT,
    DOMAIN,
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_TARGET_AGENT, default=DEFAULT_TARGET_AGENT
                ): cv.entity_id,
                vol.Optional(
                    CONF_CONFIRMATION_SCRIPT, default=DEFAULT_CONFIRMATION_SCRIPT
                ): cv.entity_id,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class ToneConfirmationAgent(conversation.ConversationEntity):
    """Delegate to Google and suppress speech after successful actions."""

    _attr_name = "Tone Confirmation Conversation"
    _attr_unique_id = "tone_confirmation_conversation"
    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, target_agent: str, confirmation_script: str) -> None:
        """Initialize the wrapper."""
        self._target_agent = target_agent
        self._script_domain, self._script_service = split_entity_id(confirmation_script)

    @property
    def supported_languages(self) -> Literal["*"]:
        """Return supported languages."""
        return MATCH_ALL

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process a message with Google and replace action speech with a tone."""
        target = async_get_agent(self.hass, self._target_agent)
        if not isinstance(target, conversation.ConversationEntity) or target is self:
            raise HomeAssistantError(
                f"Conversation agent {self._target_agent} is unavailable"
            )

        # Buffer Google's response so the pipeline cannot begin streaming TTS
        # before we know whether the completed result should become a tone.
        delta_listener = chat_log.delta_listener
        chat_log.delta_listener = None
        try:
            result = await target._async_handle_message(
                replace(user_input, agent_id=self._target_agent), chat_log
            )
        finally:
            chat_log.delta_listener = delta_listener

        response = result.response
        if (
            response.response_type is intent.IntentResponseType.ACTION_DONE
            and response.success_results
            and not response.failed_results
            and user_input.satellite_id
        ):
            response.async_set_speech("")
            await self.hass.services.async_call(
                self._script_domain,
                self._script_service,
                {"satellite_id": user_input.satellite_id},
                blocking=False,
                context=user_input.context,
            )

        return result


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import legacy YAML configuration."""
    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the tone-confirming conversation entity from a config entry."""
    options = {
        CONF_TARGET_AGENT: DEFAULT_TARGET_AGENT,
        CONF_CONFIRMATION_SCRIPT: DEFAULT_CONFIRMATION_SCRIPT,
        **entry.options,
    }
    component: EntityComponent[conversation.ConversationEntity] = hass.data[
        DATA_COMPONENT
    ]
    agent = ToneConfirmationAgent(
        options[CONF_TARGET_AGENT],
        options[CONF_CONFIRMATION_SCRIPT],
    )
    await component.async_add_entities([agent])
    entry.runtime_data = agent
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a tone confirmation config entry."""
    await entry.runtime_data.async_remove()
    return True
