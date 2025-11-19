"""Shade device for xComfort integration."""

import logging

from .constants import Messages, ShadeOperationState
from .device_base import BridgeDevice
from .device_states import ShadeState

_LOGGER = logging.getLogger(__name__)


class Shade(BridgeDevice):
    """Shade device class."""

    def __init__(self, bridge, device_id, name, comp_id, payload):
        """Initialize shade device."""
        BridgeDevice.__init__(self, bridge, device_id, name)

        self.component = bridge._comps.get(comp_id)  # noqa: SLF001
        self.payload = payload

        # We get partial updates of shade state across different state updates, so
        # we aggregate them via this object
        self.__shade_state = ShadeState()

        self.comp_id = comp_id

    @property
    def supports_go_to(self) -> bool | None:
        """Check if shade supports go to position."""
        # "go to" is whether a specific position can be set, i.e. 50 meaning halfway down
        # Not all actuators support this, even if they can be stopped at arbitrary positions.
        if (component := self.bridge._comps.get(self.comp_id)) is not None:  # noqa: SLF001
            return component.comp_type == 86 and self.payload.get("shRuntime") == 1
        return None

    def handle_state(self, payload):
        """Handle shade state updates."""
        self.__shade_state.update_from_partial_state_update(payload)
        _LOGGER.debug(
            "Shade %s state update: position=%s, current_state=%s, safety=%s",
            self.name,
            self.__shade_state.position,
            self.__shade_state.current_state,
            self.__shade_state.is_safety_enabled,
        )
        self.state.on_next(self.__shade_state)

    async def send_state(self, state, **kw):
        """Send shade state to bridge."""
        if self.__shade_state.is_safety_enabled:
            # Do not trigger changes if safety is on. The official xcomfort client does
            # this check in the client, so we do that too just to be safe.
            _LOGGER.warning("Shade %s: Cannot send state, safety is enabled", self.name)
            return

        _LOGGER.debug("Shade %s: Sending state %s with args %s", self.name, state, kw)
        await self.bridge.send_message(
            Messages.SET_DEVICE_SHADING_STATE,
            {"deviceId": self.device_id, "state": state, **kw},
        )

    async def move_down(self):
        """Move shade down."""
        _LOGGER.debug("Shade %s: Moving down", self.name)
        await self.send_state(ShadeOperationState.CLOSE)

    async def move_up(self):
        """Move shade up."""
        _LOGGER.debug("Shade %s: Moving up", self.name)
        await self.send_state(ShadeOperationState.OPEN)

    async def move_stop(self):
        """Stop shade movement."""
        if self.__shade_state.is_safety_enabled:
            _LOGGER.warning("Shade %s: Cannot stop, safety is enabled", self.name)
            return

        _LOGGER.debug("Shade %s: Stopping", self.name)
        await self.send_state(ShadeOperationState.STOP)

    async def move_to_position(self, position: int):
        """Move shade to specific position."""
        assert self.supports_go_to and 0 <= position <= 100
        _LOGGER.debug("Shade %s: Moving to position %s", self.name, position)
        await self.send_state(ShadeOperationState.GO_TO, value=position)

    def __str__(self) -> str:
        """Return string representation of shade device."""
        return f"<Shade device_id={self.device_id} name={self.name} state={self.state} supports_go_to={self.supports_go_to}>"

