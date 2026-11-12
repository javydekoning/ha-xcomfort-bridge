"""Class used to communicate with xComfort bridge."""

from __future__ import annotations

import asyncio
import logging
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .xcomfort.bridge import Bridge
from .xcomfort.devices import (
    Appliance,
    DoorSensor,
    DoorWindowSensor,
    Heater,
    HeatingValve,
    Light,
    RcTouch,
    Rocker,
    Shade,
    WindowSensor,
)

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


"""Wrapper class over bridge library to emulate hub."""


class XComfortHub:
    """Hub wrapper for xComfort bridge communication."""

    def __init__(
        self,
        hass: HomeAssistant,
        identifier: str,
        ip: str,
        auth_key: str,
        entry: ConfigEntry,
        username: str = "default",
    ):
        """Initialize underlying bridge."""
        bridge = Bridge(ip, auth_key, username=username)
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
        """Return the total number of scenes defined on the bridge.

        Named `home_scenes_count` for backwards compatibility with the
        existing sensor's unique_id. Prior versions read this from
        `homeScenes` in SET_BRIDGE_DATA, which is a 4-slot quick-access
        dashboard array — misleading as a general count. Now reads the
        actual scenes dict.
        """
        return getattr(self.bridge, "scenes_count", 0)

    @property
    def dashboard_scene_slots_used(self) -> int:
        """Return number of non-empty quick-access dashboard scene slots.

        The bridge exposes a 4-slot `homeScenes` array; zeros mean empty.
        """
        return sum(1 for sid in getattr(self.bridge, "home_scene_ids", []) if sid)

    # --- Typed device-query helpers --------------------------------------
    #
    # Platforms used to filter `hub.devices` with `isinstance(...)` inline.
    # That pattern left the device-type vocabulary duplicated across every
    # platform file and made `hub.devices` an untyped `dict_values`. The
    # helpers below centralise the filtering and give platforms a typed
    # return value, so e.g. `light.py` can iterate `hub.get_lights()`
    # directly without importing the model class.

    def _devices_of_type(self, device_cls: type[_T]) -> list[_T]:
        """Return all devices that are an instance of device_cls."""
        return [d for d in self.devices if isinstance(d, device_cls)]

    def get_lights(self) -> list[Light]:
        """Return all light devices."""
        return self._devices_of_type(Light)

    def get_appliances(self) -> list[Appliance]:
        """Return all appliance (switchable load) devices."""
        return self._devices_of_type(Appliance)

    def get_shades(self) -> list[Shade]:
        """Return all shade (cover) devices."""
        return self._devices_of_type(Shade)

    def get_heaters(self) -> list[Heater]:
        """Return all heater devices (electric heating actuators)."""
        return self._devices_of_type(Heater)

    def get_heating_valves(self) -> list[HeatingValve]:
        """Return all heating-valve devices."""
        return self._devices_of_type(HeatingValve)

    def get_rctouches(self) -> list[RcTouch]:
        """Return all RC-Touch room controllers."""
        return self._devices_of_type(RcTouch)

    def get_rockers(self) -> list[Rocker]:
        """Return all rocker (pushbutton/remote channel) devices."""
        return self._devices_of_type(Rocker)

    def get_multisensor_rockers(self) -> list[Rocker]:
        """Return only rockers that also carry temp/humidity sensors."""
        return [r for r in self.get_rockers() if r.has_sensors]

    def get_window_sensors(self) -> list[WindowSensor]:
        """Return all window sensors."""
        return self._devices_of_type(WindowSensor)

    def get_door_sensors(self) -> list[DoorSensor]:
        """Return all door sensors."""
        return self._devices_of_type(DoorSensor)

    def get_door_window_sensors(self) -> list[DoorWindowSensor]:
        """Return all door/window sensors (both door and window variants)."""
        return self._devices_of_type(DoorWindowSensor)

    def get_primary_devices_per_component(self) -> list:
        """Return one representative device per physical component.

        A component (e.g. a 4-channel pushbutton) exposes multiple device
        channels, but attributes like signal quality and battery level live
        at the component level and should produce a single HA entity — not
        one per channel. The "primary" device per component is deterministic
        (lowest device_id with a comp_id) so the resulting entities are
        stable across restarts.
        """
        seen_comps: set = set()
        primaries: list = []
        for device in sorted(self.devices, key=lambda d: getattr(d, "device_id", 0)):
            comp_id = getattr(device, "comp_id", None)
            if comp_id is None or comp_id in seen_comps:
                continue
            seen_comps.add(comp_id)
            primaries.append(device)
        return primaries

    def get_components_with_signal(self) -> list:
        """Return primary devices whose component reports signal quality."""
        return [
            d
            for d in self.get_primary_devices_per_component()
            if (comp := self.bridge.comps.get(d.comp_id)) is not None
            and comp.signal_quality_label is not None
        ]

    def get_components_with_battery(self) -> list:
        """Return primary devices whose component reports a battery level.

        Mains-powered components are excluded, matching the app's UI
        (battery tile only appears on battery-powered hardware).
        """
        result = []
        for d in self.get_primary_devices_per_component():
            comp = self.bridge.comps.get(d.comp_id)
            if comp is None:
                continue
            if comp.is_mains_powered:
                continue
            if comp.battery_percent is None:
                continue
            result.append(d)
        return result

    def get_devices_with_device_temperature(self) -> list:
        """Return devices whose payload reports internal device temperature.

        Device temperature (info code 1109) is a per-channel reading — the
        silicon/die temperature used by the device for overload protection.
        Discovered dynamically from the latest payload rather than
        hardcoded by device type, so any future hardware that reports 1109
        picks up a sensor automatically.
        """
        return [d for d in self.devices if d.device_temperature_c is not None]

    # ---------------------------------------------------------------------

    async def test_connection(self) -> bool:
        """Test if connection to the bridge is working."""
        await asyncio.sleep(1)
        return True

    @staticmethod
    def get_hub(hass: HomeAssistant, entry: ConfigEntry) -> XComfortHub:
        """Get hub instance from Home Assistant data."""
        return hass.data[DOMAIN][entry.entry_id]
