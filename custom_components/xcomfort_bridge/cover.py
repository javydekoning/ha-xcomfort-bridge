"""Support for xComfort Bridge cover shades."""
import logging

from xcomfort.devices import Shade

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the xComfort Bridge covers from a config entry."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        devices = hub.devices

        _LOGGER.debug("Found %s xcomfort devices", len(devices))

        shades = []
        for device in devices:
            if isinstance(device, Shade):
                _LOGGER.debug("Adding %s", device)
                shade = HASSXComfortShade(hass, hub, device)
                shades.append(shade)

        _LOGGER.debug("Added %s shades", len(shades))
        async_add_entities(shades)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class HASSXComfortShade(CoverEntity):
    """Representation of an xComfort Bridge cover device."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Shade):
        """Initialize the cover device.

        Args:
            hass: The Home Assistant instance
            hub: The xComfort Bridge hub
            device: The shade device

        """
        self.hass = hass
        self.hub = hub

        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id

        self._unique_id = f"shade_{DOMAIN}_{hub.identifier}-{device.device_id}"

    @property
    def device_class(self):
        """Return the class of this device."""
        return CoverDeviceClass.SHADE

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        _LOGGER.debug("Added to hass %s", self._name)  # Changed from f-string
        if self._device.state is None:
            _LOGGER.debug("State is null for %s", self._name)  # Changed from f-string
        else:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        """Handle state changes."""
        self._state = state

        should_update = self._state is not None

        _LOGGER.debug("State changed %s : %s", self._name, state)  # Changed from f-string

        if should_update:
            self.schedule_update_ha_state()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        if not self._state:
            return None
        return self._state.is_closed

    @property
    def device_info(self):
        """Return device information about this entity."""
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
        """Return the display name of this cover."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self._device.supports_go_to:
            supported_features |= CoverEntityFeature.SET_POSITION
        return supported_features

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._device.move_up()

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self._device.move_down()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._device.move_stop()

    def update(self):
        """Update the entity."""

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        if self._state:
            if self._state.position is None:
                return None  # Return None if position is NoneType
            # xcomfort interprets 90% to be almost fully closed,
            # while HASS UI makes 90% look almost open, so we
            # invert.
            return 100 - self._state.position
        return None  # Return None if _state is falsy or does not exist

    async def async_set_cover_position(self, **kwargs) -> None:
        """Move the cover to a specific position."""
        if (position := kwargs.get(ATTR_POSITION)) is not None:
            # See above comment
            position = 100 - position
            await self._device.move_to_position(position)
