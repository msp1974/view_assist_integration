"""Handles entity listeners."""

import asyncio
from asyncio import Task
import logging

from homeassistant.const import CONF_MODE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.config_validation import ensure_list
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    BROWSERMOD_DOMAIN,
    CONF_DO_NOT_DISTURB,
    DOMAIN,
    REMOTE_ASSIST_DISPLAY_DOMAIN,
    VA_ATTRIBUTE_UPDATE_EVENT,
    VAConfigEntry,
    VADisplayType,
    VAMode,
)
from .helpers import (
    get_device_name_from_id,
    get_display_type_from_browser_id,
    get_random_image,
    get_revert_settings_for_mode,
)

_LOGGER = logging.getLogger(__name__)


class EntityListeners:
    """Class to manage entity monitors."""

    def __init__(self, hass: HomeAssistant, config_entry: VAConfigEntry) -> None:
        """Initialise."""
        self.hass = hass
        self.config_entry = config_entry
        self.browser_or_device_id: str | None = None

        self.revert_view_task: Task | None = None
        self.cycle_view_task: Task | None = None

        # Add microphone mute switch listener
        mic_device = config_entry.runtime_data.mic_device
        mic_type = config_entry.runtime_data.mic_type
        mute_switch = self.get_mute_switch(mic_device, mic_type)

        # Add browser navigate service listener
        config_entry.async_on_unload(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{config_entry.entry_id}_browser_navigate",
                self._handle_browser_navigate_service_call,
            )
        )

        # Add listener to set_state service to call sensor_attribute_changed
        hass.bus.async_listen(
            VA_ATTRIBUTE_UPDATE_EVENT.format(config_entry.entry_id),
            self.async_set_state_changed_attribute,
        )

        # Add mic mute switch listener
        config_entry.async_on_unload(
            async_track_state_change_event(hass, mute_switch, self._async_on_mic_change)
        )

        # Add media player mute listener
        mediaplayer_device = self.config_entry.data["mediaplayer_device"]

        config_entry.async_on_unload(
            async_track_state_change_event(
                hass, mediaplayer_device, self._async_on_mediaplayer_device_mute_change
            )
        )

    async def _display_revert_delay(
        self, path: str, display_index: int = -1, timeout: int = 0
    ):
        """Display revert function.  To be called from task."""
        if timeout:
            await asyncio.sleep(timeout)
            await self.async_browser_navigate(
                path, display_index=display_index, is_revert_action=True
            )

    def _cancel_display_revert_task(self):
        """Cancel any existing revert timer task."""
        if self.revert_view_task and not self.revert_view_task.cancelled():
            _LOGGER.info("Cancelled revert task")
            self.revert_view_task.cancel()
            self.revert_view_task = None

    async def _handle_browser_navigate_service_call(self, args):
        """Navigate browser to defined view.

        Optionally revert to another view after timeout.
        """
        _LOGGER.debug("NAVIGATE ARGS: %s", args)
        path = args["path"]
        display_index = args.get("display_index")
        await self.async_browser_navigate(path, display_index)

    async def async_browser_navigate(
        self,
        path: str,
        display_index: int = -1,
        is_revert_action: bool = False,
    ):
        """Navigate browser to defined view.

        Optionally only navigate 1 display device from list with display index
        Optionally revert to another view after timeout.
        """

        _LOGGER.debug(
            "Navigate called for %s, index %s to %s",
            self.config_entry.runtime_data.name,
            display_index,
            path,
        )

        # If new navigate before revert timer has expired, cancel revert timer.
        if not is_revert_action:
            self._cancel_display_revert_task()

        # Handle list of display devices
        display_devices = ensure_list(self.config_entry.runtime_data.display_device)

        # If display index is set
        if display_index != -1:
            try:
                display_devices = [display_devices[display_index]]
                _LOGGER.debug("Navigation limited to display index %s", display_index)
            except IndexError:
                pass

        # Do navigation and set revert if needed
        for index, display_device in enumerate(display_devices):
            browser_id = get_device_name_from_id(self.hass, display_device)
            display_type = get_display_type_from_browser_id(self.hass, browser_id)

            _LOGGER.debug(
                "Navigating: %s-%s, browser_id: %s, path: %s, display_type: %s, mode: %s",
                self.config_entry.runtime_data.name,
                index,
                browser_id,
                path,
                display_type,
                self.config_entry.runtime_data.mode,
            )

            # If using BrowserMod
            if display_type == VADisplayType.BROWSERMOD:
                await self.hass.services.async_call(
                    BROWSERMOD_DOMAIN,
                    "navigate",
                    {"browser_id": browser_id, "path": path},
                )

            # If using RAD
            elif display_type == VADisplayType.REMOTE_ASSIST_DISPLAY:
                device_reg = dr.async_get(self.hass)
                if device := device_reg.async_get_device(
                    identifiers={(REMOTE_ASSIST_DISPLAY_DOMAIN, browser_id)}
                ):
                    await self.hass.services.async_call(
                        REMOTE_ASSIST_DISPLAY_DOMAIN,
                        "navigate",
                        {"target": device.id, "path": path},
                    )

        # If this was a revert action, end here
        if is_revert_action:
            return

        # Find required revert action
        revert, revert_view = get_revert_settings_for_mode(
            self.config_entry.runtime_data.mode
        )
        revert_path = (
            getattr(self.config_entry.runtime_data, revert_view)
            if revert_view
            else None
        )

        # Set revert action if required
        if revert and path != revert_path:
            timeout = self.config_entry.runtime_data.view_timeout
            _LOGGER.debug("Adding revert to %s in %ss", revert_path, timeout)
            self.revert_view_task = self.hass.async_create_task(
                self._display_revert_delay(revert_path, display_index, timeout)
            )

    async def async_cycle_display_view(self, views: list[str]):
        """Cycle display."""

        view_index = 0
        _LOGGER.debug("Cycle display started")
        while self.config_entry.runtime_data.mode == VAMode.CYCLE:
            view_index = view_index % len(views)
            _LOGGER.debug("Cycling to view: %s", views[view_index])
            await self.async_browser_navigate(
                f"{self.config_entry.runtime_data.dashboard}/{views[view_index]}",
            )
            view_index += 1
            await asyncio.sleep(self.config_entry.runtime_data.view_timeout)

    def update_entity(self):
        """Dispatch message that entity is listening for to update."""
        async_dispatcher_send(
            self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update"
        )

    # ---------------------------------------------------------------------------------------
    # Actions for monitoring changes to external entities
    # ---------------------------------------------------------------------------------------

    @callback
    def _async_on_mic_change(self, event: Event[EventStateChangedData]) -> None:
        mic_mute_new_state = event.data["new_state"].state

        # If not change to mic mute state, exit function
        if (
            not event.data.get("old_state")
            or event.data["old_state"].state == mic_mute_new_state
        ):
            return

        _LOGGER.info("MIC MUTE: %s", mic_mute_new_state)
        status_icons = self.config_entry.runtime_data.status_icons.copy()

        if mic_mute_new_state == "on" and "mic" not in status_icons:
            status_icons.append("mic")
        elif mic_mute_new_state == "off" and "mic" in status_icons:
            status_icons.remove("mic")

        self.config_entry.runtime_data.status_icons = status_icons
        self.update_entity()

    @callback
    def _async_on_mediaplayer_device_mute_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        mp_mute_new_state = event.data["new_state"].attributes.get(
            "is_volume_muted", False
        )

        # If not change to mute state, exit function
        if (
            not event.data.get("old_state")
            or event.data["old_state"].attributes.get("is_volume_muted")
            == mp_mute_new_state
        ):
            return

        _LOGGER.info("MP MUTE: %s", mp_mute_new_state)
        status_icons = (
            self.config_entry.runtime_data.status_icons.copy()
            if self.config_entry.runtime_data.status_icons
            else []
        )

        if mp_mute_new_state and "mediaplayer" not in status_icons:
            status_icons.append("mediaplayer")
        elif not mp_mute_new_state and "mediaplayer" in status_icons:
            status_icons.remove("mediaplayer")

        self.config_entry.runtime_data.status_icons = status_icons
        self.update_entity()

    def get_mute_switch(self, target_device: str, mic_type: str):
        """Get mute switch."""

        if mic_type == "Stream Assist":
            return target_device.replace("sensor", "switch").replace("_stt", "_mic")
        if mic_type == "HassMic":
            return target_device.replace("sensor", "switch").replace(
                "simple_state", "microphone"
            )
        if mic_type == "Home Assistant Voice Satellite":
            return target_device.replace("assist_satellite", "switch") + "_mute"

        return None

    # ---------------------------------------------------------------------------------------
    # Actions for attributes changed via the set_state service
    # ---------------------------------------------------------------------------------------

    async def async_set_state_changed_attribute(self, event: Event):
        """Call when a sensor attribute is changed by the set_state service."""

        # This function is only called if the new_value != old_value so no need to test
        # for that.  If you are here, an attribute has changed.
        attribute = event.data.get("attribute")
        old_value = event.data.get("old_value")
        new_value = event.data.get("new_value")

        _LOGGER.info(
            "ATTR CHANGED: %s - old value: %s, new value: %s",
            attribute,
            old_value,
            new_value,
        )

        if attribute == CONF_DO_NOT_DISTURB:
            await self._async_on_dnd_device_state_change(event)

        if attribute == CONF_MODE:
            await self._async_on_mode_state_change(event)

    async def _async_on_dnd_device_state_change(self, event: Event) -> None:
        """Set dnd status icon."""

        # This is called from our set_service event listener and therefore event data is
        # slightly different.  See set_state_changed_attribute above
        dnd_new_state = event.data["new_value"]

        _LOGGER.info("DND STATE: %s", dnd_new_state)
        status_icons = self.config_entry.runtime_data.status_icons.copy()
        if dnd_new_state and "dnd" not in status_icons:
            status_icons.append("dnd")
        elif not dnd_new_state and "dnd" in status_icons:
            status_icons.remove("dnd")

        self.config_entry.runtime_data.status_icons = status_icons
        self.update_entity()

    async def _async_on_mode_state_change(self, event: Event) -> None:
        """Set mode status icon."""

        new_mode = event.data["new_value"]

        _LOGGER.info("MODE STATE: %s", new_mode)
        status_icons = self.config_entry.runtime_data.status_icons.copy()

        modes = [VAMode.HOLD, VAMode.CYCLE]

        # Remove all mode icons
        for mode in modes:
            if mode in status_icons:
                status_icons.remove(mode)

        # Now add back any you want
        if new_mode in modes and new_mode not in status_icons:
            status_icons.append(new_mode)

        self.config_entry.runtime_data.status_icons = status_icons
        self.update_entity()

        if new_mode != VAMode.CYCLE:
            if self.cycle_view_task and not self.cycle_view_task.cancelled():
                self.cycle_view_task.cancel()
                _LOGGER.info("Cycle display terminated")

        if new_mode == VAMode.NORMAL:
            # Add navigate to default view
            await self.async_browser_navigate(self.config_entry.runtime_data.home)
            _LOGGER.info("NAVIGATE TO: %s", new_mode)

        elif new_mode == VAMode.MUSIC:
            # Add navigate to music view
            await self.async_browser_navigate(self.config_entry.runtime_data.music)

            # --------------------------------------------
            # Service call option
            # --------------------------------------------
            # await self.hass.services.async_call(
            #     "switch",
            #     "turn_on",
            #     {
            #         "entity_id": "switch.android_satellite_viewassist_office_wyoming_mute"
            #     },
            # )

            _LOGGER.info("NAVIGATE TO: %s", new_mode)

        elif new_mode == VAMode.CYCLE:
            # Add start cycle mode
            # Pull cycle_mode attribute
            self.cycle_view_task = self.hass.async_create_task(
                self.async_cycle_display_view(
                    views=["music", "info", "weather", "clock"]
                )
            )
            _LOGGER.info("START MODE: %s", new_mode)
        elif new_mode == VAMode.HOLD:
            # Hold mode, so cancel any revert timer
            self._cancel_display_revert_task()
        elif new_mode == VAMode.ROTATE:
            #
            # Test image rotate service
            #
            image_path = await self.hass.async_add_executor_job(
                get_random_image,
                self.hass,
                "/config/www/viewassist/backgrounds",
                "local",
            )
            _LOGGER.info("START MODE: %s %s", new_mode, image_path)
