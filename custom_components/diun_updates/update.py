"""Update platform for Diun Container Updates."""
from __future__ import annotations

import logging

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_CONTAINERS,
    DOMAIN,
    EVENT_INSTALL_REQUESTED,
    EVENT_SET_UPDATE,
    VERSION_CURRENT,
    VERSION_UPDATE_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one update entity per configured container."""
    containers: list[str] = entry.options.get(
        CONF_CONTAINERS, entry.data.get(CONF_CONTAINERS, [])
    )
    async_add_entities(
        [DiunUpdateEntity(entry.entry_id, name) for name in containers],
        update_before_add=True,
    )


class DiunUpdateEntity(RestoreEntity, UpdateEntity):
    """
    Update entity for a Docker container with a pending diun update.

    Diun liefert keine echten Versionsnummern, daher wird rein binär
    gearbeitet: installed_version ist immer "latest", latest_version wird
    bei einem gemeldeten Update auf "Update vorhanden" gesetzt (bzw. auf
    einen von Diun mitgelieferten Wert, falls vorhanden).

    Gesteuert ausschließlich über die Services des Integrations-Domains:
      - diun_updates.set_update   container: <name>
      - diun_updates.clear_update container: <name>   (Quittierung)

    Klick auf "Install" installiert nichts selbst, sondern feuert nur
    diun_updates_install_requested, damit eine separate Automation reagieren kann.
    """

    _attr_should_poll = False
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, entry_id: str, container_name: str) -> None:
        self._container_name = container_name
        self._attr_name = f"Diun Update {container_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{container_name}"
        self._attr_installed_version = VERSION_CURRENT
        self._attr_latest_version = VERSION_CURRENT
        self._attr_release_url = None
        self._attr_release_summary = None

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to set_update events."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            attrs = last_state.attributes
            self._attr_latest_version = attrs.get("latest_version", VERSION_CURRENT)
            self._attr_release_url = attrs.get("release_url")
            self._attr_release_summary = attrs.get("release_summary")
            _LOGGER.debug(
                "diun_updates: Restored '%s' → latest=%s",
                self._container_name,
                self._attr_latest_version,
            )

        @callback
        def _handle_set_update(event: Event) -> None:
            if event.data.get("entity_id") != self.entity_id:
                return

            if event.data.get("available"):
                self._attr_latest_version = (
                    event.data.get("latest_version") or VERSION_UPDATE_AVAILABLE
                )
                self._attr_release_url = event.data.get("release_url")
                self._attr_release_summary = event.data.get("release_summary")
            else:
                # Quittierung: zurück auf "latest", optional mit echter Versionsangabe
                self._attr_installed_version = (
                    event.data.get("installed_version") or VERSION_CURRENT
                )
                self._attr_latest_version = self._attr_installed_version
                self._attr_release_url = None
                self._attr_release_summary = None

            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_SET_UPDATE, _handle_set_update)
        )

    async def async_install(self, version: str | None, backup: bool, **kwargs) -> None:
        """Handle the 'Install' button: only announce the request, do nothing else."""
        self.hass.bus.async_fire(
            EVENT_INSTALL_REQUESTED,
            {
                "entity_id": self.entity_id,
                "container": self._container_name,
            },
        )
        _LOGGER.info(
            "diun_updates: Install requested for container '%s'", self._container_name
        )

    @property
    def extra_state_attributes(self) -> dict:
        return {"container": self._container_name}
