# Tone Confirmation Conversation

A Home Assistant conversation agent that delegates to another conversation
entity and replaces spoken confirmations for successful home-control actions
with one Assist acknowledgment tone.

Questions, informational replies, clarifications, and failed actions remain
spoken. Google response deltas are buffered so streamed TTS cannot begin before
the completed action result is inspected.

## Requirements

- Home Assistant 2026.7 or newer
- A conversation entity such as `conversation.google_generative_ai`

## Installation with HACS

### 1. Install the integration

Until this repository is included in the default HACS repository list:

1. In Home Assistant, open **HACS → Integrations**.
2. Open the top-right menu and choose **Custom repositories**.
3. Add `https://github.com/jameskorzekwa/ha-tone-confirmation` with category
   **Integration**.
4. Find **Tone Confirmation Conversation** in HACS and choose **Download**.

Restart Home Assistant after HACS finishes downloading the integration.

### 2. Add and configure the integration

1. Open **Settings → Devices & services** and choose **Add integration**.
2. Search for **Tone Confirmation Conversation**.
3. Select the conversation agent to wrap, then choose **Submit**.
4. Open **Settings → Voice assistants → Assist** and edit the pipeline used by
   your Assist satellite.
5. Set **Conversation agent** to **Tone Confirmation Conversation** and save.

The underlying agent must already be configured and available. You can change
the selection later from the integration's **Configure** button. The short
two-note confirmation tone is included with the integration.

### 3. Verify the result

Ask an informational question first; its answer should still be spoken. Then
ask the same satellite to perform a home-control action. A fully successful
action should produce one tone and no spoken confirmation. Failed actions and
clarification questions remain spoken.

If a request does not originate from an Assist satellite, the wrapper preserves
the spoken response because it has nowhere to play the confirmation tone.

### Upgrading

Version 1.1 imports the existing `tone_confirmation:` YAML configuration into
the UI automatically. After updating and restarting Home Assistant once, remove
the complete `tone_confirmation:` block from `configuration.yaml`; subsequent
changes are made with the integration's **Configure** button.

Version 1.2 replaces the external confirmation script and media file with a
bundled tone. Existing configuration entries migrate automatically. The old
confirmation script and `/config/media/voice/acknowledge.mp3` are no longer
used and may be removed after verifying the upgrade.

## Behavior

- Successful action with no failed targets: clear speech, wait for the Assist
  satellite to become idle, and play the bundled tone once.
- Query, clarification, or failure: preserve Google's spoken response.
- Multi-turn conversations: preserve the delegated agent's chat log and
  continuation state.

## Development

```bash
python -m pip install -r requirements-test.txt
ruff check .
ruff format --check .
pytest
bash .github/scripts/build_release.sh
```
