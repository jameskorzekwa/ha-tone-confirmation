"""Conversation agent behavior tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent

from custom_components.tone_confirmation import (
    DEFAULT_TARGET_AGENT,
    ToneConfirmationAgent,
    _async_play_confirmation_tone,
)
from custom_components.tone_confirmation.const import TONE_URL


class FakeGoogleAgent(conversation.ConversationEntity):
    """Minimal Google conversation entity for delegation tests."""

    _attr_name = "Fake Google"

    @property
    def supported_languages(self):
        """Return supported languages."""
        return MATCH_ALL


def _user_input(*, satellite_id: str | None = "assist_satellite.test"):
    return conversation.ConversationInput(
        text="Turn off the lamp",
        context=Context(),
        conversation_id="test-conversation",
        device_id="test-device",
        satellite_id=satellite_id,
        language="en",
        agent_id="conversation.tone_confirmation_conversation",
    )


def _result(*, success: bool, failed: bool = False):
    response = intent.IntentResponse(language="en")
    response.async_set_speech("OK.")
    response.async_set_results(
        [
            intent.IntentResponseTarget(
                name="Lamp",
                type=intent.IntentResponseTargetType.ENTITY,
                id="light.lamp",
            )
        ]
        if success
        else [],
        [
            intent.IntentResponseTarget(
                name="Other lamp",
                type=intent.IntentResponseTargetType.ENTITY,
                id="light.other_lamp",
            )
        ]
        if failed
        else [],
    )
    return conversation.ConversationResult(
        response=response,
        conversation_id="test-conversation",
    )


@pytest.fixture
def agent(hass: HomeAssistant) -> ToneConfirmationAgent:
    """Create a wrapper agent attached to Home Assistant."""
    wrapper = ToneConfirmationAgent(DEFAULT_TARGET_AGENT)
    wrapper.hass = hass
    return wrapper


async def _call_agent(
    agent: ToneConfirmationAgent,
    hass: HomeAssistant,
    result: conversation.ConversationResult,
    *,
    satellite_id: str | None = "assist_satellite.test",
):
    target = FakeGoogleAgent()
    original_listener = MagicMock()
    chat_log = MagicMock(delta_listener=original_listener)

    async def handle_message(user_input, delegated_chat_log):
        assert user_input.agent_id == DEFAULT_TARGET_AGENT
        assert delegated_chat_log.delta_listener is None
        return result

    target._async_handle_message = handle_message
    service_call = AsyncMock()
    if satellite_id:
        hass.states.async_set(satellite_id, "idle")

    with (
        patch(
            "custom_components.tone_confirmation.async_get_agent",
            return_value=target,
        ),
        patch("homeassistant.core.ServiceRegistry.async_call", service_call),
    ):
        returned = await agent._async_handle_message(
            _user_input(satellite_id=satellite_id), chat_log
        )
        await hass.async_block_till_done()

    assert chat_log.delta_listener is original_listener
    return returned, service_call


async def test_success_clears_speech_and_plays_one_tone(
    agent: ToneConfirmationAgent, hass: HomeAssistant
) -> None:
    """Successful actions become one asynchronous tone call."""
    returned, service_call = await _call_agent(agent, hass, _result(success=True))

    assert returned.response.speech["plain"]["speech"] == ""
    service_call.assert_awaited_once()
    assert service_call.await_args.args == (
        "assist_satellite",
        "announce",
        {
            "entity_id": "assist_satellite.test",
            "media_id": TONE_URL,
            "preannounce": False,
        },
    )
    assert service_call.await_args.kwargs["blocking"] is False
    assert isinstance(service_call.await_args.kwargs["context"], Context)


async def test_success_without_satellite_preserves_speech(
    agent: ToneConfirmationAgent, hass: HomeAssistant
) -> None:
    """Calls outside a satellite pipeline keep speech instead of going silent."""
    returned, service_call = await _call_agent(
        agent, hass, _result(success=True), satellite_id=None
    )

    assert returned.response.speech["plain"]["speech"] == "OK."
    service_call.assert_not_awaited()


async def test_tone_waits_until_satellite_is_idle(hass: HomeAssistant) -> None:
    """Do not announce while the originating satellite is processing."""
    satellite_id = "assist_satellite.test"
    hass.states.async_set(satellite_id, "processing")
    service_call = AsyncMock()
    context = Context()

    with patch("homeassistant.core.ServiceRegistry.async_call", service_call):
        task = asyncio.create_task(
            _async_play_confirmation_tone(hass, satellite_id, context)
        )
        await asyncio.sleep(0)
        service_call.assert_not_awaited()

        hass.states.async_set(satellite_id, "idle")
        await task

    service_call.assert_awaited_once()
    assert service_call.await_args.kwargs["context"] is context


@pytest.mark.parametrize(
    "result",
    [
        _result(success=False),
        _result(success=True, failed=True),
    ],
)
async def test_non_success_preserves_speech(
    agent: ToneConfirmationAgent,
    hass: HomeAssistant,
    result: conversation.ConversationResult,
) -> None:
    """Queries and partial failures remain spoken and do not play a tone."""
    returned, service_call = await _call_agent(agent, hass, result)

    assert returned.response.speech["plain"]["speech"] == "OK."
    service_call.assert_not_awaited()


async def test_missing_google_agent_raises(
    agent: ToneConfirmationAgent,
) -> None:
    """Fail clearly when the delegated Google agent is unavailable."""
    with (
        patch("custom_components.tone_confirmation.async_get_agent", return_value=None),
        pytest.raises(
            HomeAssistantError,
            match=(
                r"Conversation agent conversation\.google_generative_ai "
                r"is unavailable"
            ),
        ),
    ):
        await agent._async_handle_message(_user_input(), MagicMock())
