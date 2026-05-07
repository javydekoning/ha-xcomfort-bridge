"""Component module for xComfort integration."""

from __future__ import annotations

import logging

import rx

_LOGGER = logging.getLogger(__name__)

# Info-array text codes used for component-level status. Values are the
# i18n keys from the official app's en.json (see CLAUDE.md protocol notes).
# NOTE: Device temperature (1109) lives on the per-channel device payload,
# not on the component — handled in BridgeDevice, not here.
_INFO_CODE_SIGNAL_QUALITY = "1111"
_INFO_CODE_MAINS_POWERED = "1119"
# Signal quality payload values map to human-readable labels. The label
# strings are paraphrased from the app's 11110-11114 i18n keys (which
# are the per-value labels — our keys 1111{value} are joined here).
_SIGNAL_QUALITY_LABELS: dict[str, str] = {
    "0": "Unknown",
    "1": "Excellent",
    "2": "Good",
    "3": "Fair",
    "4": "Poor",
}
# Battery-level text codes → percentage bucket (i18n keys 1113-1117).
_BATTERY_CODE_TO_PERCENT: dict[str, int] = {
    "1113": 0,
    "1114": 25,
    "1115": 50,
    "1116": 75,
    "1117": 100,
}


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
        # Keep the most recent payload on the instance so info[] lookups
        # continue to work even between state events (subscribers may also
        # get a stale reference to the initial payload).
        self.payload = payload
        _LOGGER.debug(
            "Component %s (type: %s) state update: %s",
            self.name,
            self.comp_type,
            payload,
        )
        self.state.on_next(CompState(payload))

    def _info_items(self) -> list[dict]:
        """Return the current info[] array, or [] if not present."""
        return self.payload.get("info", []) if isinstance(self.payload, dict) else []

    @property
    def signal_quality_label(self) -> str | None:
        """Return the signal quality label (e.g. "Good"), or None if absent.

        Extracted from the component's info[] array under text code
        `INFO_CODE_SIGNAL_QUALITY` (1111). The numeric value 0-4 is mapped
        to a human-readable label to match how the app displays it.
        """
        for item in self._info_items():
            if str(item.get("text", "")) == _INFO_CODE_SIGNAL_QUALITY:
                return _SIGNAL_QUALITY_LABELS.get(str(item.get("value", "")))
        return None

    @property
    def battery_percent(self) -> int | None:
        """Return battery level as percent bucket, or None if unknown/mains.

        The bridge doesn't report exact percentages; it uses one of five
        text codes (1113-1117) meaning Empty/Weak/Medium/Good/Full. Those
        are mapped to 0/25/50/75/100 — rough but comparable to the app.
        """
        for item in self._info_items():
            code = str(item.get("text", ""))
            if code in _BATTERY_CODE_TO_PERCENT:
                return _BATTERY_CODE_TO_PERCENT[code]
        return None

    @property
    def is_mains_powered(self) -> bool:
        """Return True if the component reports mains power (no battery)."""
        return any(
            str(item.get("text", "")) == _INFO_CODE_MAINS_POWERED
            for item in self._info_items()
        )

    def __str__(self):
        """Return string representation of component."""
        return f'Comp({self.comp_id}, "{self.name}", comp_type: {self.comp_type}, payload: {self.payload})'

    __repr__ = __str__
