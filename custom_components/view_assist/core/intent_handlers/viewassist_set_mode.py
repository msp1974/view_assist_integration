"""Assist Satellite intents."""

from typing import override

import voluptuous as vol

from homeassistant.helpers.intent import Intent, IntentResponse

from ...const import DOMAIN  # noqa: TID252
from . import IntentOverrideHandler


class VASetModeIntentHandler(IntentOverrideHandler):
    """Change View Asist Modes."""

    intent_type = "ViewAssistSetMode"
    description = """
        Change modes on a View Assist satellite through voice command.
    """

    @property
    @override
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return {
            vol.Required("mode"): str,
        }

    @override
    async def async_handle(self, intent_obj: Intent) -> IntentResponse:
        """Change View Assist mode."""
        hass = intent_obj.hass
        mode = intent_obj.slots["mode"]["value"]
        device_info = self.get_device_info(intent_obj)
        entity_id = device_info.entity_id if device_info else None

        # Call mode change here
        await hass.services.async_call(
            DOMAIN,
            "set_state",
            {"mode": mode},
            blocking=True,
            context=intent_obj.context,
            target={"entity_id": entity_id},
        )

        response = intent_obj.create_response()
        response.async_set_speech_slots(
            {
                "mode": intent_obj.slots["mode"]["value"],
            }
        )
        return response
