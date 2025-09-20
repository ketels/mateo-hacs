from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
)
from .coordinator import MateoMealsCoordinator, MateoConfig

if TYPE_CHECKING:  # pragma: no cover
    from .coordinator import MateoMealsCoordinator

# Store coordinators per entry_id for refresh service
COORDINATORS: dict[str, MateoMealsCoordinator] = {}

PLATFORMS: list[str] = ["sensor", "calendar"]


async def _handle_refresh_service(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_id = call.data.get("entry_id")
    if entry_id:
        coord = COORDINATORS.get(entry_id)
        if coord:
            await coord.async_request_refresh()
        return
    for coord in list(COORDINATORS.values()):
        await coord.async_request_refresh()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: D401
    services = hass.services.async_services().get(DOMAIN, {})  # type: ignore[attr-defined]
    if "refresh" not in services:
        hass.services.async_register(DOMAIN, "refresh", _handle_refresh_service)
    return True


# Indicate this integration is config-entry only (no YAML options)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: D401
    logger = logging.getLogger(__name__)
    # Build config (prefer options school selection if present)
    data = entry.data
    school_id = int(entry.options.get("school_id", data["school_id"]))
    school_name = entry.options.get("school_name", data["school_name"])  # type: ignore[assignment]
    cfg = MateoConfig(
        slug=data["slug"],
        school_id=school_id,
        school_name=school_name,
        municipality_name=data.get("municipality_name", data["slug"]),
    )
    update_hours = int(entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS))
    coordinator = MateoMealsCoordinator(hass, cfg, update_hours=update_hours)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        logger.warning("Initial Mateo Meals data fetch failed: %s", err)
    COORDINATORS[entry.entry_id] = coordinator
    # Snapshot current options so we can detect which specific values changed later.
    coordinator.options_snapshot = dict(entry.options)  # type: ignore[attr-defined]

    async def _update_listener(hass: HomeAssistant, updated_entry: ConfigEntry) -> None:
        coord = COORDINATORS.get(updated_entry.entry_id)
        if not coord:
            return
        prev_opts = getattr(coord, "options_snapshot", {})  # type: ignore[attr-defined]
        new_opts = updated_entry.options

        # If any non-interval option actually changed value, reload the entry so that
        # entities (day sensors count, calendar days_ahead, school change, serving window)
        # are reconstructed correctly. We avoid a reload when only the update interval changes.
        non_interval_changed = any(
            prev_opts.get(k) != new_opts.get(k)
            for k in new_opts
            if k != CONF_UPDATE_INTERVAL_HOURS
        )
        if non_interval_changed:
            # If days_ahead decreased, proactively remove obsolete day sensors from the entity registry
            try:
                old_days = int(prev_opts.get("days_ahead", 5))
                new_days = int(new_opts.get("days_ahead", 5))
            except Exception:  # noqa: BLE001
                old_days = new_days = 0  # fallback
            if new_days and old_days and new_days < old_days:
                ent_reg = er.async_get(hass)
                # Unique IDs for day sensors follow pattern mateo_meals:slug:school_id:day<offset>
                for entity_id, ent in list(ent_reg.entities.items()):  # type: ignore[attr-defined]
                    if ent.config_entry_id != updated_entry.entry_id:
                        continue
                    if not ent.unique_id.startswith(f"{DOMAIN}:"):
                        continue
                    if ":day" not in ent.unique_id:
                        continue
                    try:
                        offset_str = ent.unique_id.rsplit(":day", 1)[1]
                        offset = int(offset_str)
                    except Exception:  # noqa: BLE001
                        continue
                    if offset >= new_days:
                        ent_reg.async_remove(entity_id)
            coord.options_snapshot = dict(new_opts)  # type: ignore[attr-defined]
            await hass.config_entries.async_reload(updated_entry.entry_id)
            return

        # Otherwise handle a pure polling interval change in-place.
        new_hours = int(new_opts.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS))
        new_hours = max(1, new_hours)
        if not coord.update_interval or coord.update_interval.total_seconds() != new_hours * 3600:
            coord.update_interval = timedelta(hours=new_hours)
            await coord.async_request_refresh()
        coord.options_snapshot = dict(new_opts)  # type: ignore[attr-defined]

    # Attach listener for dynamic option changes.
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: D401
    # Unload platforms first; only drop coordinator if they unloaded cleanly.
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        COORDINATORS.pop(entry.entry_id, None)
    # If no more entries remain, remove the refresh service to be tidy.
    if not COORDINATORS and DOMAIN in hass.services.async_services():  # type: ignore[attr-defined]
        domain_services = hass.services.async_services().get(DOMAIN, {})  # type: ignore[attr-defined]
        if "refresh" in domain_services:
            hass.services.async_remove(DOMAIN, "refresh")
    return unloaded
