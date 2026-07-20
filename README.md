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

## Installation

Install this repository as a HACS custom integration, then add:

```yaml
tone_confirmation:
  target_agent: conversation.google_generative_ai
  confirmation_script: script.voice_command_acknowledge
```

Restart Home Assistant and select
`conversation.tone_confirmation_conversation` as the conversation engine for
the desired Assist pipeline.

The defaults shown above can be omitted. `target_agent` can be any
ConversationEntity-based agent. The confirmation script is called with the
satellite that originated the request:

```yaml
voice_command_acknowledge:
  mode: parallel
  fields:
    satellite_id:
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
