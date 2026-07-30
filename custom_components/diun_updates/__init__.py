"""Diun Container Updates Integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import CONF_CONTAINERS, DOMAIN, EVENT_SET_UPDATE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.UPDATE]

SERVICE_SET_UPDATE = "set_update"
SERVICE_CLEAR_UPDATE = "clear_update"

ATTR_CONTAINER = "container"
ATTR_LATEST_VERSION = "latest_version"
ATTR_INSTALLED_VERSION = "installed_version"
ATTR_RELEASE_URL = "release_url"
ATTR_RELEASE_SUMMARY = "release_summary"

SET_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONTAINER): cv.string,
        vol.Optional(ATTR_LATEST_VERSION): cv.string,
        vol.Optional(ATTR_INSTALLED_VERSION): cv.string,
        vol.Optional(ATTR_RELEASE_URL): cv.string,
        vol.Optional(ATTR_RELEASE_SUMMARY): cv.string,
    }
)

CLEAR_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONTAINER): cv.string,
        vol.Optional(ATTR_INSTALLED_VERSION): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Diun Updates from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    if not hass.services.has_service(DOMAIN, SERVICE_SET_UPDATE):

        async def _handle_set_update(call: ServiceCall) -> None:
            await _dispatch(
                hass,
                call.data[ATTR_CONTAINER],
                {
                    "available": True,
                    "latest_version": call.data.get(ATTR_LATEST_VERSION),
                    "installed_version": call.data.get(ATTR_INSTALLED_VERSION),
                    "release_url": call.data.get(ATTR_RELEASE_URL),
                    "release_summary": call.data.get(ATTR_RELEASE_SUMMARY),
                },
            )

        async def _handle_clear_update(call: ServiceCall) -> None:
            await _dispatch(
                hass,
                call.data[ATTR_CONTAINER],
                {
                    "available": False,
                    "installed_version": call.data.get(ATTR_INSTALLED_VERSION),
                },
            )

        hass.services.async_register(
            DOMAIN, SERVICE_SET_UPDATE, _handle_set_update, schema=SET_UPDATE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, SERVICE_CLEAR_UPDATE, _handle_clear_update, schema=CLEAR_UPDATE_SCHEMA
        )
        _LOGGER.debug("diun_updates: Services registered")

    return True


async def _dispatch(hass: HomeAssistant, container_name: str, payload: dict) -> None:
    """Find the update entity for the given container and push new data to it."""
    registry = er.async_get(hass)
    for entity_entry in registry.entities.values():
        if entity_entry.platform != DOMAIN or entity_entry.domain != "update":
            continue
        # unique_id pattern: diun_updates_<entry_id>_<container_name>
        if entity_entry.unique_id.endswith(f"_{container_name}"):
            hass.bus.async_fire(
                EVENT_SET_UPDATE,
                {"entity_id": entity_entry.entity_id, **payload},
            )
            _LOGGER.info(
                "diun_updates: container '%s' → update_available=%s",
                container_name,
                payload.get("available"),
            )
            return
    _LOGGER.warning(
        "diun_updates: No update entity found for container '%s'. "
        "Is it listed under Integrationen → Diun Container Updates → Konfigurieren?",
        container_name,
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_UPDATE)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR_UPDATE)
    return unloaded
