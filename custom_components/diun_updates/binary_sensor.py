"""Binary sensor platform for Diun Container Updates."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    A binary sensor representing a Docker container with a pending update.

    State is writable via the standard Home Assistant services:
      - homeassistant.turn_on   â marks update available  (state: on)
      - homeassistant.turn_off  â clears update            (state: off)
      - homeassistant.toggle    â toggles state

    Use these in your diun webhook automation to set the correct sensor.
    Entity ID pattern: binary_sensor.diun_update_<container_name>
    """

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_should_poll = False

    def __init__(self, entry_id: str, container_name: str) -> None:
        self._container_name = container_name
        self._attr_is_on = False
        self._attr_name = f"Diun Update {container_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{container_name}"

    # ------------------------------------------------------------------
    # RestoreEntity â persist state across restarts
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Restore last known state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
            _LOGGER.debug(
                "diun_updates: Restored '%s' â %s",
                self._container_name,
                self._attr_is_on,
            )

    # ------------------------------------------------------------------
    # Make the entity writable so HA's built-in toggle services work
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Mark update as available."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Clear the update flag."""
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_toggle(self, **kwargs) -> None:
        """Toggle update flag."""
        self._attr_is_on = not self._attr_is_on
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Extra attributes
    # ------------------------------------------------------------------

    @property
    def extra_state_attributes(self) -> dict:
        return {"container": self._container_name}
