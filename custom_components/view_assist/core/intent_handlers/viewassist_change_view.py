"""Assist Satellite intents."""

from typing import override

import voluptuous as vol

from homeassistant.helpers import intent

from ...const import DOMAIN  # noqa: TID252

from ...helpers import get_config_entry_by_entity_id
from ...typed import VAConfigEntry


class VASetChangeViewIntentHandler(intent.IntentHandler):
    """Change View Assist View."""

    intent_type = "ViewAssistChangeView"
    description = """
        Changes the displayed view on a View Assist satellite through voice command.
    """

    @property
    @override
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return {
            vol.Required("view"): str,
        }

    @override
    async def async_handle(
        self, intent_obj: intent.Intent, extra_data: dict | None = None
    ) -> intent.IntentResponse:
        """Change View Assist view."""
        hass = intent_obj.hass
        view = intent_obj.slots["view"]["value"]
        
        entity_id = (
            extra_data["entity_id"]
            if extra_data and "entity_id" in extra_data
            else None
        )

        # Retrieve the dashboard path now that hass and entity_id are available
        entry: VAConfigEntry = get_config_entry_by_entity_id(hass, entity_id)
        dashboard_path = entry.runtime_data.dashboard.dashboard

        await hass.services.async_call(
            DOMAIN,
            "navigate",
            {
                "device": entity_id,
                "path": f"{dashboard_path}/{view}"
            },
            blocking=True,
            context=intent_obj.context,
        )

        response = intent_obj.create_response()
        response.async_set_speech_slots(
            {
                "view": view,
            }
        )
        return response