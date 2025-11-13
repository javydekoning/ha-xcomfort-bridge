"""Component module for xComfort integration."""
import logging

import rx

_LOGGER = logging.getLogger(__name__)


class CompState:
    """Component state representation."""

    def __init__(self, raw):
        """Initialize component state with raw data."""
        self.raw = raw

    def __str__(self):
        """Return string representation of component state."""
        return f"CompState({self.raw})"

    __repr__ = __str__


class Comp:
    """Component class for xComfort devices."""

    def __init__(self, bridge, comp_id, comp_type, name: str, payload: dict):
        """Initialize component with bridge, ID, type, name and payload."""
        self.bridge = bridge
        self.comp_id = comp_id
        self.comp_type = comp_type
        self.name = name
        self.payload = payload

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        """Handle state updates for this component."""
        _LOGGER.debug("Component %s (type: %s) state update: %s", self.name, self.comp_type, payload)
        self.state.on_next(CompState(payload))

    def __str__(self):
        """Return string representation of component."""
        return f'Comp({self.comp_id}, "{self.name}", comp_type: {self.comp_type}, payload: {self.payload})'

    __repr__ = __str__
