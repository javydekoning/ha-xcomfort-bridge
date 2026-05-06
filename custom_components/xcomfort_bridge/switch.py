"""Support for xComfort appliance switches."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity_lifecycle import (
    init_entity_lifecycle,
    mark_entity_added,
    schedule_state_update_safely,
    subscribe_observable,
)
from .hub import XComfortHub
from .xcomfort.device_states import SwitchState
from .xcomfort.devices import Appliance

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up xComfort appliance switch devices."""
    hub = XComfortHub.get_hub(hass, entry)

    # Bridge-level toggles are available as soon as the hub exists — don't
    # wait for device enumeration. The entity reads its own state from the
    # Rx observable, which resolves once the first SET_BRIDGE_DATA arrives.
    async_add_entities([XComfortRemoteAccessSwitch(hub)])

    async def _wait_for_hub_then_setup():
        await hub.has_done_initial_load.wait()

        appliances = hub.get_appliances()
        _LOGGER.debug("Found %s xcomfort appliances", len(appliances))

        switches = [HASSXComfortSwitch(hass, hub, device) for device in appliances]
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
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        mark_entity_added(self)
        _LOGGER.debug("Added appliance switch to hass %s", self._name)
        subscribe_observable(
            self, self._device.state, self._state_change, "device.state"
        )

    def _state_change(self, state):
        """Handle state changes from the device."""
        self._state = state
        if self._state is not None:
            schedule_state_update_safely(self, "device.state")

    def _set_optimistic_state(self, is_on: bool) -> None:
        """Set optimistic state after successful command send."""
        if self._state is None:
            self._state = SwitchState(is_on, None, {"switch": is_on})
        else:
            self._state.is_on = is_on
            if not is_on:
                self._state.power = 0.0
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


class XComfortRemoteAccessSwitch(SwitchEntity):
    """Switch exposing the bridge's 'Allow Remote Access' setting.

    Mirrors the toggle in the official Eaton app: when on, the bridge is
    permitted to establish an outbound cloud connection to Eaton's
    web-connect relay. State is pushed via SET_BRIDGE_DATA; the toggle
    sends SET_REMOTE_CONFIG.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-lock-outline"
    _attr_name = "Allow Remote Access"

    def __init__(self, hub: XComfortHub):
        """Initialize the remote-access switch bound to the hub device."""
        self.hub = hub
        self._is_on: bool | None = None
        self._attr_unique_id = f"{hub.hub_id}_remote_access"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, hub.hub_id)})
        init_entity_lifecycle(self)

    async def async_added_to_hass(self):
        """Subscribe to bridge state once the entity is live."""
        await super().async_added_to_hass()
        mark_entity_added(self)
        subscribe_observable(
            self,
            self.hub.bridge.remote_allowed,
            self._on_remote_allowed,
            "bridge.remote_allowed",
        )

    def _on_remote_allowed(self, value: bool | None) -> None:
        if value is None:
            return
        self._is_on = bool(value)
        schedule_state_update_safely(self, "bridge.remote_allowed")

    @property
    def should_poll(self) -> bool:
        """Return False — state is pushed via Rx observable."""
        return False

    @property
    def available(self) -> bool:
        """Available once the bridge has reported its current remote-access state."""
        return self._is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if remote access is currently allowed."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Enable remote access on the bridge."""
        await self.hub.bridge.set_remote_access(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable remote access on the bridge."""
        await self.hub.bridge.set_remote_access(False)
