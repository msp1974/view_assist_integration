"""Intent handlers that override or add to core HA intent handlers."""

from typing import Any, override

from homeassistant.core import State, callback
from homeassistant.helpers.intent import (
    Intent,
    IntentHandler,
    IntentResponse,
    IntentResponseErrorCode,
    IntentResponseTarget,
    IntentResponseType,
)


class IntentOverrideHandler(IntentHandler):
    """Handler to override existing intent handlers."""

    @override
    async def async_handle(
        self, intent_obj: Intent, extra_data: dict | None = None
    ) -> IntentOverrideResponse:
        raise NotImplementedError

    def create_override_handler_response(
        self, intent_obj: Intent
    ) -> IntentOverrideResponse:
        """Create an intent override response."""
        response = intent_obj.create_response()
        return IntentOverrideResponse(response)


class IntentOverrideResponse:
    """Response class for intent overrides."""

    def __init__(
        self,
        response: IntentResponse,
    ) -> None:
        """Initialize an IntentResponse."""
        self.response = response
        self.view_data: dict[str, Any] = {}

    @callback
    def async_set_speech(
        self,
        speech: str,
        speech_type: str = "plain",
        extra_data: Any | None = None,
    ) -> None:
        """Set speech response."""
        self.response.speech[speech_type] = {
            "speech": speech,
            "extra_data": extra_data,
        }

    @callback
    def async_set_reprompt(
        self,
        speech: str,
        speech_type: str = "plain",
        extra_data: Any | None = None,
    ) -> None:
        """Set reprompt response."""
        self.response.reprompt[speech_type] = {
            "reprompt": speech,
            "extra_data": extra_data,
        }

    @callback
    def async_set_card(
        self, title: str, content: str, card_type: str = "simple"
    ) -> None:
        """Set card response."""
        self.response.card[card_type] = {"title": title, "content": content}

    @callback
    def async_set_error(self, code: IntentResponseErrorCode, message: str) -> None:
        """Set response error."""
        self.response.response_type = IntentResponseType.ERROR
        self.response.error_code = code

        # Speak error message
        self.async_set_speech(message)

    @callback
    def async_set_results(
        self,
        success_results: list[IntentResponseTarget],
        failed_results: list[IntentResponseTarget] | None = None,
    ) -> None:
        """Set response results."""
        self.response.success_results = success_results
        self.response.failed_results = (
            failed_results if failed_results is not None else []
        )

    @callback
    def async_set_states(
        self, matched_states: list[State], unmatched_states: list[State] | None = None
    ) -> None:
        """Set matched/unmatched entity states during intent handling."""
        self.response.matched_states = matched_states
        self.response.unmatched_states = unmatched_states or []

    @callback
    def async_set_speech_slots(self, speech_slots: dict[str, Any]) -> None:
        """Set slots that will be used in the response template of the default agent."""
        self.response.speech_slots = speech_slots

    @callback
    def async_set_view_data(self, view_data: dict[str, Any] | None) -> None:
        """Set the view data associated with this response."""
        self.view_data = view_data
