"""Integration classes and constants."""

from enum import StrEnum
from typing import Any

from homeassistant.config_entries import ConfigEntry

DOMAIN = "view_assist"
GITHUB_REPO = "dinki/View-Assist"
GITHUB_BRANCH = "main"
GITHUB_PATH = "View Assist dashboard and views"
VIEWS_DIR = "views"
DASHBOARD_DIR = "dashboard"

DASHBOARD_NAME = "View Assist"
DEFAULT_VIEWS = ["clock", "weather", "alarm", "music", "info", "intent"]

BROWSERMOD_DOMAIN = "browser_mod"
REMOTE_ASSIST_DISPLAY_DOMAIN = "remote_assist_display"
VA_SUB_DIRS = ["audio", "images"]
URL_BASE = "/view_assist"
JSMODULES = [
    {
        "name": "View Assist Helper",
        "filename": "view_assist.js",
        "version": "1.0.2",
    },
]


type VAConfigEntry = ConfigEntry[RuntimeData]


class VAMode(StrEnum):
    """View Assist modes."""

    NORMAL = "normal"
    MUSIC = "music"
    CYCLE = "cycle"
    HOLD = "hold"
    NIGHT = "night"
    ROTATE = "rotate"


VAMODE_REVERTS = {
    VAMode.NORMAL: {"revert": True, "view": "home"},
    VAMode.MUSIC: {"revert": True, "view": "music"},
    VAMode.CYCLE: {"revert": False},
    VAMode.HOLD: {"revert": False},
    VAMode.NIGHT: {"revert": True, "view": "home"},
}


class VAType(StrEnum):
    """Sensor type enum."""

    VIEW_AUDIO = "view_audio"
    AUDIO_ONLY = "audio_only"


class VAAssistPrompt(StrEnum):
    """Assist prompt types enum."""

    BLUR_POPUP = "blur pop up"
    FLASHING_BAR = "flashing bar"


class VAIconSizes(StrEnum):
    """Icon size options enum."""

    SMALL = "6vw"
    MEDIUM = "7vw"
    LARGE = "8vw"


class VAMicType(StrEnum):
    """Mic types."""

    HA_VOICE_SATELLITE = "Home Assistant Voice Satellite"
    HASS_MIC = "HassMic"
    STREAM_ASSIST = "Stream Assist"


class VADisplayType(StrEnum):
    """Display types."""

    BROWSERMOD = "BrowserMod"
    REMOTE_ASSIST_DISPLAY = "Remote Assist Display"


# Config keys
CONF_MIC_DEVICE = "mic_device"
CONF_MEDIAPLAYER_DEVICE = "mediaplayer_device"
CONF_MUSICPLAYER_DEVICE = "musicplayer_device"
CONF_DISPLAY_DEVICE = "display_device"
CONF_DASHBOARD = "dashboard"
CONF_HOME = "home"
CONF_INTENT = "intent"
CONF_MUSIC = "music"
CONF_BACKGROUND = "background"
CONF_ASSIST_PROMPT = "assist_prompt"
CONF_STATUS_ICON_SIZE = "status_icons_size"
CONF_FONT_STYLE = "font_style"
CONF_STATUS_ICONS = "status_icons"
CONF_USE_24H_TIME = "use_24_hour_time"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_MIC_TYPE = "mic_type"
CONF_VIEW_TIMEOUT = "view_timeout"
CONF_DO_NOT_DISTURB = "do_not_disturb"
CONF_USE_ANNOUNCE = "use_announce"
CONF_MIC_UNMUTE = "micunmute"

# Config default values
DEFAULT_NAME = "View Assist"
DEFAULT_TYPE = VAType.VIEW_AUDIO
DEFAULT_DASHBOARD = "/view-assist"
DEFAULT_VIEW_HOME = "/view-assist/clock"
DEFAULT_VIEW_MUSIC = "/view-assist/music"
DEFAULT_VIEW_INTENT = "/view-assist/intent"
DEFAULT_VIEW_BACKGROUND = "/local/viewassist/backgrounds/mybackground.jpg"
DEFAULT_ASSIST_PROMPT = VAAssistPrompt.BLUR_POPUP
DEFAULT_STATUS_ICON_SIZE = VAIconSizes.LARGE
DEFAULT_FONT_STYLE = "Roboto"
DEFAULT_STATUS_ICONS = []
DEFAULT_USE_24H_TIME = False
DEFAULT_WEATHER_ENITITY = "weather.home"
DEFAULT_MIC_TYPE = VAMicType.HA_VOICE_SATELLITE
DEFAULT_MODE = "normal"
DEFAULT_VIEW_TIMEOUT = 20
DEFAULT_DND = False
DEFAULT_USE_ANNOUNCE = True
DEFAULT_MIC_UNMUTE = False

# Service attributes
ATTR_EVENT_NAME = "event_name"
ATTR_EVENT_DATA = "event_data"
ATTR_PATH = "path"
ATTR_DOWNLOAD_IF_MISSING = "download_if_missing"
ATTR_FORCE_DOWNLOAD = "force_download"
ATTR_OVERWRITE = "overwrite"
ATTR_EXTRA = "extra"
ATTR_TYPE = "type"
ATTR_TIMER_ID = "timer_id"
ATTR_REMOVE_ALL = "remove_all"
ATTR_INCLUDE_EXPIRED = "include_expired"
ATTR_MEDIA_FILE = "media_file"
ATTR_RESUME_MEDIA = "resume_media"
ATTR_MAX_REPEATS = "max_repeats"
ATTR_DISPLAY_INDEX = "display_index"

VA_ATTRIBUTE_UPDATE_EVENT = "va_attr_update_event_{}"


class RuntimeData:
    """Class to hold your data."""

    def __init__(self) -> None:
        """Initialise runtime data."""

        # Default config
        self.type: VAType | None = None
        self.name: str = ""
        self.mic_device: str = ""
        self.mediaplayer_device: str = ""
        self.musicplayer_device: str = ""
        self.display_device: str = ""
        self.dev_mimic: bool = False

        # Dashboard options
        self.dashboard: str = DEFAULT_DASHBOARD
        self.home: str = DEFAULT_VIEW_HOME
        self.music: str = DEFAULT_VIEW_MUSIC
        self.intent: str = DEFAULT_VIEW_INTENT
        self.background: str = DEFAULT_VIEW_BACKGROUND
        self.assist_prompt: VAAssistPrompt = DEFAULT_ASSIST_PROMPT
        self.status_icons_size: VAIconSizes = DEFAULT_STATUS_ICON_SIZE
        self.font_style: str = DEFAULT_FONT_STYLE
        self.status_icons: list[str] = DEFAULT_STATUS_ICONS
        self.use_24_hour_time: bool = DEFAULT_USE_24H_TIME

        # Default options
        self.weather_entity: str = DEFAULT_WEATHER_ENITITY
        self.mic_type: VAMicType = DEFAULT_MIC_TYPE
        self.mode: str = DEFAULT_MODE
        self.view_timeout: int = DEFAULT_VIEW_TIMEOUT
        self.do_not_disturb: bool = DEFAULT_DND
        self.use_announce: bool = DEFAULT_USE_ANNOUNCE
        self.mic_unmute: bool = DEFAULT_MIC_UNMUTE

        # Extra data for holding key/value pairs passed in by set_state service call
        self.extra_data: dict[str, Any] = {}
