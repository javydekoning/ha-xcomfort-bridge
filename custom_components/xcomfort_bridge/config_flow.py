"""Config flow for Eaton xComfort Bridge."""

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.data_entry_flow import section
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers import selector
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import (
    CONF_ADD_HEATER_POWER_SENSORS,
    CONF_ADD_LIGHT_POWER_SENSORS,
    CONF_ADD_ROOM_POWER_SENSORS,
    CONF_AUTH_KEY,
    CONF_HEATER_ROOM_ID,
    CONF_HEATER_ROOM_MAPPING,
    CONF_HEATER_ROOM_SKIP_REMAINING,
    CONF_HEATER_POWER_STALE_PROTECTION,
    CONF_IDENTIFIER,
    CONF_MAC,
    CONF_POWER_ENERGY_SECTION,
    DOMAIN,
)
from .hub import XComfortHub
from .xcomfort.devices import Heater

_LOGGER = logging.getLogger(__name__)


# If auto-discovered, we'll minimally need the AUTH_KEY
IDENTIFIER_AND_AUTH = vol.Schema(
    {
        vol.Required(CONF_AUTH_KEY): str,
        vol.Optional(CONF_IDENTIFIER, default="XComfort Bridge"): str,
    }
)

# If added manually, we'll also need the IP address:
FULL_CONFIG = IDENTIFIER_AND_AUTH.extend({vol.Required(CONF_IP_ADDRESS): str})


@config_entries.HANDLERS.register(DOMAIN)
class XComfortBridgeConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Eaton xComfort Bridge."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> config_entries.ConfigFlowResult:
        """Handle dhcp discovery."""
        ip = discovery_info.ip
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)

        for entry in self._async_current_entries():
            if (configured_mac := entry.data.get(CONF_MAC)) is not None and format_mac(configured_mac) == mac:
                if (old_ip := entry.data.get(CONF_IP_ADDRESS)) != ip:
                    _LOGGER.info(
                        "Bridge has changed IP-address. Configuring new IP and restarting. [mac=%s, new_ip=%s, old_ip=%s]",
                        mac, ip, old_ip
                    )
                    self.hass.config_entries.async_update_entry(
                        entry, data=entry.data | {CONF_IP_ADDRESS: ip}, title=self.title
                    )
                    self.hass.async_create_task(self.hass.config_entries.async_reload(entry.entry_id))
                return self.async_abort(reason="already_configured")
            if entry.data.get(CONF_MAC) is None and entry.data.get(CONF_IP_ADDRESS) == ip:
                _LOGGER.info("Saved MAC-address for bridge [mac=%s, ip=%s]", mac, ip)
                self.hass.config_entries.async_update_entry(entry, data=entry.data | {CONF_MAC: mac})
                self.hass.async_create_task(self.hass.config_entries.async_reload(entry.entry_id))
                return self.async_abort(reason="already_configured")

        # TODO: Does it actually look like an xcomfort bridge?

        self.data[CONF_MAC] = mac
        self.data[CONF_IP_ADDRESS] = ip

        return await self.async_step_auth()

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle the authentication step of config flow."""
        if user_input is not None:
            self.data[CONF_AUTH_KEY] = user_input[CONF_AUTH_KEY]
            self.data[CONF_IDENTIFIER] = user_input.get(CONF_IDENTIFIER)

            return self.async_create_entry(
                title=self.title,
                data=self.data,
            )
        return self.async_show_form(step_id="auth", data_schema=IDENTIFIER_AND_AUTH)

    async def async_step_user(self, user_input=None):
        """Handle a onboarding flow initiated by the user."""
        if user_input is not None:
            self.data[CONF_IP_ADDRESS] = user_input[CONF_IP_ADDRESS]
            self.data[CONF_AUTH_KEY] = user_input[CONF_AUTH_KEY]
            self.data[CONF_IDENTIFIER] = user_input.get(CONF_IDENTIFIER)

            await self.async_set_unique_id(f"{user_input[CONF_IDENTIFIER]}/{user_input[CONF_IP_ADDRESS]}")

            return self.async_create_entry(
                title=self.title,
                data=self.data,
            )

        return self.async_show_form(step_id="user", data_schema=FULL_CONFIG)

    async def async_step_import(self, import_data: dict):
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)

    @property
    def title(self) -> str:
        """Return the title of the config entry."""
        return self.data.get(CONF_IDENTIFIER, self.data.get(CONF_MAC, self.data.get(CONF_IP_ADDRESS, "Untitled")))

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow for this handler."""
        return XComfortBridgeOptionsFlowHandler(config_entry)


class XComfortBridgeOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle options flow for Eaton xComfort Bridge."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] = {}
        self._heater_devices: list[Heater] = []
        self._rooms = []
        self._heater_index = 0
        self._heater_room_mapping: dict[str, int] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options for the config entry."""
        if user_input is not None:
            options = dict(self._config_entry.options)
            section_options = dict(options.get(CONF_POWER_ENERGY_SECTION, {}))
            section_options.update(user_input.get(CONF_POWER_ENERGY_SECTION, {}))
            if not section_options.get(CONF_HEATER_POWER_STALE_PROTECTION, False):
                section_options.pop(CONF_HEATER_ROOM_MAPPING, None)
            options[CONF_POWER_ENERGY_SECTION] = section_options
            self._pending_options = options

            if section_options.get(CONF_HEATER_POWER_STALE_PROTECTION, False):
                await self._load_mapping_data()
                existing_mapping = section_options.get(CONF_HEATER_ROOM_MAPPING, {})
                self._heater_room_mapping = _normalize_heater_room_mapping(existing_mapping)
                if self._heater_devices and self._rooms:
                    self._heater_index = 0
                    return await self.async_step_heater_mapping()

            return self.async_create_entry(title="", data=self._pending_options)

        options = self._config_entry.options
        section_options = _filter_power_section_options(options.get(CONF_POWER_ENERGY_SECTION, {}))
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POWER_ENERGY_SECTION,
                    default=section_options,
                ): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_ADD_ROOM_POWER_SENSORS,
                                default=section_options.get(CONF_ADD_ROOM_POWER_SENSORS, True),
                            ): bool,
                            vol.Optional(
                                CONF_ADD_HEATER_POWER_SENSORS,
                                default=section_options.get(CONF_ADD_HEATER_POWER_SENSORS, False),
                            ): bool,
                            vol.Optional(
                                CONF_HEATER_POWER_STALE_PROTECTION,
                                default=section_options.get(CONF_HEATER_POWER_STALE_PROTECTION, False),
                            ): bool,
                            vol.Optional(
                                CONF_ADD_LIGHT_POWER_SENSORS,
                                default=section_options.get(CONF_ADD_LIGHT_POWER_SENSORS, False),
                            ): bool,
                        }
                    ),
                    {"collapsed": False},
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_heater_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Map heaters to rooms for stale protection."""
        if user_input is not None:
            heater = self._heater_devices[self._heater_index]
            selection = user_input.get(CONF_HEATER_ROOM_ID)
            self._update_heater_mapping(heater, selection)

            if user_input.get(CONF_HEATER_ROOM_SKIP_REMAINING):
                section_options = dict(self._pending_options.get(CONF_POWER_ENERGY_SECTION, {}))
                if self._heater_room_mapping:
                    section_options[CONF_HEATER_ROOM_MAPPING] = self._heater_room_mapping
                else:
                    section_options.pop(CONF_HEATER_ROOM_MAPPING, None)
                self._pending_options[CONF_POWER_ENERGY_SECTION] = section_options
                return self.async_create_entry(title="", data=self._pending_options)

            self._heater_index += 1
            if self._heater_index >= len(self._heater_devices):
                section_options = dict(self._pending_options.get(CONF_POWER_ENERGY_SECTION, {}))
                if self._heater_room_mapping:
                    section_options[CONF_HEATER_ROOM_MAPPING] = self._heater_room_mapping
                else:
                    section_options.pop(CONF_HEATER_ROOM_MAPPING, None)
                self._pending_options[CONF_POWER_ENERGY_SECTION] = section_options
                return self.async_create_entry(title="", data=self._pending_options)

        heater = self._heater_devices[self._heater_index]
        default_value = _get_default_room_selection(heater, self._heater_room_mapping)
        options = _build_room_options(self._rooms, default_value)
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HEATER_ROOM_ID,
                    default=default_value,
                ): selector.SelectSelector(
                    {
                        "options": options,
                        "mode": selector.SelectSelectorMode.DROPDOWN,
                    }
                ),
                vol.Optional(
                    CONF_HEATER_ROOM_SKIP_REMAINING,
                    default=False,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="heater_mapping",
            data_schema=data_schema,
            description_placeholders={
                "heater": heater.name,
                "index": str(self._heater_index + 1),
                "total": str(len(self._heater_devices)),
            },
        )

    async def _load_mapping_data(self) -> None:
        """Load heaters and rooms for mapping."""
        hub = XComfortHub.get_hub(self.hass, self._config_entry)
        try:
            await asyncio.wait_for(hub.has_done_initial_load.wait(), timeout=5)
        except asyncio.TimeoutError:
            _LOGGER.warning("Timed out waiting for hub data; skipping heater mapping UI")
        devices = list(getattr(hub, "devices", []) or [])
        rooms = list(getattr(hub, "rooms", []) or [])
        self._heater_devices = sorted(
            [device for device in devices if isinstance(device, Heater)],
            key=lambda device: device.name.lower(),
        )
        self._rooms = sorted(
            rooms,
            key=lambda room: room.name.lower(),
        )

    def _update_heater_mapping(self, heater: Heater, selection: str | None) -> None:
        """Store mapping selection for a heater."""
        heater_key = str(heater.device_id)
        if not selection or selection == _AUTO_ROOM_SELECTION:
            self._heater_room_mapping.pop(heater_key, None)
            return
        try:
            self._heater_room_mapping[heater_key] = int(selection)
        except (TypeError, ValueError):
            self._heater_room_mapping.pop(heater_key, None)


