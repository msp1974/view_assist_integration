"""Intent handlers to override core HA handlers."""

from .hass_cancel_timer import (
    VACancelAllTimersIntentHandler,
    VACancelTimerIntentHandler,
)
from .hass_media_search_and_play import VAMediaSearchAndPlayHandler
from .hass_start_timer import VAStartTimerIntentHandler
from .hass_timer_status import VATimerStatusIntentHandler

all = [
    VAMediaSearchAndPlayHandler,
    VAStartTimerIntentHandler,
    VATimerStatusIntentHandler,
    VACancelTimerIntentHandler,
    VACancelAllTimersIntentHandler,
]
