"""Binary sensor platform for Diun Container Updates."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_CONTAINERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one binary sensor per configured container."""
    containers: list[str] = entry.options.get(
        CONF_CONTAINERS, entry.data.get(CONF_CONTAINERS, [])
    )
    async_add_entities(
        [DiunUpdateSensor(entry.entry_id, name) for name in containers],
        update_before_add=True,
    )


class DiunUpdateSensor(RestoreEntity, BinarySensorEntity):
    """
    Binary sensor for a Docker container with a pending diun update.

    Controlled via the integration's own services:
      - diun_updates.set   container: <name>   → on
      - diun_updates.clear container: <name>   → off
    """

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_should_poll = False

    def __init__(self, entry_id: str, container_name: str) -> None:
        self._container_name = container_name
        self._attr_is_on = False
        self._attr_name = f"Diun Update {container_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{container_name}"

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to set_state events."""
        await super().async_added_to_hass()

        # Restore last known state across restarts
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
            _LOGGER.debug(
                "diun_updates: Restored '%s' → %s",
                self._container_name,
                self._attr_is_on,
            )

        # Listen for state-change events fired by the services in __init__.py
        @callback
        def _handle_set_state(event: Event) -> None:
            if event.data.get("entity_id") == self.entity_id:
                self._attr_is_on = event.data.get("state", False)
                self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_set_state", _handle_set_state)
        )

    @property
    def extra_state_attributes(self) -> dict:
        return {"container": self._container_name}
