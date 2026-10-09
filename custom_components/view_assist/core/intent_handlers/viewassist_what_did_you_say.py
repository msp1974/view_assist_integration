"""Intent handler that repeats the last response spoken by the calling device."""

from typing import override

from homeassistant.helpers import intent

from ...devices.status import StatusManager  # noqa: TID252
from ...helpers import (  # noqa: TID252
    get_config_entry_by_entity_id,
    get_entity_id_from_conversation_device_id,
)
from . import IntentOverrideHandler, IntentOverrideResponse

INTENT_WHAT_DID_YOU_SAY = "VAWhatDidYouSay"


class VAWhatDidYouSayHandler(IntentOverrideHandler):
    """Repeat the last response spoken by the calling device."""

    intent_type = INTENT_WHAT_DID_YOU_SAY
    description = "Repeats the last thing the assistant said on this device."

    @property
    @override
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return None

    @override
    async def async_handle(
        self, intent_obj: intent.Intent, extra_data: dict | None = None
    ) -> IntentOverrideResponse:
        """Handle the intent."""
        hass = intent_obj.hass

        # Find the View Assist device that made the request:
        # satellite device id -> VA sensor entity -> VA config entry -> StatusManager
        last_response = None
        if intent_obj.device_id:
            sensor_entity_id = get_entity_id_from_conversation_device_id(
                hass, intent_obj.device_id
            )
            if sensor_entity_id:
                entry = get_config_entry_by_entity_id(hass, sensor_entity_id)
                if entry:
                    sm = StatusManager.get(hass, entry)
                    if sm:
                        last_response = sm.last_response

        response = self.create_override_handler_response(intent_obj)
        response.response_type = intent.IntentResponseType.QUERY_ANSWER

        speech_text = last_response
        if speech_text:
            word_count = len(speech_text.split())
            message_font_size = ["10vw", "8vw", "6vw", "4vw"][min(word_count // 6, 3)]

            response.async_set_speech_slots({"last_response": speech_text})

            response.async_set_view_data(
                {
                    "title": "Last Response",
                    "message": speech_text,
                    "message_font_size": message_font_size,
                }
            )

        return response