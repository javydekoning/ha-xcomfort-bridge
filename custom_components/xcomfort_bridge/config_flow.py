"""Config flow for Eaton xComfort Bridge."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import (
    AUTH_MODE_DEVICE,
    AUTH_MODE_USER,
    CONF_ADD_APPLIANCE_POWER_SENSORS,
    CONF_ADD_HEATER_POWER_SENSORS,
    CONF_ADD_LIGHT_POWER_SENSORS,
    CONF_ADD_ROOM_POWER_SENSORS,
    CONF_AUTH_KEY,
    CONF_AUTH_MODE,
    CONF_IDENTIFIER,
    CONF_MAC,
    CONF_POWER_ENERGY_SECTION,
    CONF_USERNAME,
    DEFAULT_DEVICE_USERNAME,
    DOMAIN,
)
from .xcomfort.connection import InvalidAuth, setup_secure_connection

_LOGGER = logging.getLogger(__name__)

# Labels shown in the auth-mode dropdown. Keys are the CONF_AUTH_MODE values
# written into the config entry.
_AUTH_MODE_LABELS = {
    AUTH_MODE_DEVICE: "Device auth code (default)",
    AUTH_MODE_USER: "Named user account",
}


def _mode_schema(
    *,
    include_ip: bool,
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build the initial schema: IP (optional), identifier, auth mode."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}
    if include_ip:
        fields[
            vol.Required(CONF_IP_ADDRESS, default=defaults.get(CONF_IP_ADDRESS, ""))
        ] = str
    fields[
        vol.Optional(
            CONF_IDENTIFIER, default=defaults.get(CONF_IDENTIFIER, "XComfort Bridge")
        )
    ] = str
    fields[
        vol.Required(
            CONF_AUTH_MODE, default=defaults.get(CONF_AUTH_MODE, AUTH_MODE_DEVICE)
        )
    ] = vol.In(_AUTH_MODE_LABELS)
    return vol.Schema(fields)


def _credentials_schema(
    auth_mode: str, defaults: dict[str, Any] | None = None
) -> vol.Schema:
    """Build the credentials schema — username only shown in user mode."""
    defaults = defaults or {}
    fields: dict[Any, Any] = {}
    if auth_mode == AUTH_MODE_USER:
        fields[vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, ""))] = (
            str
        )
    fields[vol.Required(CONF_AUTH_KEY, default=defaults.get(CONF_AUTH_KEY, ""))] = str
    return vol.Schema(fields)


async def _validate_credentials(
    hass, ip: str, auth_key: str, username: str
) -> str | None:
    """Probe the bridge with the given credentials.

    Returns an error code ("invalid_auth" / "cannot_connect") suitable for
    `async_show_form(errors=...)`, or None on success.
    """
    session = async_get_clientsession(hass)
    try:
        connection = await setup_secure_connection(session, ip, auth_key, username)
    except InvalidAuth:
        _LOGGER.warning("Bridge at %s rejected credentials for user '%s'", ip, username)
        return "invalid_auth"
    except (ConnectionError, OSError) as err:
        _LOGGER.warning("Could not reach bridge at %s: %r", ip, err)
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error while validating bridge credentials")
        return "cannot_connect"
    else:
        # Handshake succeeded — close the probe connection; the integration
        # will open its own long-lived one during entry setup.
        await connection.close()
        return None


@config_entries.HANDLERS.register(DOMAIN)
class XComfortBridgeConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Eaton xComfort Bridge."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle dhcp discovery."""
        ip = discovery_info.ip
        mac = format_mac(discovery_info.macaddress)
        await self.async_set_unique_id(mac)

        for entry in self._async_current_entries():
            if (configured_mac := entry.data.get(CONF_MAC)) is not None and format_mac(
                configured_mac
            ) == mac:
                if (old_ip := entry.data.get(CONF_IP_ADDRESS)) != ip:
                    _LOGGER.info(
                        "Bridge has changed IP-address. Configuring new IP and restarting. [mac=%s, new_ip=%s, old_ip=%s]",
                        mac,
                        ip,
                        old_ip,
                    )
                    self.hass.config_entries.async_update_entry(
                        entry, data=entry.data | {CONF_IP_ADDRESS: ip}, title=self.title
                    )
                    self.hass.async_create_task(
                        self.hass.config_entries.async_reload(entry.entry_id)
                    )
                return self.async_abort(reason="already_configured")
            if (
                entry.data.get(CONF_MAC) is None
                and entry.data.get(CONF_IP_ADDRESS) == ip
            ):
                _LOGGER.info("Saved MAC-address for bridge [mac=%s, ip=%s]", mac, ip)
                self.hass.config_entries.async_update_entry(
                    entry, data=entry.data | {CONF_MAC: mac}
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
                return self.async_abort(reason="already_configured")

        # TODO: Does it actually look like an xcomfort bridge?

        self.data[CONF_MAC] = mac
        self.data[CONF_IP_ADDRESS] = ip

        return await self.async_step_auth()

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect identifier + auth mode for a DHCP-discovered bridge."""
        if user_input is not None:
            self.data[CONF_IDENTIFIER] = user_input.get(CONF_IDENTIFIER)
            self.data[CONF_AUTH_MODE] = user_input[CONF_AUTH_MODE]
            return await self.async_step_credentials()

        return self.async_show_form(
            step_id="auth", data_schema=_mode_schema(include_ip=False)
        )

    async def async_step_user(self, user_input=None):
        """Collect host + identifier + auth mode for a manually-added bridge."""
        if user_input is not None:
            self.data[CONF_IP_ADDRESS] = user_input[CONF_IP_ADDRESS]
            self.data[CONF_IDENTIFIER] = user_input.get(CONF_IDENTIFIER)
            self.data[CONF_AUTH_MODE] = user_input[CONF_AUTH_MODE]
            return await self.async_step_credentials()

        return self.async_show_form(
            step_id="user", data_schema=_mode_schema(include_ip=True)
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect and validate the secret (and username in user mode)."""
        auth_mode = self.data.get(CONF_AUTH_MODE, AUTH_MODE_DEVICE)
        errors: dict[str, str] = {}

        if user_input is not None:
            username = (
                user_input[CONF_USERNAME].strip()
                if auth_mode == AUTH_MODE_USER
                else DEFAULT_DEVICE_USERNAME
            )
            auth_key = user_input[CONF_AUTH_KEY].strip()

            if auth_mode == AUTH_MODE_USER and not username:
                errors["base"] = "username_required"
            elif not auth_key:
                errors["base"] = "secret_required"
            else:
                error = await _validate_credentials(
                    self.hass, self.data[CONF_IP_ADDRESS], auth_key, username
                )
                if error is None:
                    self.data[CONF_AUTH_KEY] = auth_key
                    self.data[CONF_USERNAME] = username

                    # Only set the composite unique_id if DHCP didn't already
                    # provide a MAC-based one.
                    if self.unique_id is None:
                        await self.async_set_unique_id(
                            f"{self.data.get(CONF_IDENTIFIER)}/"
                            f"{self.data[CONF_IP_ADDRESS]}"
                        )
                    return self.async_create_entry(title=self.title, data=self.data)
                errors["base"] = error

        return self.async_show_form(
            step_id="credentials",
            data_schema=_credentials_schema(auth_mode, user_input),
            errors=errors,
            description_placeholders={"auth_mode": _AUTH_MODE_LABELS[auth_mode]},
        )

    async def async_step_import(self, import_data: dict):
        """Handle import from configuration.yaml — legacy device-mode only."""
        # Imports predate auth-mode support; preserve the device-code flow.
        self.data[CONF_IP_ADDRESS] = import_data[CONF_IP_ADDRESS]
        self.data[CONF_IDENTIFIER] = import_data.get(CONF_IDENTIFIER)
        self.data[CONF_AUTH_MODE] = AUTH_MODE_DEVICE
        self.data[CONF_AUTH_KEY] = import_data[CONF_AUTH_KEY]
        self.data[CONF_USERNAME] = DEFAULT_DEVICE_USERNAME
        return self.async_create_entry(title=self.title, data=self.data)

    @property
    def title(self) -> str:
        """Return the title of the config entry."""
        return self.data.get(
            CONF_IDENTIFIER,
            self.data.get(CONF_MAC, self.data.get(CONF_IP_ADDRESS, "Untitled")),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow for this handler."""
        return XComfortBridgeOptionsFlowHandler(config_entry)


class XComfortBridgeOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle options flow for Eaton xComfort Bridge."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options for the config entry."""
        if user_input is not None:
            options = dict(self._config_entry.options)
            section_options = dict(options.get(CONF_POWER_ENERGY_SECTION, {}))
            section_options.update(user_input.get(CONF_POWER_ENERGY_SECTION, {}))
            options[CONF_POWER_ENERGY_SECTION] = _filter_power_section_options(
                section_options
            )
            return self.async_create_entry(title="", data=options)

        options = self._config_entry.options
        section_options = _filter_power_section_options(
            options.get(CONF_POWER_ENERGY_SECTION, {})
        )
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
                                default=section_options.get(
                                    CONF_ADD_ROOM_POWER_SENSORS, True
                                ),
                            ): bool,
                            vol.Optional(
                                CONF_ADD_HEATER_POWER_SENSORS,
                                default=section_options.get(
                                    CONF_ADD_HEATER_POWER_SENSORS, False
                                ),
                            ): bool,
                            vol.Optional(
                                CONF_ADD_LIGHT_POWER_SENSORS,
                                default=section_options.get(
                                    CONF_ADD_LIGHT_POWER_SENSORS, False
                                ),
                            ): bool,
                            vol.Optional(
                                CONF_ADD_APPLIANCE_POWER_SENSORS,
                                default=section_options.get(
                                    CONF_ADD_APPLIANCE_POWER_SENSORS, False
                                ),
                            ): bool,
                        }
                    ),
                    {"collapsed": False},
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


def _filter_power_section_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return only schema-supported keys for the power/energy section."""
    if not isinstance(options, dict):
        return {}
    allowed_keys = {
        CONF_ADD_ROOM_POWER_SENSORS,
        CONF_ADD_HEATER_POWER_SENSORS,
        CONF_ADD_LIGHT_POWER_SENSORS,
        CONF_ADD_APPLIANCE_POWER_SENSORS,
    }
    return {key: value for key, value in options.items() if key in allowed_keys}
