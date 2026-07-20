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
- A script accepting a required `satellite_id` field

## Installation with HACS

### 1. Install the integration

Until this repository is included in the default HACS repository list:

1. In Home Assistant, open **HACS → Integrations**.
2. Open the top-right menu and choose **Custom repositories**.
3. Add `https://github.com/jameskorzekwa/ha-tone-confirmation` with category
   **Integration**.
4. Find **Tone Confirmation Conversation** in HACS and choose **Download**.

Do not restart yet; complete the YAML and script setup below first.

### 2. Add the integration to `configuration.yaml`

Open the Home Assistant configuration directory using File editor, Studio Code
Server, Samba, or SSH. Edit the top-level `/config/configuration.yaml` file, the
same file that normally contains `default_config:` and `automation:`.

Add this block at the left margin, not inside another integration's section:

```yaml
tone_confirmation:
```

That minimal configuration uses these defaults:

```yaml
tone_confirmation:
  target_agent: conversation.google_generative_ai
  confirmation_script: script.voice_command_acknowledge
```

To wrap a different conversation entity or use a differently named script,
specify its entity ID here. Only add one `tone_confirmation:` block.

### 3. Provide the confirmation sound

The example script below plays
`/config/media/voice/acknowledge.mp3`. Create the `voice` directory under
Home Assistant's `media` directory if needed, then place your preferred short
confirmation sound at that path.

You can use another Home Assistant media source instead. If you do, replace the
script's `media_id` with the media ID shown by Home Assistant's Media browser.

### 4. Create the confirmation script

1. Open **Settings → Automations & scenes → Scripts**.
2. Choose **Create script → Create new script**.
3. Open the script menu and choose **Edit in YAML**.
4. Replace the editor contents with:

   ```yaml
   alias: Voice Command Acknowledge
   mode: parallel
   max: 4
   fields:
     satellite_id:
       name: Satellite
       description: Assist satellite that received the command.
       required: true
       selector:
         entity:
           domain: assist_satellite
   sequence:
     - wait_template: "{{ is_state(satellite_id, 'idle') }}"
       timeout: "00:00:03"
       continue_on_timeout: false
     - action: assist_satellite.announce
       target:
         entity_id: "{{ satellite_id }}"
       data:
         media_id: media-source://media_source/local/voice/acknowledge.mp3
         preannounce: false
   ```

5. Save the script.
6. Confirm its entity ID is `script.voice_command_acknowledge` under
   **Settings → Devices & services → Entities**. If Home Assistant assigned a
   different ID, put that ID in `confirmation_script` in `configuration.yaml`.

### 5. Restart and select the wrapper

1. Validate the configuration from **Developer tools → YAML → Check
   configuration**.
2. Restart Home Assistant from **Settings → System → Restart Home Assistant**.
3. Open **Settings → Voice assistants → Assist** and edit the pipeline used by
   your Assist satellite.
4. Set **Conversation agent** to **Tone Confirmation Conversation** and save.

The underlying agent must already be configured and available as the
`target_agent` entity. For the default configuration, set up Google Generative
AI Conversation before selecting this wrapper.

### 6. Verify the result

Ask an informational question first; its answer should still be spoken. Then
ask the same satellite to perform a home-control action. A fully successful
action should produce one tone and no spoken confirmation. Failed actions and
clarification questions remain spoken.

If a request does not originate from an Assist satellite, the wrapper preserves
the spoken response because it has nowhere to play the confirmation tone.

## Behavior

- Successful action with no failed targets: clear speech and invoke the tone
  script once.
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