_AUTO_ROOM_SELECTION = "auto"


def _normalize_heater_room_mapping(mapping: dict[str, Any]) -> dict[str, int]:
    """Normalize stored heater-room mapping values."""
    normalized: dict[str, int] = {}
    if not isinstance(mapping, dict):
        return normalized
    for heater_id, room_id in mapping.items():
        try:
            normalized[str(int(heater_id))] = int(room_id)
        except (TypeError, ValueError):
            continue
    return normalized


def _get_default_room_selection(heater: Heater, mapping: dict[str, int]) -> str:
    """Return default room selection for a heater."""
    room_id = mapping.get(str(heater.device_id))
    if room_id is None:
        return _AUTO_ROOM_SELECTION
    return str(room_id)


def _build_room_options(rooms: list, default_value: str) -> list[dict[str, str]]:
    """Build room options for the selector."""
    options = [{"value": _AUTO_ROOM_SELECTION, "label": "Auto (name match)"}]
    room_ids = set()
    for room in rooms:
        room_id = str(room.room_id)
        room_ids.add(room_id)
        options.append({"value": room_id, "label": f"{room.name} (id: {room.room_id})"})
    if default_value not in room_ids and default_value != _AUTO_ROOM_SELECTION:
        options.append({"value": default_value, "label": f"Unknown room (id: {default_value})"})
    return options


def _filter_power_section_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return only schema-supported keys for the power/energy section."""
    if not isinstance(options, dict):
        return {}
    allowed_keys = {
        CONF_ADD_ROOM_POWER_SENSORS,
        CONF_ADD_HEATER_POWER_SENSORS,
        CONF_HEATER_POWER_STALE_PROTECTION,
        CONF_ADD_LIGHT_POWER_SENSORS,
    }
    return {key: value for key, value in options.items() if key in allowed_keys}
