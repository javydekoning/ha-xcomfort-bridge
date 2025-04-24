"""Config flow for Eaton xComfort Bridge."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_AUTH_KEY, CONF_IDENTIFIER, CONF_MAC, DOMAIN

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
