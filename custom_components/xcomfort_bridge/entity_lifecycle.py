"""Helpers for safe Rx subscriptions on Home Assistant entities."""

from __future__ import annotations

from collections import defaultdict
import logging
from typing import Any

from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

_DROP_LOG_COUNTS = {1, 2, 3, 5, 10, 25, 50, 100}


def init_entity_lifecycle(entity: Entity) -> None:
    """Initialize per-entity lifecycle bookkeeping for Rx subscriptions."""
    setattr(entity, "_xcomfort_rx_attached", False)
    setattr(entity, "_xcomfort_rx_pre_attach_drops", defaultdict(int))


def mark_entity_added(entity: Entity) -> None:
    """Mark an entity as attached and ready for HA state writes."""
    if not hasattr(entity, "_xcomfort_rx_attached"):
        init_entity_lifecycle(entity)

    setattr(entity, "_xcomfort_rx_attached", True)
    entity.async_on_remove(lambda: setattr(entity, "_xcomfort_rx_attached", False))

    _LOGGER.debug("Entity attached for Rx updates: %s", _describe_entity(entity))


def subscribe_observable(entity: Entity, observable: Any, callback: Any, source_name: str) -> None:
    """Subscribe an attached entity to an Rx observable and auto-dispose on removal."""
    if observable is None:
        _LOGGER.debug("Skipping Rx subscription for %s: %s is None", _describe_entity(entity), source_name)
        return

    _LOGGER.debug("Subscribing %s to %s", _describe_entity(entity), source_name)
    disposable = observable.subscribe(callback)
    entity.async_on_remove(disposable.dispose)


def async_write_state_safely(entity: Entity, source_name: str) -> bool:
    """Write entity state to HA with lifecycle guards and instrumentation."""
    return _write_state_safely(entity, source_name=source_name, schedule=False)


def schedule_state_update_safely(entity: Entity, source_name: str) -> bool:
    """Schedule entity state update with lifecycle guards and instrumentation."""
    return _write_state_safely(entity, source_name=source_name, schedule=True)


def _write_state_safely(entity: Entity, source_name: str, schedule: bool) -> bool:
    if not hasattr(entity, "_xcomfort_rx_attached"):
        init_entity_lifecycle(entity)

    if not getattr(entity, "_xcomfort_rx_attached", False):
        _record_pre_attach_drop(entity, source_name)
        return False

    try:
        if schedule:
            entity.schedule_update_ha_state()
        else:
            entity.async_write_ha_state()
    except Exception:
        action = "schedule_update_ha_state" if schedule else "async_write_ha_state"
        _LOGGER.exception(
            "State write failure for %s from %s using %s",
            _describe_entity(entity),
            source_name,
            action,
        )
        return False

    return True


def _record_pre_attach_drop(entity: Entity, source_name: str) -> None:
    drops: defaultdict[str, int] = getattr(entity, "_xcomfort_rx_pre_attach_drops")
    drops[source_name] += 1
    count = drops[source_name]

    if count in _DROP_LOG_COUNTS or count % 250 == 0:
        _LOGGER.warning(
            "Dropping pre-attach state update for %s from %s (drop_count=%s)",
            _describe_entity(entity),
            source_name,
            count,
        )


def _describe_entity(entity: Entity) -> str:
    unique_id = getattr(entity, "unique_id", None) or getattr(entity, "_attr_unique_id", None)
    entity_id = getattr(entity, "entity_id", None)
    return f"{entity.__class__.__name__}(entity_id={entity_id}, unique_id={unique_id})"
