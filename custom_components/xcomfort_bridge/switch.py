"""Support for xComfort appliance switches."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import XComfortHub
from .xcomfort.devices import Appliance
from .xcomfort.device_states import SwitchState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up xComfort appliance switch devices."""
    hub = XComfortHub.get_hub(hass, entry)

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        devices = hub.devices
        _LOGGER.debug("Found %s xcomfort devices", len(devices))

        switches = []
        for device in devices:
            if isinstance(device, Appliance):
                _LOGGER.debug("Adding appliance switch %s", device)
                switches.append(HASSXComfortSwitch(hass, hub, device))

        _LOGGER.debug("Added %s switches", len(switches))
        async_add_entities(switches)

    entry.async_create_task(hass, _wait_for_hub_then_setup())


class HASSXComfortSwitch(SwitchEntity):
    """Entity class for xComfort appliances."""

    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Appliance):
        """Initialize the switch entity."""
        self.hass = hass
        self.hub = hub
        self._device = device
        self._name = device.name
        self._state = None
        self._unique_id = f"switch_{DOMAIN}_{hub.identifier}-{device.device_id}"

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        _LOGGER.debug("Added appliance switch to hass %s", self._name)
        if self._device.state is None:
            _LOGGER.debug("State is null for %s", self._name)
        else:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        """Handle state changes from the device."""
        self._state = state
        if self._state is not None:
            self.schedule_update_ha_state()

    def _set_optimistic_state(self, is_on: bool) -> None:
        """Set optimistic state after successful command send."""
        if self._state is None:
            self._state = SwitchState(is_on, {"switch": is_on})
        else:
            self._state.is_on = is_on
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Eaton",
            "model": "Other appliance",
            "sw_version": "Unknown",
            "via_device": (DOMAIN, self.hub.hub_id),
        }

    @property
    def name(self):
        """Return the display name of this switch."""
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
    def is_on(self):
        """Return true if switch is on."""
        return self._state and self._state.is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning appliance switch on: %s", self._name)
        await self._device.switch(True)
        self._set_optimistic_state(True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning appliance switch off: %s", self._name)
        await self._device.switch(False)
        self._set_optimistic_state(False)
