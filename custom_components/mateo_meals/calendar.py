from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Iterable

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import COORDINATORS
from .const import (
    DOMAIN,
    CONF_SERVING_START,
    CONF_SERVING_END,
    CONF_DAYS_AHEAD,
    CONF_INCLUDE_WEEKENDS,
    DEFAULT_SERVING_START,
    DEFAULT_SERVING_END,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_INCLUDE_WEEKENDS,
)
from .coordinator import MateoMealsCoordinator, MateoConfig


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord = COORDINATORS.get(entry.entry_id)
    if not coord:
        return
    coord_cfg = coord._cfg  # existing config
    # If school changed via options, update a shallow copy for entity naming
    school_id = int(entry.options.get("school_id", coord_cfg.school_id))
    school_name = entry.options.get("school_name", coord_cfg.school_name)
    cfg = MateoConfig(
        slug=coord_cfg.slug,
        school_id=school_id,
        school_name=school_name,
        municipality_name=coord_cfg.municipality_name,
    )
    serving_start = entry.options.get(CONF_SERVING_START, DEFAULT_SERVING_START)
    serving_end = entry.options.get(CONF_SERVING_END, DEFAULT_SERVING_END)
    days_ahead = int(entry.options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))
    include_weekends = bool(entry.options.get(CONF_INCLUDE_WEEKENDS, DEFAULT_INCLUDE_WEEKENDS))
    entity = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id=entry.entry_id,
        serving_start=serving_start,
        serving_end=serving_end,
        days_ahead=days_ahead,
        include_weekends=include_weekends,
    )
    async_add_entities([entity])


def _parse_hhmm(value: str) -> time:
    parts = value.split(":")
    hour = int(parts[0]) if parts and parts[0].isdigit() else 0
    minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return time(hour=hour, minute=minute)


class MateoMealsCalendarEntity(CoordinatorEntity[MateoMealsCoordinator], CalendarEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MateoMealsCoordinator,
        cfg: MateoConfig,
        entry_id: str,
        serving_start: str,
        serving_end: str,
        days_ahead: int,
        include_weekends: bool,
    ) -> None:
        super().__init__(coordinator)
        self._cfg = cfg
        self._attr_unique_id = f"{DOMAIN}:{cfg.slug}:{cfg.school_id}:calendar"
        self._attr_name = f"{cfg.school_name} menu"
        self._serving_start = _parse_hhmm(serving_start)
        self._serving_end = _parse_hhmm(serving_end)
        self._days_ahead = max(1, min(14, days_ahead))
        self._include_weekends = include_weekends
        self._current_event: CalendarEvent | None = None

    async def async_update(self) -> None:  # fallback if HA calls manual update
        await self.coordinator.async_request_refresh()

    @property
    def event(self) -> CalendarEvent | None:  # Next ongoing or upcoming event
        self._update_cached_event()
        return self._current_event

    def _update_cached_event(self) -> None:
        tzinfo = None
        if getattr(self, "hass", None):  # type: ignore[attr-defined]
            tz_name = getattr(self.hass.config, "time_zone", None)  # type: ignore[attr-defined]
            if tz_name:
                try:
                    import zoneinfo  # noqa: PLC0415

                    tzinfo = zoneinfo.ZoneInfo(tz_name)
                except Exception:  # noqa: BLE001
                    tzinfo = timezone.utc
        if tzinfo is None:
            tzinfo = timezone.utc
        now = datetime.now(tzinfo)
        events = list(self._iter_events(now, self._days_ahead))
        # find first event with end >= now
        for ev in events:
            if ev.end >= now:
                self._current_event = ev
                return
        self._current_event = None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:  # noqa: D401
        events: list[CalendarEvent] = []
        # Limit iteration window to configured days ahead from 'start_date'
        window_days = self._days_ahead
        for ev in self._iter_events(start_date, window_days):
            if ev.start <= end_date and ev.end >= start_date:
                events.append(ev)
        return events

    def _iter_events(self, reference: datetime, days: int) -> Iterable[CalendarEvent]:
        data = self.coordinator.data or {}
        meals_by_date: dict[str, list[str]] = data.get("meals_by_date") or {}
        tzinfo = None
        if getattr(self, "hass", None):  # type: ignore[attr-defined]
            tz_name = getattr(self.hass.config, "time_zone", None)  # type: ignore[attr-defined]
            if tz_name:
                try:
                    import zoneinfo  # noqa: PLC0415

                    tzinfo = zoneinfo.ZoneInfo(tz_name)
                except Exception:  # noqa: BLE001
                    tzinfo = timezone.utc
        if tzinfo is None:
            tzinfo = timezone.utc
        today_local = reference.date()
        produced = 0
        cursor = today_local
        # Iterate calendar days until we have 'days' school days (or hit a safety cap)
        safety = 0
        while produced < days and safety < days * 3:  # safety cap
            safety += 1
            if not self._include_weekends and cursor.weekday() >= 5:
                cursor += timedelta(days=1)
                continue
            key = cursor.isoformat()
            names = meals_by_date.get(key) or []
            if names:
                start_dt = datetime.combine(cursor, self._serving_start, tzinfo)
                end_dt = datetime.combine(cursor, self._serving_end, tzinfo)
                summary = "; ".join(names)
                yield CalendarEvent(summary=summary, start=start_dt, end=end_dt, description=summary)
                produced += 1
            cursor += timedelta(days=1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "days_ahead": self._days_ahead,
            "serving_start": self._serving_start.strftime("%H:%M"),
            "serving_end": self._serving_end.strftime("%H:%M"),
            "include_weekends": self._include_weekends,
            "school_day_counting": (not self._include_weekends),
        }
