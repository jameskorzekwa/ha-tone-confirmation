"""Conversation agent that replaces successful action speech with a tone."""

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import Literal

import voluptuous as vol
from homeassistant.components import conversation
from homeassistant.components.conversation.agent_manager import async_get_agent
from homeassistant.components.conversation.const import (
    DATA_COMPONENT,
    ConversationEntityFeature,
)
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, MATCH_ALL
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    ASSIST_SATELLITE_DOMAIN,
    CONF_CONFIRMATION_SCRIPT,
    CONF_LEGACY_ENTITY_ID,
    CONF_TARGET_AGENT,
    DEFAULT_TARGET_AGENT,
    DOMAIN,
    LEGACY_UNIQUE_ID,
    NAME,
    TONE_FILENAME,
    TONE_URL,
    TONE_WAIT_TIMEOUT,
)

TONE_PATH = Path(__file__).parent / "media" / TONE_FILENAME

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_TARGET_AGENT, default=DEFAULT_TARGET_AGENT
                ): cv.entity_id,
                vol.Optional(CONF_CONFIRMATION_SCRIPT): cv.entity_id,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class ToneConfirmationAgent(conversation.ConversationEntity):
    """Delegate to Google and suppress speech after successful actions."""

    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, target_agent: str, name: str, unique_id: str) -> None:
        """Initialize the wrapper."""
        self._target_agent = target_agent
        self._attr_name = name
        self._attr_unique_id = unique_id

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
            self.hass.async_create_background_task(
                _async_play_confirmation_tone(
                    self.hass, user_input.satellite_id, user_input.context
                ),
                "play bundled Assist confirmation tone",
            )

        return result


async def _async_play_confirmation_tone(
    hass: HomeAssistant, satellite_id: str, context: Context
) -> None:
    """Wait for the satellite to finish its pipeline, then play the tone."""
    state_changed = asyncio.Event()
    remove_listener = async_track_state_change_event(
        hass, [satellite_id], lambda _: state_changed.set()
    )
    try:
        async with asyncio.timeout(TONE_WAIT_TIMEOUT):
            while (
                satellite_state := hass.states.get(satellite_id)
            ) is None or satellite_state.state != "idle":
                await state_changed.wait()
                state_changed.clear()
    except TimeoutError:
        return
    finally:
        remove_listener()

    await hass.services.async_call(
        ASSIST_SATELLITE_DOMAIN,
        "announce",
        {
            ATTR_ENTITY_ID: satellite_id,
            "media_id": TONE_URL,
            "preannounce": False,
        },
        blocking=False,
        context=context,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import legacy YAML configuration."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(TONE_URL, str(TONE_PATH))]
    )
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
    legacy_entity = entry.data.get(CONF_LEGACY_ENTITY_ID, False)
    component: EntityComponent[conversation.ConversationEntity] = hass.data[
        DATA_COMPONENT
    ]
    agent = ToneConfirmationAgent(
        entry.data[CONF_TARGET_AGENT],
        NAME if legacy_entity else entry.title,
        LEGACY_UNIQUE_ID if legacy_entity else entry.entry_id,
    )
    await component.async_add_entities([agent])
    entry.runtime_data = agent
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a tone confirmation config entry."""
    await entry.runtime_data.async_remove()
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate singleton entries to the multi-entry data format."""
    if entry.version > 3:
        return False

    if entry.version <= 2:
        options = dict(entry.options)
        options.pop(CONF_CONFIRMATION_SCRIPT, None)
        target_agent = options.pop(CONF_TARGET_AGENT, DEFAULT_TARGET_AGENT)
        target_state = hass.states.get(target_agent)
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_TARGET_AGENT: target_agent,
                CONF_LEGACY_ENTITY_ID: True,
            },
            options=options,
            title=(
                f"Tone Confirmation: {target_state.name}"
                if target_state
                else entry.title
            ),
            unique_id=target_agent,
            version=3,
        )

    return True
