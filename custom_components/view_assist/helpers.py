"""Helper functions."""

import logging
import os
from pathlib import Path
import random
from typing import Any

import requests

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.config_validation import ensure_list
from homeassistant.util import datetime

from .const import (
    BROWSERMOD_DOMAIN,
    CONF_DISPLAY_DEVICE,
    DOMAIN,
    REMOTE_ASSIST_DISPLAY_DOMAIN,
    VAMODE_REVERTS,
    VAConfigEntry,
    VADisplayType,
    VAMode,
    VAType,
)

_LOGGER = logging.getLogger(__name__)


def is_first_instance(
    hass: HomeAssistant, config: VAConfigEntry, display_instance_only: bool = False
):
    """Return if first config entry.

    Optional to return if first config entry for instance with type of view_audio
    """
    accepted_types = [VAType.VIEW_AUDIO]
    if not display_instance_only:
        accepted_types.append(VAType.AUDIO_ONLY)

    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.data["type"] in accepted_types and not entry.disabled_by
    ]

    # If first instance matches this entry id, return True
    if entries and entries[0].entry_id == config.entry_id:
        return True
    return False


def get_loaded_instance_count(hass: HomeAssistant) -> int:
    """Return number of loaded instances."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if not entry.disabled_by
    ]
    return len(entries)


def get_entity_attribute(hass: HomeAssistant, entity_id: str, attribute: str) -> Any:
    """Get attribute from entity by entity_id."""
    if entity := hass.states.get(entity_id):
        return entity.attributes.get(attribute)
    return None


def get_config_entry_by_config_data_value(
    hass: HomeAssistant, value: str
) -> VAConfigEntry:
    """Get config entry from a config data param value."""
    # Loop config entries
    for entry in hass.config_entries.async_entries(DOMAIN):
        for param_value in entry.data.values():
            if (
                param_value == value
                or get_device_id_from_entity_id(hass, param_value) == value
            ):
                return entry
    return None


def get_config_entry_by_entity_id(hass: HomeAssistant, entity_id: str) -> VAConfigEntry:
    """Get config entry by entity id."""
    entity_registry = er.async_get(hass)
    if entity := entity_registry.async_get(entity_id):
        return hass.config_entries.async_get_entry(entity.config_entry_id)
    return None


def get_device_name_from_id(hass: HomeAssistant, device_id: str) -> str:
    """Get the browser_id for the device based on device domain."""
    device_reg = dr.async_get(hass)
    device = device_reg.async_get(device_id)

    return device.name if device else None


def get_device_id_from_entity_id(hass: HomeAssistant, entity_id: str) -> str:
    """Get the device id of an entity by id."""
    entity_registry = er.async_get(hass)
    if entity := entity_registry.async_get(entity_id):
        return entity.device_id
    return None


def get_device_id_from_name(hass: HomeAssistant, device_name: str) -> str:
    """Get the device id of the device with the given name."""

    def find_device_for_domain(domain: str, device_name: str) -> str | None:
        entries = list(
            hass.config_entries.async_entries(
                domain, include_ignore=False, include_disabled=False
            )
        )

        if entries:
            device_reg = dr.async_get(hass)
            for entry in entries:
                devices = device_reg.devices.get_devices_for_config_entry_id(
                    entry.entry_id
                )
                if devices:
                    for device in devices:
                        if device.name == device_name:
                            return device.id
        return None

    supported_device_domains = [BROWSERMOD_DOMAIN, REMOTE_ASSIST_DISPLAY_DOMAIN]

    for domain in supported_device_domains:
        if device_id := find_device_for_domain(domain, device_name):
            return device_id
    return None


def get_sensor_entity_from_instance(
    hass: HomeAssistant,
    entry_id: str,
) -> str:
    """Get VA sensor entity from config entry."""
    entity_registry = er.async_get(hass)
    if integration_entities := er.async_entries_for_config_entry(
        entity_registry, entry_id
    ):
        for entity in integration_entities:
            if entity.domain == Platform.SENSOR:
                return entity.entity_id
    return None


def get_entity_id_from_conversation_device_id(
    hass: HomeAssistant, device_id: str
) -> str | None:
    """Get the view assist entity id for a device id relating to the mic entity."""
    entries = list(
        hass.config_entries.async_entries(
            DOMAIN, include_ignore=False, include_disabled=False
        )
    )
    entry: VAConfigEntry
    for entry in entries:
        mic_entity_id = entry.runtime_data.mic_device
        entity_registry = er.async_get(hass)
        mic_entity = entity_registry.async_get(mic_entity_id)
        if mic_entity.device_id == device_id:
            return get_sensor_entity_from_instance(hass, entry.entry_id)
    return None


def get_entity_id_by_browser_id(hass: HomeAssistant, browser_id: str) -> str:
    """Get entity id form browser id.

    Support websocket
    """
    # Browser ID is same as device name, so get device id to VA device with display device
    # set to this id
    if device_id := get_device_id_from_name(hass, browser_id):
        # Get all instances of view assist for browser id
        entry_ids = [
            entry.entry_id
            for entry in hass.config_entries.async_entries(DOMAIN)
            if device_id in ensure_list(entry.data.get(CONF_DISPLAY_DEVICE))
        ]
        if entry_ids:
            return get_sensor_entity_from_instance(hass, entry_ids[0])

    return None


def get_display_index(hass: HomeAssistant, entity_id: str, browser_id: str) -> int:
    """Get display index of browser id on entity."""
    browser_device_id = get_device_id_from_name(hass, browser_id)
    entity_config = get_config_entry_by_entity_id(hass, entity_id)

    entity_devices = entity_config.data.get(CONF_DISPLAY_DEVICE)
    if not isinstance(entity_devices, list):
        entity_devices = [entity_devices]

    for index, device in enumerate(entity_devices):
        if device == browser_device_id:
            return index
    return -1


def get_display_type_from_browser_id(
    hass: HomeAssistant, browser_id: str
) -> VADisplayType:
    """Return VAType from a browser id."""
    device_id = get_device_id_from_name(hass, browser_id)
    if device_id:
        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)

        entry = hass.config_entries.async_get_entry(device.primary_config_entry)
        if entry:
            if entry.domain == BROWSERMOD_DOMAIN:
                return VADisplayType.BROWSERMOD
            if entry.domain == REMOTE_ASSIST_DISPLAY_DOMAIN:
                return VADisplayType.REMOTE_ASSIST_DISPLAY
    return None


def get_revert_settings_for_mode(mode: VAMode) -> tuple:
    """Get revert settings from VAMODE_REVERTS for mode."""
    if mode in VAMODE_REVERTS:
        return VAMODE_REVERTS[mode].get("revert"), VAMODE_REVERTS[mode].get("view")
    return False, None


def get_assist_satellite_entity_id_from_device_id(
    hass: HomeAssistant, device_id: str
) -> str | None:
    """Get assist satellite entity id from device id."""
    device_entities = er.async_entries_for_device(er.async_get(hass), device_id)
    for entity in device_entities:
        if entity.domain == "assist_satellite":
            return entity.entity_id
    return None


def get_entities_by_attr_filter(
    hass: HomeAssistant,
    filter: dict[str, Any] | None = None,
    exclude: dict[str, Any] | None = None,
) -> list[str]:
    """Get the entity ids of devices not in dnd mode."""
    matched_entities = []
    entry_ids = [entry.entry_id for entry in hass.config_entries.async_entries(DOMAIN)]
    for entry_id in entry_ids:
        entity_registry = er.async_get(hass)
        entities = er.async_entries_for_config_entry(entity_registry, entry_id)
        for entity in entities:
            if filter or exclude:
                if state := hass.states.get(entity.entity_id):
                    add_entity = False
                    if filter:
                        for attr, value in filter.items():
                            if state.attributes.get(attr) == value:
                                add_entity = True
                    if add_entity and exclude:
                        for attr, value in exclude.items():
                            if state.attributes.get(attr) == value:
                                add_entity = False
                    if add_entity:
                        matched_entities.append(entity.entity_id)
            else:
                matched_entities.append(entity.entity_id)
    return matched_entities


# ----------------------------------------------------------------
# Images
# ----------------------------------------------------------------
def get_random_image(
    hass: HomeAssistant, directory: str, source: str
) -> dict[str, Any]:
    """Return a random image from supplied directory or url."""

    valid_extensions = (".jpeg", ".jpg", ".tif", ".png")

    if source == "local":
        config_dir = hass.config.config_dir
        # Translate /local/ to /config/www/ for directory validation
        if "local" in directory:
            filesystem_directory = directory.replace("local", f"{config_dir}/www/", 1)
        elif "config" in directory:
            filesystem_directory = directory.replace("config", f"{config_dir}/{DOMAIN}")
        else:
            filesystem_directory = f"{config_dir}/{directory}"

        # Remove any //
        filesystem_directory = filesystem_directory.replace("//", "/")

        # Verify the directory exists
        if not Path.is_dir(Path(filesystem_directory)):
            return {"error": f"The directory '{filesystem_directory}' does not exist."}

        # List only image files with the valid extensions
        dir_files = os.listdir(filesystem_directory)
        images = [f for f in dir_files if f.lower().endswith(valid_extensions)]

        # Check if any images were found
        if not images:
            return {
                "error": f"No images found in the directory '{filesystem_directory}'."
            }

        # Select a random image
        selected_image = random.choice(images)

        # Replace /config/www/ with /local/ for constructing the relative path
        if filesystem_directory.startswith(f"{config_dir}/www/"):
            relative_path = filesystem_directory.replace(
                f"{config_dir}/www/", "/local/"
            )
        else:
            relative_path = directory

        # Ensure trailing slash in the relative path
        if not relative_path.endswith("/"):
            relative_path += "/"

        # Construct the image path
        image_path = f"{relative_path}{selected_image}"

        # Remove any //
        image_path = image_path.replace("//", "/")

    elif source == "download":
        url = "https://unsplash.it/640/425?random"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            current_time = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"random_{current_time}.jpg"
            full_path = Path(f"{directory}/{filename}")

            with Path.open(full_path, "wb") as file:
                file.write(response.content)

            # Remove previous background image
            for file in os.listdir(directory):
                if file.startswith("random_") and file != filename:
                    Path(f"{directory}/{filename}").unlink(missing_ok=True)

            image_path = full_path
        else:
            # Return existing image if the download fails
            existing_files = [
                Path(f"{directory}/{filename}")
                for file in os.listdir(directory)
                if file.startswith("random_")
            ]
            image_path = existing_files[0] if existing_files else None

        if not image_path:
            return {
                "error": "Failed to download a new image and no existing images found."
            }

    else:
        return {"error": "Invalid source specified. Use 'local' or 'download'."}

    # Return the image path in a dictionary
    return {"image_path": image_path}


def create_dir_if_not_exist(hass: HomeAssistant, dir_name: str) -> bool:
    """Create a directory under config if it doesn't exist.

    Needs to be called from the executor to prevent blocking.
    """
    config_dir = hass.config.config_dir
    path = Path(f"{config_dir}/{dir_name}")
    try:
        if not Path.exists(path):
            Path.mkdir(path)
            return True
    except OSError:
        return False
    return False
