from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

if TYPE_CHECKING:  # pragma: no cover
    from .coordinator import MateoMealsCoordinator

# Store coordinators per entry_id for refresh service
COORDINATORS: dict[str, MateoMealsCoordinator] = {}

PLATFORMS: list[str] = ["sensor"]


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: D401
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: D401
    COORDINATORS.pop(entry.entry_id, None)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
