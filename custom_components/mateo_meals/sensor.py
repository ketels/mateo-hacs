from __future__ import annotations

import logging
from typing import Any

from datetime import date, datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import COORDINATORS
from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    CONF_DAYS_AHEAD,
    DEFAULT_DAYS_AHEAD,
)
from .coordinator import MateoConfig, MateoMealsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = entry.data
    school_id = int(entry.options.get("school_id", data["school_id"]))
    school_name = entry.options.get("school_name", data["school_name"])  # type: ignore[assignment]
    cfg = MateoConfig(
        slug=data["slug"],
        school_id=school_id,
        school_name=school_name,
        municipality_name=data.get("municipality_name", data["slug"]),
    )
    update_hours = int(
        entry.options.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS)
    )
    coordinator = MateoMealsCoordinator(hass, cfg, update_hours=update_hours)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Initial Mateo Meals data fetch failed: %s", err)
    COORDINATORS[entry.entry_id] = coordinator
    days_ahead = int(entry.options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))
    base_sensor = MateoMealsSensor(coordinator, cfg, entry.entry_id)
    day_sensors: list[SensorEntity] = []
    for offset in range(days_ahead):
        day_sensors.append(MateoMealsFixedDaySensor(coordinator, cfg, entry.entry_id, offset))
    _LOGGER.debug(
        "Adding Mateo Meals sensors (%d day sensors + base) for school %s (entry %s)",
        len(day_sensors),
        cfg.school_name,
        entry.entry_id,
    )
    async_add_entities([base_sensor, *day_sensors])


class MateoMealsSensor(CoordinatorEntity[MateoMealsCoordinator], SensorEntity):
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator: MateoMealsCoordinator, cfg: MateoConfig, entry_id: str) -> None:
        super().__init__(coordinator)
        self._cfg = cfg
        self._attr_unique_id = f"{DOMAIN}:{cfg.slug}:{cfg.school_id}"
        self._attr_name = f"Skollunch – {cfg.school_name}"
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        meals = data.get("today_meals") or []
        if not meals:
            # Default to Swedish then English phrase if translations not wired
            return "Ingen meny idag" if self._cfg.municipality_name else "No menu today"
        if meals and isinstance(meals[0], str):
            names = [m for m in meals if isinstance(m, str) and m]
        else:
            names = [m.get("name") for m in meals if isinstance(m, dict) and m.get("name")]
        return "; ".join(names) if names else "No menu today"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        # Expose only minimal attributes to avoid large attribute payload warnings.
        data = self.coordinator.data or {}
        meals_today = data.get("today_meals") or []
        meals_by_date = data.get("meals_by_date") or {}
        # Provide a compact upcoming mapping for next 5 weekdays including today.
        try:
            utc = datetime.UTC  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover
            from datetime import timezone as _tz
            utc = _tz.utc
        today = datetime.now(utc).date()
        upcoming: dict[str, list[str]] = {}
        for i in range(5):
            d = today + timedelta(days=i)
            key = d.isoformat()
            if key in meals_by_date:
                upcoming[key] = meals_by_date[key]
        return {
            "today_date": data.get("today_date"),
            "today_meals": meals_today,
            "upcoming_meals": upcoming,
            "exception_days_count": len(data.get("exception_days") or []),
        }

    # Rely on Home Assistant's default entity_id generation (no override)


class MateoMealsFixedDaySensor(CoordinatorEntity[MateoMealsCoordinator], SensorEntity):
    _attr_icon = "mdi:food-hot-dog"

    def __init__(
        self,
        coordinator: MateoMealsCoordinator,
        cfg: MateoConfig,
        entry_id: str,
        day_offset: int,
    ) -> None:
        super().__init__(coordinator)
        self._cfg = cfg
        self._day_offset = day_offset
        self._attr_unique_id = f"{DOMAIN}:{cfg.slug}:{cfg.school_id}:day{day_offset}"
        label = "today" if day_offset == 0 else f"day{day_offset}"
        self._attr_name = f"Skollunch – {cfg.school_name} – {label}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        meals_by_date = data.get("meals_by_date") or {}
        # Determine target date (UTC date basis as coordinator uses UTC date())
        try:
            utc = datetime.UTC  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover
            from datetime import timezone as _tz

            utc = _tz.utc
        today = datetime.now(utc).date()
        target: date = today + timedelta(days=self._day_offset)
        meals = meals_by_date.get(target.isoformat()) or []
        if not meals:
            return None
        if isinstance(meals, list):
            names = [m for m in meals if isinstance(m, str) and m]
        else:  # defensive
            return None
        return "; ".join(names) if names else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Provide the date this sensor represents
        try:
            utc = datetime.UTC  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover
            from datetime import timezone as _tz

            utc = _tz.utc
        today = datetime.now(utc).date()
        target = today + timedelta(days=self._day_offset)
        return {"date": target.isoformat(), "offset": self._day_offset}
