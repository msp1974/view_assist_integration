"""View Assist websocket handlers."""

from dataclasses import dataclass
import logging
import time
from typing import Any

import voluptuous as vol

from homeassistant.components.websocket_api import (
    ActiveConnection,
    async_register_command,
    async_response,
    event_message,
    websocket_command,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .helpers import (
    get_config_entry_by_entity_id,
    get_device_id_from_entity_id,
    get_entity_id_by_browser_id,
    get_master_config_entry,
    get_mimic_entity_id,
)
from .timers import TIMERS, VATimers
from .typed import VAEvent, VAScreenMode

_LOGGER = logging.getLogger(__name__)


@dataclass
class MockAdminUser:
    """Mock admin user for use in MockWSConnection."""

    is_admin = True


class MockWSConnection:
    """Mock a websocket connection to be able to call websocket handler functions.

    This is here for creating the View Assist dashboard
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initilise."""
        self.hass = hass
        self.user = MockAdminUser()

        self.failed_request: bool = False

    def send_result(self, id, item):
        """Receive result."""
        self.failed_request = False

    def send_error(self, id, code, msg):
        """Receive error."""
        self.failed_request = True

    def execute_ws_func(self, ws_type: str, msg: dict[str, Any]) -> bool:
        """Execute ws function."""
        if self.hass.data["websocket_api"].get(ws_type):
            try:
                handler, schema = self.hass.data["websocket_api"][ws_type]
                if schema is False:
                    handler(self.hass, self, msg)
                else:
                    handler(self.hass, self, schema(msg))
            except Exception as ex:  # noqa: BLE001
                _LOGGER.error("Error calling %s.  Error is %s", ws_type, ex)
                return False
            else:
                return True
        return False


async def async_register_websockets(hass: HomeAssistant):  # noqa: C901
    """Register websocket functions."""

    @websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/connect",
            vol.Required("browser_id"): str,
        }
    )
    @async_response
    async def handle_connect(hass: HomeAssistant, connection: ActiveConnection, msg):
        """Connect to Browser Mod and subscribe to settings updates."""
        unsubscribe = {}

        browser_id = msg["browser_id"]
        timers: VATimers = hass.data[DOMAIN]["timers"]

        def close_connection():
            _LOGGER.debug("Browser with id %s disconnected", browser_id)
            for unsub_listener in unsubscribe.values():
                unsub_listener()

        def get_entity_id(browser_id):
            mimic = False
            entity = get_entity_id_by_browser_id(hass, browser_id)

            if not entity:
                if entity := get_mimic_entity_id(hass, browser_id):
                    mimic = True
            return entity, mimic

        async def send_event(event: VAEvent):
            va_entity, mimic = get_entity_id(browser_id)
            _LOGGER.debug(
                "Sending event: %s to %s - %s", event.event_name, browser_id, va_entity
            )

            if event.event_name == "config_update" and not va_entity:
                # Browser id has been deregistered
                connection.send_message(
                    event_message(msg["id"], {"event": "unregistered", "payload": {}})
                )
                return
            if event.event_name in (
                "connection",
                "config_update",
                "registered",
                "master_config_update",
            ):
                payload = await get_data(hass, browser_id, va_entity, mimic)
            else:
                payload = event.payload

            connection.send_message(
                event_message(
                    msg["id"], {"event": event.event_name, "payload": payload}
                )
            )

        async def send_timer_update(*args):
            await send_event(
                VAEvent(
                    "timer_update",
                    timers.get_timers(
                        device_or_entity_id=va_entity, include_expired=True
                    ),
                )
            )

        async def send_register_event():
            await subscribe_listeners(is_registered=True)
            await send_event(VAEvent("registered"))

        async def subscribe_listeners(is_registered: bool = False):
            if is_registered:
                va_entity, _ = get_entity_id(browser_id)
                if va_entity is None:
                    return

                config = get_config_entry_by_entity_id(hass, va_entity)
                unsubscribe["all_devices"] = async_dispatcher_connect(
                    hass, f"{DOMAIN}_event", send_event
                )
                unsubscribe["this_device"] = async_dispatcher_connect(
                    hass, f"{DOMAIN}_{config.entry_id}_event", send_event
                )
                unsubscribe["timers"] = timers.store.add_listener(
                    va_entity, send_timer_update
                )
                if "register" in unsubscribe:
                    unsubscribe["register"]()
            else:
                unsubscribe["register"] = async_dispatcher_connect(
                    hass, f"{DOMAIN}_{browser_id}_registered", send_register_event
                )

        # Register close connection
        connection.subscriptions[browser_id] = close_connection
        connection.send_result(msg["id"])

        # Add (if va browser id) to list of known connected browsers
        if (
            str(browser_id).startswith("va-")
            and browser_id not in hass.data[DOMAIN]["va_browser_ids"]
        ):
            # Store browser id in hass.data
            hass.data[DOMAIN]["va_browser_ids"][browser_id] = browser_id

        va_entity, mimic = get_entity_id(browser_id)
        if va_entity and not mimic:
            # If registered browser id
            _LOGGER.debug(
                "Browser with id %s connected with mimic as %s. VA Entity is %s",
                browser_id,
                mimic,
                va_entity,
            )
            await send_event(VAEvent("connection"))

        elif va_entity and mimic:
            await send_event(VAEvent("connection"))

        elif not va_entity and not mimic:
            # If not registered browser id
            await subscribe_listeners(is_registered=False)
            config = get_master_config_entry(hass)
            await send_event(
                VAEvent(
                    "unregistered",
                    {"dashboard": config.runtime_data.dashboard.dashboard},
                )
            )

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
        is_mimic = False
        entity_id = get_entity_id_by_browser_id(hass, msg["browser_id"])
        if not entity_id:
            if entity_id := get_mimic_entity_id(hass):
                is_mimic = True

        connection.send_result(
            msg["id"], {"entity_id": entity_id, "mimic_device": is_mimic}
        )

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

    # Get timer by name
    @websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_timer",
            vol.Required("browser_id"): str,
            vol.Required("name"): str,
        }
    )
    @async_response
    async def websocket_get_timer_by_name(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict
    ) -> None:
        """Get entity id by browser id."""
        entity = get_entity_id_by_browser_id(hass, msg["browser_id"])
        if not entity:
            output = get_mimic_entity_id(hass)

        if entity:
            timer_name = msg["name"]
            timers: VATimers = hass.data[DOMAIN][TIMERS]

            output = timers.get_timers(device_or_entity_id=entity, name=timer_name)

        connection.send_result(msg["id"], output)

    async_register_command(hass, handle_connect)
    async_register_command(hass, websocket_get_entity_by_browser_id)
    async_register_command(hass, websocket_get_server_time)
    async_register_command(hass, websocket_get_timer_by_name)

    async def get_data(
        hass: HomeAssistant,
        browser_id: str,
        entity_id: str | None = None,
        mimic: bool = False,
    ) -> dict[str, Any]:
        output = {}

        if entity_id:
            config = get_config_entry_by_entity_id(hass, entity_id)
            if config.disabled_by:
                return output
            data = config.runtime_data
            timers: VATimers = hass.data[DOMAIN][TIMERS]
            timer_info = timers.get_timers(
                device_or_entity_id=entity_id, include_expired=True
            )
            try:
                output = {
                    "browser_id": browser_id,
                    "entity_id": entity_id,
                    "mimic_device": mimic,
                    "name": data.core.name,
                    "mic_entity_id": data.core.mic_device,
                    "mic_device_id": get_device_id_from_entity_id(
                        hass, data.core.mic_device
                    ),
                    "mediaplayer_entity_id": data.core.mediaplayer_device,
                    "mediaplayer_device_id": get_device_id_from_entity_id(
                        hass, data.core.mediaplayer_device
                    ),
                    "musicplayer_entity_id": data.core.musicplayer_device,
                    "musicplayer_device_id": get_device_id_from_entity_id(
                        hass, data.core.musicplayer_device
                    ),
                    "display_device_id": data.core.display_device,
                    "timers": timer_info,
                    "background": data.dashboard.background_settings.background,
                    "dashboard": data.dashboard.dashboard,
                    "home": data.dashboard.home,
                    "music": data.dashboard.music,
                    "intent": data.dashboard.intent,
                    "hide_sidebar": data.dashboard.display_settings.screen_mode
                    in [VAScreenMode.HIDE_HEADER_SIDEBAR, VAScreenMode.HIDE_SIDEBAR],
                    "hide_header": data.dashboard.display_settings.screen_mode
                    in [VAScreenMode.HIDE_HEADER_SIDEBAR, VAScreenMode.HIDE_HEADER],
                }
            except Exception:  # noqa: BLE001
                output = {}
        return output
