# Right now this doesn't do much.  It will be expanded to set the calendar attribute when I figure
# out how to do that

"""Assist Satellite intents."""

from typing import override

import voluptuous as vol

from homeassistant.helpers import intent

from ...const import DOMAIN  # noqa: TID252

from ...helpers import get_config_entry_by_entity_id
from ...typed import VAConfigEntry


class VASShowCalendarIntentHandler(intent.IntentHandler):
    """Change View Assist View."""

    intent_type = "ViewAssistShowCalendar"
    description = """
        Shows the user's calendar on a View Assist satellite through voice command.
    """

    @property
    @override
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return {
            vol.Optional("calendar"): str,
        }

    @override
    async def async_handle(
        self, intent_obj: intent.Intent, extra_data: dict | None = None
    ) -> intent.IntentResponse:
        """Change View Assist mode."""
        hass = intent_obj.hass

        # Safely extract the optional slot with a fallback
        calendar_slot = intent_obj.slots.get("calendar")
        calendar = calendar_slot["value"] if calendar_slot else "calendar.local_calendar"

        entity_id = (
            extra_data["entity_id"]
            if extra_data and "entity_id" in extra_data
            else None
        )

        await hass.services.async_call(
            DOMAIN,
            "set_state",
            {"calendar_list": [calendar]},
            blocking=True,
            context=intent_obj.context,
            target={"entity_id": entity_id},
        )

        response = intent_obj.create_response()
        response.async_set_speech_slots(
            {
                "calendar": calendar,
            }
        )
        return response