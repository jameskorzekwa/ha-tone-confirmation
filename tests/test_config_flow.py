"""Config flow tests."""

from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.tone_confirmation.const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_LEGACY_ENTITY_ID,
    CONF_TARGET_AGENT,
    DEFAULT_TARGET_AGENT,
    DOMAIN,
)


async def _create_entry(hass: HomeAssistant, target_agent: str):
    """Create a wrapper entry through the user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TARGET_AGENT: target_agent}
    )


async def test_multiple_entries_and_options_reload(hass: HomeAssistant) -> None:
    """Create multiple wrappers, prevent duplicates, and edit a target."""
    assert await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set(
        DEFAULT_TARGET_AGENT, "unknown", {"friendly_name": "Google Generative AI"}
    )
    hass.states.async_set("conversation.openai", "unknown", {"friendly_name": "OpenAI"})
    hass.states.async_set(
        "conversation.anthropic", "unknown", {"friendly_name": "Anthropic"}
    )

    result = await _create_entry(hass, DEFAULT_TARGET_AGENT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    google_entry = result["result"]

    result = await _create_entry(hass, "conversation.openai")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    openai_entry = result["result"]
    await hass.async_block_till_done()
    assert google_entry.title == "Tone Confirmation: Google Generative AI"
    assert openai_entry.title == "Tone Confirmation: OpenAI"
    assert google_entry.runtime_data._target_agent == DEFAULT_TARGET_AGENT
    assert openai_entry.runtime_data._target_agent == "conversation.openai"
    assert hass.states.get("conversation.tone_confirmation_google_generative_ai")
    assert hass.states.get("conversation.tone_confirmation_openai")

    result = await _create_entry(hass, DEFAULT_TARGET_AGENT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    options = await hass.config_entries.options.async_init(openai_entry.entry_id)
    assert options["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {CONF_TARGET_AGENT: "conversation.anthropic"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert openai_entry.data[CONF_TARGET_AGENT] == "conversation.anthropic"
    assert openai_entry.unique_id == "conversation.anthropic"
    assert openai_entry.title == "Tone Confirmation: Anthropic"
    assert openai_entry.runtime_data._target_agent == "conversation.anthropic"
    assert hass.states.get("conversation.tone_confirmation_openai")

    options = await hass.config_entries.options.async_init(google_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        options["flow_id"], {CONF_TARGET_AGENT: "conversation.anthropic"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "already_configured"}


async def test_yaml_is_imported_once(hass: HomeAssistant) -> None:
    """Migrate a shipped YAML configuration into a config entry."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass,
        DOMAIN,
        {
            DOMAIN: {
                CONF_TARGET_AGENT: "conversation.legacy_agent",
                CONF_CONFIRMATION_SCRIPT: "script.legacy_tone",
            }
        },
    )
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].source == SOURCE_IMPORT
    assert entries[0].data == {
        CONF_TARGET_AGENT: "conversation.legacy_agent",
        CONF_LEGACY_ENTITY_ID: True,
    }
    assert entries[0].options == {}
    assert entries[0].unique_id == "conversation.legacy_agent"
    assert hass.states.get("conversation.tone_confirmation_conversation") is not None

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_TARGET_AGENT: "conversation.legacy_agent"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
