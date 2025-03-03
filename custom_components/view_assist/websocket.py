"""View Assist websocket handlers."""

import logging
import time

import voluptuous as vol

from homeassistant.components.websocket_api import (
    ActiveConnection,
    async_register_command,
    async_response,
    websocket_command,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import get_display_index, get_entity_id_by_browser_id

_LOGGER = logging.getLogger(__name__)


async def async_register_websockets(hass: HomeAssistant):
    """Register websocket functions."""

    # Get sensor entity by browser id
    @websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_entity_id",
            vol.Required("browser_id"): str,
        }
    )
    @async_response
    async def websocket_get_entity_by_browser_id(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict
    ) -> None:
        """Get entity id by browser id."""
        browser_id = msg["browser_id"]
        if entity_id := get_entity_id_by_browser_id(hass, browser_id):
            result = {"entity_id": entity_id}
            display_index = get_display_index(hass, entity_id, browser_id)
            result["display_index"] = display_index

        connection.send_result(msg["id"], result)

    # Get server datetime
    @websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_server_time_delta",
            vol.Required("epoch"): int,
        }
    )
    @async_response
    async def websocket_get_server_time(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict
    ) -> None:
        """Get entity id by browser id."""

        delta = round(time.time() * 1000) - msg["epoch"]
        connection.send_result(msg["id"], delta)

    async_register_command(hass, websocket_get_entity_by_browser_id)
    async_register_command(hass, websocket_get_server_time)
