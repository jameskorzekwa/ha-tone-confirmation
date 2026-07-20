"""Integration setup tests."""

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tone_confirmation import DOMAIN, ToneConfirmationAgent
from custom_components.tone_confirmation.const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_LEGACY_ENTITY_ID,
    CONF_TARGET_AGENT,
    DEFAULT_TARGET_AGENT,
    TONE_URL,
)


async def test_setup_migrates_entry_and_serves_tone(
    hass: HomeAssistant, hass_client
) -> None:
    """Migrate the singleton entry while preserving its conversation entity."""
    assert await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set(
        DEFAULT_TARGET_AGENT, "unknown", {"friendly_name": "Google Generative AI"}
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Tone Confirmation Conversation",
        data={},
        options={
            CONF_TARGET_AGENT: DEFAULT_TARGET_AGENT,
            CONF_CONFIRMATION_SCRIPT: "script.voice_command_acknowledge",
        },
        source="user",
        version=1,
        unique_id=None,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3
    assert entry.data == {
        CONF_TARGET_AGENT: DEFAULT_TARGET_AGENT,
        CONF_LEGACY_ENTITY_ID: True,
    }
    assert entry.options == {}
    assert entry.unique_id == DEFAULT_TARGET_AGENT
    assert entry.title == "Tone Confirmation: Google Generative AI"

    state = hass.states.get("conversation.tone_confirmation_conversation")
    assert state is not None
    assert state.attributes["supported_features"] == 1
    assert isinstance(entry.runtime_data, ToneConfirmationAgent)

    client = await hass_client()
    response = await client.get(TONE_URL)
    assert response.status == 200
    assert response.content_type == "audio/x-wav"
    assert (await response.read()).startswith(b"RIFF")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    unloaded_state = hass.states.get("conversation.tone_confirmation_conversation")
    assert unloaded_state is not None
    assert unloaded_state.state == STATE_UNAVAILABLE
