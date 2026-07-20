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
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType

DOMAIN = "tone_confirmation"
CONF_TARGET_AGENT = "target_agent"
CONF_CONFIRMATION_SCRIPT = "confirmation_script"
DEFAULT_TARGET_AGENT = "conversation.google_generative_ai"
DEFAULT_CONFIRMATION_SCRIPT = "script.voice_command_acknowledge"

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
    """Set up the tone-confirming conversation entity."""
    domain_config = config[DOMAIN]
    component: EntityComponent[conversation.ConversationEntity] = hass.data[
        DATA_COMPONENT
    ]
    await component.async_add_entities(
        [
            ToneConfirmationAgent(
                domain_config[CONF_TARGET_AGENT],
                domain_config[CONF_CONFIRMATION_SCRIPT],
            )
        ]
    )
    return True
