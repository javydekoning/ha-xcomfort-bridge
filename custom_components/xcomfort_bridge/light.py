"""Support for xComfort lights."""

from functools import cached_property
import logging
from math import ceil

from xcomfort.devices import Light

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort light devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        devices = hub.devices

        _LOGGER.debug("Found %s xcomfort devices", len(devices))

        lights = []
        for device in devices:
            if isinstance(device, Light):
                _LOGGER.debug("Adding %s", device)
                light = HASSXComfortLight(hass, hub, device)
                lights.append(light)

        _LOGGER.debug("Added %s lights", len(lights))
        async_add_entities(lights)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class HASSXComfortLight(LightEntity):
    """Entity class for xComfort lights."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Light):
        """Initialize the light entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Light device instance

        """
        self.hass = hass
        self.hub = hub

        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id
        self._unique_id = f"light_{DOMAIN}_{hub.identifier}-{device.device_id}"
        self._color_mode = ColorMode.BRIGHTNESS if self._device.dimmable else ColorMode.ONOFF

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        _LOGGER.debug("Added to hass %s", self._name)
        if self._device.state is None:
            _LOGGER.debug("State is null for %s", self._name)
        else:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        """Handle state changes from the device."""
        self._state = state

        should_update = self._state is not None

        _LOGGER.debug("State changed %s : %s", self._name, state)

        if should_update:
            self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Eaton",
            "model": "XXX",
            "sw_version": "Unknown",
            "via_device": (DOMAIN, self.hub.hub_id),
        }

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return if the entity should be polled for state updates."""
        return False

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return int(255.0 * self._state.dimmvalue / 99.0)

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state and self._state.switch

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return self._color_mode

    @cached_property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        """Return a set of supported color modes."""
        return {self._color_mode}

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("async_turn_on %s : %s", self._name, kwargs)
        if ATTR_BRIGHTNESS in kwargs and self._device.dimmable:
            br = ceil(kwargs[ATTR_BRIGHTNESS] * 99 / 255.0)
            _LOGGER.debug("async_turn_on br %s : %s", self._name, br)
            await self._device.dimm(br)
            self._state.dimmvalue = br
            self.schedule_update_ha_state()
            return

        switch_task = self._device.switch(True)
        await switch_task

        self._state.switch = True
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("async_turn_off %s : %s", self._name, kwargs)
        switch_task = self._device.switch(False)
        await switch_task

        self._state.switch = False
        self.schedule_update_ha_state()

    def update(self):
        """Update the entity."""
