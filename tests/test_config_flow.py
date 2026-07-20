"""Config flow tests."""

from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.tone_confirmation.const import (
    CONF_CONFIRMATION_SCRIPT,
    CONF_TARGET_AGENT,
    DEFAULT_CONFIRMATION_SCRIPT,
    DEFAULT_TARGET_AGENT,
    DOMAIN,
)


async def test_user_flow_and_options_reload(hass: HomeAssistant) -> None:
    """Set up through the UI and reload when options change."""
    assert await async_setup_component(hass, "homeassistant", {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TARGET_AGENT: DEFAULT_TARGET_AGENT,
            CONF_CONFIRMATION_SCRIPT: DEFAULT_CONFIRMATION_SCRIPT,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    await hass.async_block_till_done()
    assert hass.states.get("conversation.tone_confirmation_conversation") is not None

    options = await hass.config_entries.options.async_init(entry.entry_id)
    assert options["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        options["flow_id"],
        {
            CONF_TARGET_AGENT: "conversation.test_agent",
            CONF_CONFIRMATION_SCRIPT: "script.test_tone",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {
        CONF_TARGET_AGENT: "conversation.test_agent",
        CONF_CONFIRMATION_SCRIPT: "script.test_tone",
    }
    assert entry.runtime_data._target_agent == "conversation.test_agent"
    assert entry.runtime_data._script_service == "test_tone"


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
    assert entries[0].options == {
        CONF_TARGET_AGENT: "conversation.legacy_agent",
        CONF_CONFIRMATION_SCRIPT: "script.legacy_tone",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
