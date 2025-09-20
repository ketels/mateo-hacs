from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
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

    async def _update_listener(updated_entry: ConfigEntry) -> None:
        coord = COORDINATORS.get(updated_entry.entry_id)
        if not coord:
            return
        # Adjust polling interval dynamically if user changed update interval hours.
        new_hours = int(
            updated_entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS)
        )
        new_hours = max(1, new_hours)
        # Only update if changed to avoid resetting loop unnecessarily.
        if coord.update_interval and coord.update_interval.total_seconds() == new_hours * 3600:
            return
        coord.update_interval = timedelta(hours=new_hours)
        # Force a refresh so new schedule has fresh data soon.
        await coord.async_request_refresh()

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
