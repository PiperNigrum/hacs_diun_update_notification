"""Config flow for Diun Container Updates."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector

from .const import (
    CONF_CONTAINERS,
    CONF_EXTRA_CONTAINERS,
    CONF_PORTAINER_DEVICES,
    DOMAIN,
    PORTAINER_DOMAIN,
)


def _parse_containers(raw: str) -> list[str]:
    """Split a comma- or newline-separated string into a clean list."""
    items = []
    for part in raw.replace("\n", ",").split(","):
        name = part.strip()
        if name:
            items.append(name)
    return items


def _resolve_portainer_names(hass: HomeAssistant, device_ids: list[str]) -> list[str]:
    """Turn selected Portainer device IDs into their container names."""
    registry = dr.async_get(hass)
    names: list[str] = []
    for device_id in device_ids:
        device = registry.async_get(device_id)
        if device is None:
            continue
        name = device.name_by_user or device.name
        if name:
            names.append(name)
    return names


def _build_schema(defaults: dict) -> vol.Schema:
    """Build the setup/options form schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_PORTAINER_DEVICES,
                default=defaults.get(CONF_PORTAINER_DEVICES, []),
            ): selector.DeviceSelector(
                selector.DeviceSelectorConfig(
                    integration=PORTAINER_DOMAIN, multiple=True
                )
            ),
            vol.Optional(
                CONF_EXTRA_CONTAINERS,
                default=defaults.get(CONF_EXTRA_CONTAINERS, ""),
            ): str,
        }
    )


def _resolve_containers(hass: HomeAssistant, user_input: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (final container list, portainer device ids, extra container names)."""
    portainer_devices: list[str] = user_input.get(CONF_PORTAINER_DEVICES, [])
    extra_containers = _parse_containers(user_input.get(CONF_EXTRA_CONTAINERS, ""))
    portainer_names = _resolve_portainer_names(hass, portainer_devices)
    containers = sorted(set(portainer_names) | set(extra_containers))
    return containers, portainer_devices, extra_containers


class DiunUpdatesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup via the UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Show the setup form."""
        errors = {}
        if user_input is not None:
            containers, portainer_devices, extra_containers = _resolve_containers(
                self.hass, user_input
            )
            if not containers:
                errors["base"] = "no_containers"
            else:
                return self.async_create_entry(
                    title="Diun Container Updates",
                    data={
                        CONF_CONTAINERS: containers,
                        CONF_PORTAINER_DEVICES: portainer_devices,
                        CONF_EXTRA_CONTAINERS: extra_containers,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
            description_placeholders={
                "example": "homeassistant, portainer, nginx"
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DiunUpdatesOptionsFlow(config_entry)


class DiunUpdatesOptionsFlow(config_entries.OptionsFlow):
    """Allow editing the container selection after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        # options override data when present (set by a previous options save)
        current = self._config_entry.options or self._config_entry.data

        if user_input is not None:
            containers, portainer_devices, extra_containers = _resolve_containers(
                self.hass, user_input
            )
            if not containers:
                errors["base"] = "no_containers"
            else:
                # Saving into options triggers the update_listener → reload
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_CONTAINERS: containers,
                        CONF_PORTAINER_DEVICES: portainer_devices,
                        CONF_EXTRA_CONTAINERS: extra_containers,
                    },
                )

        defaults = {
            CONF_PORTAINER_DEVICES: current.get(CONF_PORTAINER_DEVICES, []),
            CONF_EXTRA_CONTAINERS: ", ".join(current.get(CONF_EXTRA_CONTAINERS, [])),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
            errors=errors,
        )
