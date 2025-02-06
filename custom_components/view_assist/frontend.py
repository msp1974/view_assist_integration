"""Functions to configure Lovelace frontend with dashboard and views."""

import asyncio
from dataclasses import dataclass
import logging

from homeassistant.components.lovelace import (
    CONF_ALLOW_SINGLE_WORD,
    CONF_ICON,
    CONF_TITLE,
    CONF_URL_PATH,
    dashboard,
)
from homeassistant.const import CONF_MODE
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.util.yaml import load_yaml_dict

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DASHBOARD_NAME = "View Assist"

# This is path of dashboard files in integration directory.
# Ie the directory this file is in.
CONFIG_FILES_PATH = "default_config"

# This could be replaced with a function that loads all files in directory if desired
VIEWS_TO_LOAD = ["clock", "music", "info", "weather"]


@dataclass
class DashboardView:
    """Class for dashboard view config."""

    type: str
    title: str
    path: str
    cards: list


class FrontendConfig:
    """Class to configure front end for View Assist."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        self.hass = hass
        self.files_path = f"{self.hass.config.config_dir}/custom_components/{DOMAIN}/{CONFIG_FILES_PATH}"
        self.path = f"dashboard-{slugify(DASHBOARD_NAME)}"

    async def async_config(self):
        """Create the view assist dashboard and views if they dont exist already.

        It will not overwrite modifications made to views
        """
        await self._config_dashboard()
        await self._config_views(VIEWS_TO_LOAD)
        await self._delete_home_view()

    async def _config_dashboard(self):
        """Create dashboard if it doesn#t exist."""

        # Path to dashboard config file
        f = f"{self.files_path}/dashboard.yaml"

        # Get lovelace (frontend) config data
        lovelace = self.hass.data["lovelace"]

        # If dashboard not in existing dashboard collection
        if self.path not in lovelace["dashboards"]:
            # Load dashboard config file
            dashboard_config = await self.hass.async_add_executor_job(load_yaml_dict, f)

            # Create dashboard
            dashboards_collection: dashboard.DashboardsCollection = lovelace[
                "dashboards_collection"
            ]
            await dashboards_collection.async_create_item(
                {
                    CONF_ICON: "mdi:glasses",
                    CONF_TITLE: DASHBOARD_NAME,
                    CONF_URL_PATH: self.path,
                }
            )

            # Wait for dashboard to be registered in Hass object
            while not lovelace["dashboards"].get(self.path):
                await asyncio.sleep(0.1)

            dashboard_store: dashboard.LovelaceStorage = lovelace["dashboards"][
                self.path
            ]
            await dashboard_store.async_save(dashboard_config)
        else:
            _LOGGER.info("View Assist dashboard already configured")

    async def _config_views(self, views_to_load: list[str]):
        """Create views from config files if not exist."""
        # Get lovelace (frontend) config data
        lovelace = self.hass.data["lovelace"]

        # Get access to dashboard store
        dashboard_store: dashboard.LovelaceStorage = lovelace["dashboards"].get(
            self.path
        )

        # Load dashboard config data
        if dashboard_store:
            dashboard_config = await dashboard_store.async_load(True)

            # Make list of existing view names for this dashboard
            existing_views = [
                view["path"] for view in dashboard_config["views"] if view.get("path")
            ]

            # Iterate list of views to add
            for view in views_to_load:
                # If view already exists, skip adding it
                if view in existing_views:
                    continue

                # Load view config from file.
                f = f"{self.files_path}/views/{view}.yaml"
                new_view_config = await self.hass.async_add_executor_job(
                    load_yaml_dict, f
                )

                # Create new view and add it to dashboard
                new_view = DashboardView(
                    type="panel", title=view.title(), path=view, cards=[new_view_config]
                )
                dashboard_config["views"].append(new_view)

            # Save dashboard config back to HA
            await dashboard_store.async_save(dashboard_config)

    async def _delete_home_view(self):
        # Get lovelace (frontend) config data
        lovelace = self.hass.data["lovelace"]

        # Get access to dashboard store
        dashboard_store: dashboard.LovelaceStorage = lovelace["dashboards"].get(
            self.path
        )

        # Load dashboard config data
        if dashboard_store:
            dashboard_config = await dashboard_store.async_load(True)

            # Remove view with title of home
            for i, view in enumerate(dashboard_config["views"]):
                if view.get("title", "").lower() == "home":
                    del dashboard_config["views"][i]
                    break

            # Save dashboard config back to HA
            await dashboard_store.async_save(dashboard_config)
