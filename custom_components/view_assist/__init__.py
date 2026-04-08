"""View Assist custom integration."""

import logging

from homeassistant import config_entries
from homeassistant.const import CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_DISPLAY_DEVICE,
    CONF_MEDIAPLAYER_DEVICE,
    CONF_MIC_DEVICE,
    CONF_MUSICPLAYER_DEVICE,
    DOMAIN,
)
from .core import CoreManager
from .data import set_runtime_data_for_config
from .devices import DeviceManager
from .helpers import get_integration_entries, get_master_config_entry, is_first_instance
from .migration import async_migrate_view_assist_config_entry
from .typed import VAConfigEntry, VAType

_LOGGER = logging.getLogger(__name__)


def _repair_stale_vaca_entity_ids(
    hass: HomeAssistant, entry: VAConfigEntry
) -> VAConfigEntry:
    """Repair stale VACA entity ids after a tablet reinstall changes its UUID."""
    display_device = entry.data.get(CONF_DISPLAY_DEVICE) or ""
    if not display_device.startswith("va-"):
        return entry

    suffix = display_device.removeprefix("va-")
    entity_registry = er.async_get(hass)
    data = dict(entry.data)
    updated = False

    def resolve_entity(prefix: str) -> str | None:
        candidates = sorted(
            entity.entity_id
            for entity in entity_registry.entities.values()
            if entity.entity_id.startswith(prefix)
        )
        return candidates[0] if candidates else None

    stale_mic = data.get(CONF_MIC_DEVICE)
    if stale_mic and entity_registry.async_get(stale_mic) is None:
        if mic_entity := resolve_entity(f"assist_satellite.vaca_{suffix}"):
            data[CONF_MIC_DEVICE] = mic_entity
            updated = True

    stale_media = data.get(CONF_MEDIAPLAYER_DEVICE)
    if stale_media and entity_registry.async_get(stale_media) is None:
        if media_entity := resolve_entity(f"media_player.vaca_{suffix}"):
            data[CONF_MEDIAPLAYER_DEVICE] = media_entity
            updated = True

    stale_music = data.get(CONF_MUSICPLAYER_DEVICE)
    if stale_music and entity_registry.async_get(stale_music) is None:
        if music_entity := resolve_entity(f"media_player.vaca_{suffix}"):
            data[CONF_MUSICPLAYER_DEVICE] = music_entity
            updated = True

    if updated:
        _LOGGER.info(
            "Repairing stale VACA entity ids for %s using display device %s",
            entry.title,
            display_device,
        )
        hass.config_entries.async_update_entry(entry, data=data)

    return entry


def migrate_to_section(entry: VAConfigEntry, params: list[str]):
    """Build a section for the config entry."""
    section = {}
    for param in params:
        if entry.options.get(param):
            section[param] = entry.options.pop(param)
    return section


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: VAConfigEntry,
) -> bool:
    """Migrate config entry if needed."""
    return await async_migrate_view_assist_config_entry(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: VAConfigEntry):
    """Set up View Assist from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    has_master_entry = get_master_config_entry(hass)
    is_master_entry = has_master_entry and entry.data[CONF_TYPE] == VAType.MASTER_CONFIG

    if not has_master_entry:
        # Start a config flow to add a master entry if no master entry
        if is_first_instance(hass, entry):
            _LOGGER.debug("No master entry found, starting config flow")
            discovery_flow.async_create_flow(
                hass,
                DOMAIN,
                {"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
                {"name": VAType.MASTER_CONFIG},
            )
            return True
        return False

    if entry.data[CONF_TYPE] != VAType.MASTER_CONFIG:
        entry = _repair_stale_vaca_entity_ids(hass, entry)

    # Set runtime data
    set_runtime_data_for_config(hass, entry, is_master_entry)

    if is_master_entry:
        # Load asset manager
        await CoreManager(hass, entry).async_start()
    else:
        # Load device manager
        await DeviceManager(hass, entry).async_setup()

    # Add config change listener
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: VAConfigEntry):
    """Handle config options update."""
    # Reload the updated entry when options change.
    hass.config_entries.async_schedule_reload(config_entry.entry_id)

    # Dashboard options on the master entry flow down into every device entry.
    # Reload those entries too so runtime dashboard paths stay in sync.
    if config_entry.data[CONF_TYPE] == VAType.MASTER_CONFIG:
        for entry in get_integration_entries(hass):
            if entry.entry_id != config_entry.entry_id:
                hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VAConfigEntry):
    """Unload a config entry."""

    # Unload js resources
    if entry.data[CONF_TYPE] == VAType.MASTER_CONFIG:
        return await CoreManager.async_unload(hass, entry)
    return await DeviceManager.async_unload(hass, entry)
