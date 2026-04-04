"""Config flow for Diun Container Updates."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_CONTAINERS


def _parse_containers(raw: str) -> list[str]:
    """Split a comma- or newline-separated string into a clean list."""
    items = []
    for part in raw.replace("\n", ",").split(","):
        name = part.strip()
        if name:
            items.append(name)
    return items


class DiunUpdatesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup via the UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Show the setup form."""
        errors = {}

        if user_input is not None:
            containers = _parse_containers(user_input[CONF_CONTAINERS])
            if not containers:
                errors[CONF_CONTAINERS] = "no_containers"
            else:
                return self.async_create_entry(
                    title="Diun Container Updates",
                    data={CONF_CONTAINERS: containers},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTAINERS): str,
                }
            ),
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
    """Allow editing the container list after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        # options override data when present (set by a previous options save)
        current = self._config_entry.options.get(
            CONF_CONTAINERS,
            self._config_entry.data.get(CONF_CONTAINERS, []),
        )

        if user_input is not None:
            containers = _parse_containers(user_input[CONF_CONTAINERS])
            if not containers:
                errors[CONF_CONTAINERS] = "no_containers"
            else:
                # Saving into options triggers the update_listener â reload
                return self.async_create_entry(
                    title="",
                    data={CONF_CONTAINERS: containers},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONTAINERS,
                        default=", ".join(current),
                    ): str,
                }
            ),
            errors=errors,
        )
