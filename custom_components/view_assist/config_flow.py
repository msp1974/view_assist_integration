"""Config flow handler."""

import voluptuous as vol

from homeassistant.components.assist_satellite import DOMAIN as ASSIST_SAT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIAPLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.weather import DOMAIN as WEATHER_DOMAIN
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_MODE, CONF_NAME, CONF_TYPE
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BROWSERMOD_DOMAIN,
    CONF_ASSIST_PROMPT,
    CONF_BACKGROUND,
    CONF_DASHBOARD,
    CONF_DISPLAY_DEVICE,
    CONF_DO_NOT_DISTURB,
    CONF_FONT_STYLE,
    CONF_HOME,
    CONF_INTENT,
    CONF_MEDIAPLAYER_DEVICE,
    CONF_MIC_DEVICE,
    CONF_MIC_TYPE,
    CONF_MIC_UNMUTE,
    CONF_MUSIC,
    CONF_MUSICPLAYER_DEVICE,
    CONF_STATUS_ICON_SIZE,
    CONF_STATUS_ICONS,
    CONF_USE_24H_TIME,
    CONF_USE_ANNOUNCE,
    CONF_VIEW_TIMEOUT,
    CONF_WEATHER_ENTITY,
    DEFAULT_ASSIST_PROMPT,
    DEFAULT_DASHBOARD,
    DEFAULT_DND,
    DEFAULT_FONT_STYLE,
    DEFAULT_MIC_TYPE,
    DEFAULT_MIC_UNMUTE,
    DEFAULT_MODE,
    DEFAULT_NAME,
    DEFAULT_STATUS_ICON_SIZE,
    DEFAULT_STATUS_ICONS,
    DEFAULT_TYPE,
    DEFAULT_USE_24H_TIME,
    DEFAULT_USE_ANNOUNCE,
    DEFAULT_VIEW_BACKGROUND,
    DEFAULT_VIEW_HOME,
    DEFAULT_VIEW_INTENT,
    DEFAULT_VIEW_MUSIC,
    DEFAULT_VIEW_TIMEOUT,
    DEFAULT_WEATHER_ENITITY,
    DOMAIN,
    REMOTE_ASSIST_DISPLAY_DOMAIN,
    VAAssistPrompt,
    VAIconSizes,
    VAMicType,
    VAType,
)

BASE_SCHEMA = {
    vol.Required(CONF_NAME): str,
    vol.Required(CONF_MIC_DEVICE): EntitySelector(
        EntitySelectorConfig(domain=[SENSOR_DOMAIN, ASSIST_SAT_DOMAIN])
    ),
    vol.Required(CONF_MEDIAPLAYER_DEVICE): EntitySelector(
        EntitySelectorConfig(domain=MEDIAPLAYER_DOMAIN)
    ),
    vol.Required(CONF_MUSICPLAYER_DEVICE): EntitySelector(
        EntitySelectorConfig(domain=MEDIAPLAYER_DOMAIN)
    ),
}

DISPLAY_SCHEMA = {
    vol.Required(CONF_DISPLAY_DEVICE): DeviceSelector(
        DeviceSelectorConfig(
            multiple=True,
            filter=[
                EntityFilterSelectorConfig(integration=BROWSERMOD_DOMAIN),
                EntityFilterSelectorConfig(
                    integration=REMOTE_ASSIST_DISPLAY_DOMAIN,
                ),
            ],
        )
    ),
}


class ViewAssistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for View Assist."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler.

        Remove this method and the ExampleOptionsFlowHandler class
        if you do not want any options for your integration.
        """
        return ViewAssistOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialise."""
        super().__init__()
        self.type = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            self.type = user_input[CONF_TYPE]
            return await self.async_step_options()

        # Show the initial form to select the type with descriptive text
        return self.async_show_form(
            step_id="user",
            last_step=False,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TYPE, default=DEFAULT_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            translation_key="type_selector",
                            options=[e.value for e in VAType],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_options(self, user_input=None):
        """Handle the options step."""
        if user_input is not None:
            # Include the type in the data to save in the config entry
            user_input[CONF_TYPE] = self.type
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input
            )

        # Define the schema based on the selected type
        if self.type == VAType.VIEW_AUDIO:
            data_schema = vol.Schema({**BASE_SCHEMA, **DISPLAY_SCHEMA})
        else:  # audio_only
            data_schema = vol.Schema(BASE_SCHEMA)

        # Show the form for the selected type
        return self.async_show_form(step_id="options", data_schema=data_schema)


class ViewAssistOptionsFlowHandler(OptionsFlow):
    """Handles the options flow.

    Here we use an initial menu to select different options forms,
    and show how to use api data to populate a selector.
    """

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        self.va_type = self.config_entry.data[CONF_TYPE]

        # Display an options menu if display device
        # Display reconfigure form if audio only

        # Also need to be in strings.json and translation files.

        if self.va_type == VAType.VIEW_AUDIO:
            return self.async_show_menu(
                step_id="init",
                menu_options=["main_config", "dashboard_options", "default_options"],
            )

        return await self.async_step_main_config()

    async def async_step_main_config(self, user_input=None):
        """Handle main config flow."""

        if user_input is not None:
            # This is just updating the core config so update config_entry.data
            user_input[CONF_TYPE] = self.va_type
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input
            )
            return self.async_create_entry(data=None)
        # Define the schema based on the selected type
        BASE_OPTIONS = {
            vol.Required(CONF_NAME, default=self.config_entry.data[CONF_NAME]): str,
            vol.Required(
                CONF_MIC_DEVICE, default=self.config_entry.data[CONF_MIC_DEVICE]
            ): EntitySelector(
                EntitySelectorConfig(domain=[SENSOR_DOMAIN, ASSIST_SAT_DOMAIN])
            ),
            vol.Required(
                CONF_MEDIAPLAYER_DEVICE,
                default=self.config_entry.data[CONF_MEDIAPLAYER_DEVICE],
            ): EntitySelector(EntitySelectorConfig(domain=MEDIAPLAYER_DOMAIN)),
            vol.Required(
                CONF_MUSICPLAYER_DEVICE,
                default=self.config_entry.data[CONF_MUSICPLAYER_DEVICE],
            ): EntitySelector(EntitySelectorConfig(domain=MEDIAPLAYER_DOMAIN)),
        }

        if self.va_type == VAType.VIEW_AUDIO:
            data_schema = vol.Schema(
                {
                    **BASE_OPTIONS,
                    vol.Required(
                        CONF_DISPLAY_DEVICE,
                        default=self.config_entry.data[CONF_DISPLAY_DEVICE],
                    ): DeviceSelector(
                        DeviceSelectorConfig(
                            multiple=True,
                            filter=[
                                EntityFilterSelectorConfig(
                                    integration=BROWSERMOD_DOMAIN
                                ),
                                EntityFilterSelectorConfig(
                                    integration=REMOTE_ASSIST_DISPLAY_DOMAIN,
                                ),
                            ],
                        )
                    ),
                }
            )
        else:  # audio_only
            data_schema = vol.Schema(BASE_OPTIONS)

        # Show the form for the selected type
        return self.async_show_form(step_id="main_config", data_schema=data_schema)

    async def async_step_dashboard_options(self, user_input=None):
        """Handle dashboard options flow."""
        if user_input is not None:
            # This is just updating the core config so update config_entry.data
            options = self.config_entry.options | user_input
            return self.async_create_entry(data=options)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DASHBOARD,
                    default=self.config_entry.options.get(
                        CONF_DASHBOARD, DEFAULT_DASHBOARD
                    ),
                ): str,
                vol.Optional(
                    CONF_HOME,
                    default=self.config_entry.options.get(CONF_HOME, DEFAULT_VIEW_HOME),
                ): str,
                vol.Optional(
                    CONF_MUSIC,
                    default=self.config_entry.options.get(
                        CONF_MUSIC, DEFAULT_VIEW_MUSIC
                    ),
                ): str,
                vol.Optional(
                    CONF_INTENT,
                    default=self.config_entry.options.get(
                        CONF_INTENT, DEFAULT_VIEW_INTENT
                    ),
                ): str,
                vol.Optional(
                    CONF_BACKGROUND,
                    default=self.config_entry.options.get(
                        CONF_BACKGROUND, DEFAULT_VIEW_BACKGROUND
                    ),
                ): str,
                vol.Optional(
                    CONF_ASSIST_PROMPT,
                    default=self.config_entry.options.get(
                        CONF_ASSIST_PROMPT, DEFAULT_ASSIST_PROMPT
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        translation_key="assist_prompt_selector",
                        options=[e.value for e in VAAssistPrompt],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_STATUS_ICON_SIZE,
                    default=self.config_entry.options.get(
                        CONF_STATUS_ICON_SIZE, DEFAULT_STATUS_ICON_SIZE
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        translation_key="status_icons_size_selector",
                        options=[e.value for e in VAIconSizes],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_FONT_STYLE,
                    default=self.config_entry.options.get(
                        CONF_FONT_STYLE, DEFAULT_FONT_STYLE
                    ),
                ): str,
                vol.Optional(
                    CONF_STATUS_ICONS,
                    default=self.config_entry.options.get(
                        CONF_STATUS_ICONS, DEFAULT_STATUS_ICONS
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        translation_key="status_icons_selector",
                        options=[],
                        mode=SelectSelectorMode.LIST,
                        multiple=True,
                        custom_value=True,
                    )
                ),
                vol.Optional(
                    CONF_USE_24H_TIME,
                    default=self.config_entry.options.get(
                        CONF_USE_24H_TIME, DEFAULT_USE_24H_TIME
                    ),
                ): bool,
            }
        )

        # Show the form for the selected type
        return self.async_show_form(
            step_id="dashboard_options", data_schema=data_schema
        )

    async def async_step_default_options(self, user_input=None):
        """Handle default options flow."""
        if user_input is not None:
            # This is just updating the core config so update config_entry.data
            options = self.config_entry.options | user_input
            return self.async_create_entry(data=options)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_WEATHER_ENTITY,
                    default=self.config_entry.options.get(
                        CONF_WEATHER_ENTITY, DEFAULT_WEATHER_ENITITY
                    ),
                ): EntitySelector(EntitySelectorConfig(domain=WEATHER_DOMAIN)),
                vol.Optional(
                    CONF_MIC_TYPE,
                    default=self.config_entry.options.get(
                        CONF_MIC_TYPE, DEFAULT_MIC_TYPE
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        translation_key="mic_type_selector",
                        options=[e.value for e in VAMicType],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_MODE,
                    default=self.config_entry.options.get(CONF_MODE, DEFAULT_MODE),
                ): str,
                vol.Optional(
                    CONF_VIEW_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_VIEW_TIMEOUT, DEFAULT_VIEW_TIMEOUT
                    ),
                ): int,
                vol.Optional(
                    CONF_DO_NOT_DISTURB,
                    default=self.config_entry.options.get(
                        CONF_DO_NOT_DISTURB, DEFAULT_DND
                    ),
                ): bool,
                vol.Optional(
                    CONF_USE_ANNOUNCE,
                    default=self.config_entry.options.get(
                        CONF_USE_ANNOUNCE, DEFAULT_USE_ANNOUNCE
                    ),
                ): bool,
                vol.Optional(
                    CONF_MIC_UNMUTE,
                    default=self.config_entry.options.get(
                        CONF_MIC_UNMUTE, DEFAULT_MIC_UNMUTE
                    ),
                ): bool,
            }
        )

        # Show the form for the selected type
        return self.async_show_form(step_id="default_options", data_schema=data_schema)
