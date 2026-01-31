"""Class used to communicate with xComfort bridge."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .xcomfort.bridge import Bridge

_LOGGER = logging.getLogger(__name__)


"""Wrapper class over bridge library to emulate hub."""


class XComfortHub:
    """Hub wrapper for xComfort bridge communication."""

    def __init__(self, hass: HomeAssistant, identifier: str, ip: str, auth_key: str, entry: ConfigEntry):
        """Initialize underlying bridge."""
        bridge = Bridge(ip, auth_key)
        self.hass = hass
        self.bridge = bridge
        self.identifier = identifier
        if self.identifier is None:
            self.identifier = ip
        self.entry = entry
        self._id = entry.unique_id
        self.devices = []
        self._loop = asyncio.get_event_loop()

        self.has_done_initial_load = asyncio.Event()

    def start(self):
        """Start the event loop running the bridge."""
        self.hass.async_create_task(self.bridge.run())

    async def stop(self):
        """Stop the bridge event loop.

        Will also shut down websocket, if open.
        """
        self.has_done_initial_load.clear()
        await self.bridge.close()

    async def load_devices(self):
        """Load devices from bridge."""
        devs = await self.bridge.get_devices()
        self.devices = devs.values()

        _LOGGER.info("loaded %s devices", len(self.devices))
        rooms = await self.bridge.get_rooms()
        self.rooms = rooms.values()

        _LOGGER.info("loaded %s rooms", len(self.rooms))

        scenes = await self.bridge.get_scenes()
        self.scenes = scenes.values()

        _LOGGER.info("loaded %s scenes", len(self.scenes))

        self.has_done_initial_load.set()

    @property
    def hub_id(self) -> str:
        """Return the hub identifier."""
        return self._id

    @property
    def firmware_version(self) -> str | None:
        """Return the firmware version."""
        return getattr(self.bridge, "fw_version", None)

    @property
    def bridge_model(self) -> str | None:
        """Return the bridge model based on bridge type."""
        bridge_type = getattr(self.bridge, "bridge_type", None)
        if bridge_type == 1:
            return "xComfort Bridge"
        if bridge_type is not None:
            return f"xComfort Bridge (Type {bridge_type})"
        return None

    @property
    def bridge_name(self) -> str | None:
        """Return the bridge name."""
        return getattr(self.bridge, "bridge_name", None)

    @property
    def home_scenes_count(self) -> int:
        """Return the number of home scenes."""
        return getattr(self.bridge, "home_scenes_count", 0)

    async def test_connection(self) -> bool:
        """Test if connection to the bridge is working."""
        await asyncio.sleep(1)
        return True

    @staticmethod
    def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> XComfortHub:
        """Get hub instance from Home Assistant data."""
        return hass.data[DOMAIN][entry.entry_id]
