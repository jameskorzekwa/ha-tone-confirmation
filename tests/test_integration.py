"""Integration setup tests."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.tone_confirmation import DOMAIN


async def test_setup_creates_conversation_entity(hass: HomeAssistant) -> None:
    """Set up the integration and register its conversation entity."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: {}})
    await hass.async_block_till_done()

    state = hass.states.get("conversation.tone_confirmation_conversation")
    assert state is not None
    assert state.attributes["supported_features"] == 1
