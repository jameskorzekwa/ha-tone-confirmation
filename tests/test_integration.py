"""Integration setup tests."""

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tone_confirmation import DOMAIN, ToneConfirmationAgent
from custom_components.tone_confirmation.const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_TARGET_AGENT,
    DEFAULT_CONFIRMATION_SCRIPT,
    DEFAULT_TARGET_AGENT,
)


async def test_setup_creates_conversation_entity(hass: HomeAssistant) -> None:
    """Set up the integration and register its conversation entity."""
    assert await async_setup_component(hass, "homeassistant", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Tone Confirmation Conversation",
        data={},
        options={
            CONF_TARGET_AGENT: DEFAULT_TARGET_AGENT,
            CONF_CONFIRMATION_SCRIPT: DEFAULT_CONFIRMATION_SCRIPT,
        },
        source="user",
        version=1,
        unique_id=None,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("conversation.tone_confirmation_conversation")
    assert state is not None
    assert state.attributes["supported_features"] == 1
    assert isinstance(entry.runtime_data, ToneConfirmationAgent)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    unloaded_state = hass.states.get("conversation.tone_confirmation_conversation")
    assert unloaded_state is not None
    assert unloaded_state.state == STATE_UNAVAILABLE
