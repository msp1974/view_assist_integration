"""Assist Satellite intents."""

from typing import override

import voluptuous as vol

from homeassistant.helpers import intent

from ...const import DOMAIN  # noqa: TID252


class VASetDNDIntentHandler(intent.IntentHandler):
    """Change View Asist do not disturb setting."""

    intent_type = "ViewAssistSetDND"
    description = """
        Changes setting for do not disturb on a View Assist satellite through voice command.
    """

    @property
    @override
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return {
            vol.Required("dnd_setting"): str,
        }

    @override
    async def async_handle(
        self, intent_obj: intent.Intent, extra_data: dict | None = None
    ) -> intent.IntentResponse:
        """Change View Assist do not disturb setting."""
        hass = intent_obj.hass
        dnd_setting = intent_obj.slots["dnd_setting"]["value"]
        entity_id = (
            extra_data["entity_id"]
            if extra_data and "entity_id" in extra_data
            else None
        )

        # Call mode change here
        await hass.services.async_call(
            DOMAIN,
            "set_state",
            {"do_not_disturb": dnd_setting},
            blocking=True,
            context=intent_obj.context,
            target={"entity_id": entity_id},
        )

        response = intent_obj.create_response()
        response.async_set_speech_slots(
            {
                "dnd_setting": intent_obj.slots["dnd_setting"]["value"],
            }
        )
        return response
