"""Provides device automations for xComfort button events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_ENTITY_ID, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import BUTTON_EVENT, DOMAIN

CONF_SUBTYPE = "subtype"
EVENT_TYPE_KEY = "event_type"
SUPPORTED_TRIGGER_TYPES = {
    "press_up",
    "press_down",
    "double_press_up",
    "double_press_down",
    "on",
    "off",
}
DEFAULT_TRIGGER_TYPES = [
    "press_up",
    "press_down",
    "double_press_up",
    "double_press_down",
    "on",
    "off",
]

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(SUPPORTED_TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): str,
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
    }
)


@callback
def _get_event_entities_for_device(
    hass: HomeAssistant, device_id: str
) -> list[er.RegistryEntry]:
    """Return xComfort event entities attached to the given device."""
    entity_registry = er.async_get(hass)
    return [
        entry
        for entry in er.async_entries_for_device(entity_registry, device_id)
        if entry.domain == "event"
        and entry.disabled_by is None
        and (entry.platform == DOMAIN or (entry.unique_id or "").startswith(f"event_{DOMAIN}_"))
    ]


@callback
def _get_entity_trigger_types(
    hass: HomeAssistant,
    entity_id: str,
    capabilities: Mapping[str, Any] | None = None,
) -> list[str]:
    """Return supported trigger types for an event entity."""
    if capabilities:
        capability_event_types = capabilities.get("event_types")
        if isinstance(capability_event_types, list):
            valid_types = [
                trigger_type
                for trigger_type in capability_event_types
                if trigger_type in SUPPORTED_TRIGGER_TYPES
            ]
            if valid_types:
                return valid_types

    state = hass.states.get(entity_id)
    if state is None:
        return DEFAULT_TRIGGER_TYPES

    entity_event_types = state.attributes.get("event_types")
    if not isinstance(entity_event_types, list):
        return DEFAULT_TRIGGER_TYPES

    valid_types = [trigger_type for trigger_type in entity_event_types if trigger_type in SUPPORTED_TRIGGER_TYPES]
    return valid_types or DEFAULT_TRIGGER_TYPES


@callback
def _get_entity_subtype(hass: HomeAssistant, entry: er.RegistryEntry) -> str:
    """Return a human-readable subtype label for trigger UI."""
    if entry.entity_id:
        state = hass.states.get(entry.entity_id)
        if state:
            friendly_name = state.attributes.get("friendly_name")
            if isinstance(friendly_name, str) and friendly_name.strip():
                return friendly_name

    if entry.name:
        return entry.name
    if entry.original_name:
        return entry.original_name

    if entry.entity_id:
        return entry.entity_id.split(".", 1)[1]
    return entry.unique_id or "button"


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate trigger config."""
    config = TRIGGER_SCHEMA(config)

    entity_entries = _get_event_entities_for_device(hass, config[CONF_DEVICE_ID])
    matching_entity = next(
        (entry for entry in entity_entries if entry.entity_id == config[CONF_ENTITY_ID]),
        None,
    )
    if matching_entity is None:
        raise InvalidDeviceAutomationConfig("Entity is not a valid xComfort event entity for this device")

    if config[CONF_TYPE] not in _get_entity_trigger_types(
        hass,
        config[CONF_ENTITY_ID],
        matching_entity.capabilities,
    ):
        raise InvalidDeviceAutomationConfig(
            f"Entity {config[CONF_ENTITY_ID]} does not support trigger type {config[CONF_TYPE]}"
        )

    return config


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for xComfort button events based on configuration."""
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: BUTTON_EVENT,
            event_trigger.CONF_EVENT_DATA: {
                CONF_ENTITY_ID: config[CONF_ENTITY_ID],
                EVENT_TYPE_KEY: config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    """List device triggers for xComfort event entities."""
    triggers: list[dict[str, Any]] = []
    entity_entries = sorted(
        _get_event_entities_for_device(hass, device_id),
        key=lambda entry: entry.entity_id or entry.unique_id or "",
    )

    for entry in entity_entries:
        if not entry.entity_id:
            continue
        subtype = _get_entity_subtype(hass, entry)
        for trigger_type in _get_entity_trigger_types(hass, entry.entity_id, entry.capabilities):
            triggers.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_PLATFORM: "device",
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: trigger_type,
                    CONF_SUBTYPE: subtype,
                }
            )

    return triggers
