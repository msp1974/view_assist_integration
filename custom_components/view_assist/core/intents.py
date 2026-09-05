"""Manage VA intents."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    DATA_KEY as INTENT_DATA_KEY,
    Intent,
    IntentHandler,
    IntentResponse,
    async_register,
    async_remove,
)
from homeassistant.helpers.start import async_at_started

from ..const import DOMAIN, ENABLE_INTENT_HOOKS, INSTALL_CUSTOM_SENTENCES  # noqa: TID252
from ..devices.navigation import NavigationManager  # noqa: TID252
from ..helpers import (  # noqa: TID252
    get_config_entry_by_entity_id,
    get_entity_attribute,
    get_entity_id_from_conversation_device_id,
)
from ..typed import VAConfigEntry  # noqa: TID252
from .intent_overrides import (
    VACancelAllTimersIntentHandler,
    VACancelTimerIntentHandler,
    VAMediaSearchAndPlayHandler,
    VAStartTimerIntentHandler,
    VATimerStatusIntentHandler,
)

CUSTOM_SENTENCE_FILES = {"timers": ["view_assist_Timers.yaml"]}

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class OverrideIntentHandler:
    """Definition of override handler for intent."""

    intent: str
    handler: Callable[[Any, Any], Awaitable[IntentResponse | None]]
    call_original: bool = False


class IntentsManager:
    """Manage VA intents."""

    @classmethod
    def get(cls, hass: HomeAssistant) -> IntentsManager | None:
        """Get the intents manager for a config entry."""
        try:
            return hass.data[DOMAIN][cls.__name__]
        except KeyError:
            return None

    def __init__(self, hass: HomeAssistant, config: VAConfigEntry) -> None:
        """Initialise."""
        self.hass = hass
        self.config = config
        self.overrides: dict[str, OverrideIntentHandler] = {}

    async def async_setup(self) -> bool:
        """Set up the Intents Manager."""

        # async_register(self.hass, VAIntentHandler())

        if ENABLE_INTENT_HOOKS:
            self.register_override_handler(VAMediaSearchAndPlayHandler())
            self.register_override_handler(VAStartTimerIntentHandler())
            self.register_override_handler(VATimerStatusIntentHandler())
            self.register_override_handler(VACancelTimerIntentHandler())
            self.register_override_handler(VACancelAllTimersIntentHandler())

            # Hook into intent handlers after Home Assistant has started
            # and hopefully all integrations have registered their intents
            async_at_started(self.hass, self.register_intent_hooks)

        # Enable custom sentences for intents
        if INSTALL_CUSTOM_SENTENCES:
            await self.register_custom_sentences()
        else:
            _LOGGER.debug(
                "Custom sentences for intents are disabled. Set INSTALL_CUSTOM_SENTENCES to True to enable"
            )
            await self.unregister_custom_sentences()

        return True

    async def async_unload(self) -> bool:
        """Unload the Intents Manager."""
        # Currently nothing to unload
        self.unregister_intent_hooks()
        await self.unregister_custom_sentences()
        async_remove(self.hass, VAIntentHandler.intent_type)
        return True

    @callback
    def register_intent_hooks(self, hass: HomeAssistant) -> None:
        """Get registered intents."""
        all_intents = hass.data.get(INTENT_DATA_KEY, {}).copy()
        for intent_type, handler in all_intents.items():
            if not isinstance(handler, IntentHookHandler):
                if intent_type in self.overrides:
                    override = self.overrides[intent_type]
                    handler = override.handler

                _LOGGER.debug("Registered intent: %s -> %s", intent_type, handler)
                async_remove(hass, intent_type)
                async_register(
                    hass,
                    IntentHookHandler(
                        real_handler=handler,
                    ),
                )

    def unregister_intent_hooks(self):
        """Unregister intent hooks and restore original handlers."""
        all_intents = self.hass.data.get(INTENT_DATA_KEY, {}).copy()
        for intent_type, handler in all_intents.items():
            if isinstance(handler, IntentHookHandler) and handler.real_handler:
                _LOGGER.debug("Restoring original intent handler for: %s", intent_type)
                async_remove(self.hass, intent_type)
                async_register(self.hass, handler.real_handler)

    def register_override_handler(
        self, handler: IntentHandler, call_original: bool = False
    ) -> Callable:
        """Register a trigger."""
        self.overrides[handler.intent_type] = OverrideIntentHandler(
            intent=handler.intent_type,
            handler=handler,
            call_original=call_original,
        )

        @callback
        def unregister_override() -> None:
            """Unregister the trigger."""
            self.overrides.pop(handler.intent_type, None)

        return unregister_override

    async def async_process_triggers(
        self, intent_obj: Intent
    ) -> tuple[IntentResponse | None, bool]:
        """Process handlers for a given intent."""
        result = None

        for intent, override in self.overrides.items():
            if intent_obj.intent_type == intent:
                device_info = DeviceInfoData(
                    self.hass, intent_obj.device_id
                ).device_info
                _LOGGER.debug(
                    "Processing override for intent: %s with handler: %s and device info: %s",
                    intent_obj.intent_type,
                    override.handler,
                    device_info,
                )
                response = await override.handler.async_handle(
                    intent_obj,
                    device_info,
                )
                _LOGGER.debug("Override result: %s", response)
                if response:
                    return response, override.call_original
        return result, True

    async def get_trigger_extra_data(self, intent_obj: Intent) -> dict[str, Any]:
        """Get extra data for the intent."""
        display = (
            get_entity_id_from_conversation_device_id(self.hass, intent_obj.device_id)
            if intent_obj.device_id
            else None
        )
        return {"display": display}

    def get_supported_language_id(self, path: Path, language: str) -> str:
        """Get the supported language id for a given language."""
        language_dir = Path(path, language)
        if language_dir.exists():
            return language

        # If language is hyphenated, try the first part (e.g., "en-US" -> "en")
        if "-" in language:
            language_dir = Path(path, language.split("-", 1)[0])
            if language_dir.exists():
                return language.split("-", 1)[0]
        return "en"

    async def register_custom_sentences(self) -> None:
        """Register custom sentences for intents."""
        va_custom_sentence_path = self.hass.config.path(
            f"custom_components/{DOMAIN}/core/custom_sentences"
        )
        language = self.get_supported_language_id(
            va_custom_sentence_path, self.hass.config.language
        )

        # Add symlinks for custom sentences to the HA custom sentences directory
        custom_sentences_dir = Path(self.hass.config.path("custom_sentences", language))
        if not custom_sentences_dir.exists():
            custom_sentences_dir.mkdir(parents=True, exist_ok=True)

        # Register sentences based on config of enhancmenet types
        # TODO: Add config items
        va_custom_sentences_dir = Path(va_custom_sentence_path, language)
        for files in CUSTOM_SENTENCE_FILES.values():
            for file in files:
                src = Path(va_custom_sentences_dir) / file
                dest = custom_sentences_dir / file
                if not dest.exists():
                    dest.symlink_to(src)

    async def unregister_custom_sentences(self) -> None:
        """Unregister custom sentences for intents."""
        # Add symlinks for custom sentences to the HA custom sentences directory

        custom_sentences_path = Path(self.hass.config.path("custom_sentences"))
        language = self.get_supported_language_id(
            custom_sentences_path, self.hass.config.language
        )
        custom_sentences_dir = Path(custom_sentences_path, language)
        if not custom_sentences_dir.exists():
            return

        # Unregister sentences based on config of enhancmenet types
        for files in CUSTOM_SENTENCE_FILES.values():
            for file in files:
                dest = custom_sentences_dir / file
                if dest.exists() and dest.is_symlink():
                    dest.unlink()


class VAIntentHandler(IntentHandler):
    """Intent handler for VA intents."""

    intent_type = "VAQuestionAnswer"
    description = "Handles question answers.  You should call this when providing an answer to an infomration request where no other tool is suitable."

    @property
    def slot_schema(self) -> dict | None:
        """Return a slot schema."""
        return {vol.Required("response"): cv.string}

    async def async_handle(self, intent_obj: Intent) -> IntentResponse:
        """Handle the intent."""
        _LOGGER.debug("VAIntentHandler invoked with intent: %s", intent_obj.slots)
        response = intent_obj.create_response()

        # TODO: Add custom handling logic here with before/after hooks, pre-defined slots, etc.

        _LOGGER.debug("Handling VAQuestionAnswer intent: %s", response.as_dict())
        return response


class IntentHookHandler(IntentHandler):
    """Base class for intent handlers with custom hooks."""

    def __init__(
        self,
        real_handler: IntentHandler,
    ) -> None:
        """Initialize the intent handler."""
        self.intent_type = real_handler.intent_type
        self.platforms = real_handler.platforms
        self.description = (
            real_handler.description or f"Hooked handler for {real_handler.intent_type}"
        )
        self.real_handler = real_handler

    def intent_to_dict(self, intent_obj: Intent) -> dict[str, Any]:
        """Convert the intent object to a dictionary."""
        return {
            "platform": intent_obj.platform,
            "intent_type": intent_obj.intent_type,
            "slots": intent_obj.slots,
            "text_input": intent_obj.text_input,
            "context": intent_obj.context.as_dict(),
            "language": intent_obj.language,
            "assistant": intent_obj.assistant,
            "device_id": intent_obj.device_id,
            "satellite_id": intent_obj.satellite_id,
            "conversation_agent_id": intent_obj.conversation_agent_id,
        }

    async def async_handle(self, intent_obj: Intent) -> IntentResponse:
        """Handle the intent with custom logic."""
        _LOGGER.debug(
            "%s invoked with intent: %s",
            self.__class__.__name__,
            self.intent_to_dict(intent_obj),
        )

        # Custom handling logic can be added here
        if im := IntentsManager.get(intent_obj.hass):
            response, call_original = await im.async_process_triggers(intent_obj)

        # Call original handler
        if not response or call_original:
            response = await self.real_handler.async_handle(intent_obj)

        _LOGGER.debug("%s response: %s", self.__class__.__name__, response)

        # Get config entry for device id
        config_entry = None
        if intent_obj.device_id:
            if entiy_id := get_entity_id_from_conversation_device_id(
                intent_obj.hass, intent_obj.device_id
            ):
                config_entry = get_config_entry_by_entity_id(intent_obj.hass, entiy_id)

        if config_entry:
            nm = NavigationManager.get(intent_obj.hass, config_entry)
            nm.handle_intent_navigation(intent_obj.intent_type)

        return response


class DeviceInfoData:
    """Class to hold device information."""

    def __init__(self, hass: HomeAssistant, conversation_device_id: str) -> None:
        """Initialize the DeviceInfo class."""
        self.hass = hass
        self.conversation_device_id = conversation_device_id

    @property
    def entity_id(self) -> str | None:
        """Get the entity id for the device."""
        return get_entity_id_from_conversation_device_id(
            self.hass, self.conversation_device_id
        )

    @property
    def entity_name(self) -> str | None:
        """Get the entity name for the device."""
        return (
            get_entity_attribute(self.hass, self.entity_id, "friendly_name")
            if self.entity_id
            else None
        )

    @property
    def media_player(self) -> str | None:
        """Get the media player entity id for the device."""
        return (
            get_entity_attribute(self.hass, self.entity_id, "musicplayer_device")
            if self.entity_id
            else None
        )

    @property
    def device_info(self) -> dict[str, Any]:
        """Get device information as a dictionary."""
        return {
            "name": self.entity_name,
            "media_player": self.media_player,
            "entity_id": self.entity_id,
        }
