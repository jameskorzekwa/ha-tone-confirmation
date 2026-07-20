"""Constants for Tone Confirmation Conversation."""

DOMAIN = "tone_confirmation"
ASSIST_SATELLITE_DOMAIN = "assist_satellite"

CONF_TARGET_AGENT = "target_agent"
CONF_CONFIRMATION_SCRIPT = "confirmation_script"

DEFAULT_TARGET_AGENT = "conversation.google_generative_ai"

NAME = "Tone Confirmation Conversation"

TONE_FILENAME = "confirmation.wav"
TONE_URL = f"/api/{DOMAIN}/static/{TONE_FILENAME}"
TONE_WAIT_TIMEOUT = 3
