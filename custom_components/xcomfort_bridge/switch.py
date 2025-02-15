"""Support for xComfort switches."""

import logging

from xcomfort.devices import Rocker

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort switch devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        switches = []
        for device in hub.devices:
            if isinstance(device, Rocker):
                _LOGGER.debug("Adding %s", device)
                switch = XComfortSwitch(hass, hub, device)
                switches.append(switch)

        async_add_entities(switches)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class XComfortSwitch(SwitchEntity):
    """Entity class for xComfort switches."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Rocker) -> None:
        """Initialize the switch entity.

        Args:
            hass: HomeAssistant instance
            hub: XComfortHub instance
            device: Rocker device instance

        """
        self.hass = hass
        self.hub = hub

        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id

        self._unique_id = f"switch_{DOMAIN}_{device.device_id}"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._device.state.subscribe(self._state_change)

    def _state_change(self, state) -> None:
        """Handle state changes from the device."""
        self._state = state
        should_update = self._state is not None

        if should_update:
            self.schedule_update_ha_state()
            # Emit event to enable stateless automation, since
            # actual switch state may be same as before
            self.hass.bus.fire(self._unique_id, {"on": state})

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._state

    @property
    def name(self) -> str:
        """Return the display name of this switch."""
        return self._device.name_with_controlled

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        """Return if the entity should be polled for state updates."""
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        raise NotImplementedError

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        raise NotImplementedError
