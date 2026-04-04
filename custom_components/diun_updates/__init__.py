"""Diun Container Updates Integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_CONTAINERS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR]

SERVICE_SET = "turn_on"
SERVICE_CLEAR = "turn_off"
ATTR_CONTAINER = "container"

SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_CONTAINER): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Diun Updates from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    # Register services only once (not once per entry)
    if not hass.services.has_service(DOMAIN, SERVICE_SET):

        async def _handle_set(call: ServiceCall) -> None:
            await _set_sensor_state(hass, call.data[ATTR_CONTAINER], True)

        async def _handle_clear(call: ServiceCall) -> None:
            await _set_sensor_state(hass, call.data[ATTR_CONTAINER], False)

        hass.services.async_register(DOMAIN, SERVICE_SET, _handle_set, schema=SERVICE_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_CLEAR, _handle_clear, schema=SERVICE_SCHEMA)
        _LOGGER.debug("diun_updates: Services registered")

    return True


async def _set_sensor_state(hass: HomeAssistant, container_name: str, state: bool) -> None:
    """Find the entity for the given container and update its state."""
    registry = er.async_get(hass)

    for entity_entry in registry.entities.values():
        if entity_entry.domain != "binary_sensor":
            continue
        if entity_entry.platform != DOMAIN:
            continue
        # unique_id pattern: diun_updates_<entry_id>_<container_name>
        if entity_entry.unique_id.endswith(f"_{container_name}"):
            hass.bus.async_fire(
                f"{DOMAIN}_set_state",
                {"entity_id": entity_entry.entity_id, "state": state},
            )
            _LOGGER.info(
                "diun_updates.%s: container '%s' → %s",
                "set" if state else "clear",
                container_name,
                state,
            )
            return

    _LOGGER.warning(
        "diun_updates: No sensor found for container '%s'. "
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
        hass.services.async_remove(DOMAIN, SERVICE_SET)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR)
    return unloaded
