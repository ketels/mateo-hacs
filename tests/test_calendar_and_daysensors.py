from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mateo_meals.coordinator import MateoMealsCoordinator, MateoConfig
from custom_components.mateo_meals.sensor import MateoMealsFixedDaySensor
from custom_components.mateo_meals.calendar import MateoMealsCalendarEntity


@pytest.mark.asyncio
async def test_day_sensors_states(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    # Build fake meals for today + 2 days
    now = datetime.now(UTC).date()
    meals_by_date = {
        (now + timedelta(days=offset)).isoformat(): [f"Meal {offset}"] for offset in range(3)
    }
    coord.async_set_updated_data(
        {
            "today_date": now.isoformat(),
            "today_meals": meals_by_date[now.isoformat()],
            "meals_by_date": meals_by_date,
        }
    )
    sensors = [MateoMealsFixedDaySensor(coord, cfg, "entry", offset) for offset in range(3)]
    assert sensors[0].native_value == "Meal 0"
    assert sensors[1].native_value == "Meal 1"
    assert sensors[2].native_value == "Meal 2"


@pytest.mark.asyncio
async def test_calendar_events_generation(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    now = datetime.now(UTC).date()
    meals_by_date = {
        (now + timedelta(days=offset)).isoformat(): [f"Meal {offset}"] for offset in range(2)
    }
    coord.async_set_updated_data(
        {
            "today_date": now.isoformat(),
            "today_meals": meals_by_date[now.isoformat()],
            "meals_by_date": meals_by_date,
        }
    )
    cal = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id="entry",
        serving_start="10:00",
        serving_end="12:00",
        days_ahead=3,
        include_weekends=True,
    )
    start_range = datetime.combine(now, datetime.min.time(), UTC)
    end_range = start_range + timedelta(days=3)
    events = await cal.async_get_events(hass, start_range, end_range)
    assert len(events) >= 2
    assert any(ev.summary.startswith("Meal 0") for ev in events)


@pytest.mark.asyncio
async def test_calendar_excludes_weekends(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    # Fix a Friday reference date (choose a known Friday): 2025-09-19
    base = datetime(2025, 9, 19, tzinfo=UTC).date()  # Friday
    # Provide meals for Fri (offset 0), Sat (1), Sun (2), Mon (3)
    meals_by_date = { (base + timedelta(days=o)).isoformat(): [f"Meal {o}"] for o in range(4) }
    coord.async_set_updated_data({
        "today_date": base.isoformat(),
        "today_meals": meals_by_date[base.isoformat()],
        "meals_by_date": meals_by_date,
    })
    cal = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id="entry",
        serving_start="10:00",
        serving_end="12:00",
        days_ahead=5,
        include_weekends=False,
    )
    start = datetime.combine(base, datetime.min.time(), UTC)
    end = start + timedelta(days=5)
    events = await cal.async_get_events(hass, start, end)
    dates = {e.start.date().isoformat() for e in events}
    assert (base + timedelta(days=1)).isoformat() not in dates  # Saturday excluded
    assert (base + timedelta(days=2)).isoformat() not in dates  # Sunday excluded
    assert (base + timedelta(days=3)).isoformat() in dates      # Monday included


@pytest.mark.asyncio
async def test_calendar_event_property_next_event(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    base = datetime.now(UTC).date()
    meals_by_date = {
        base.isoformat(): ["Meal A"],
        (base + timedelta(days=1)).isoformat(): ["Meal B"],
    }
    coord.async_set_updated_data({
        "today_date": base.isoformat(),
        "today_meals": meals_by_date[base.isoformat()],
        "meals_by_date": meals_by_date,
    })
    cal = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id="entry",
        serving_start="06:00",
        serving_end="23:00",
        days_ahead=2,
        include_weekends=True,
    )
    ev = cal.event
    assert ev is not None
    assert "Meal A" in ev.summary or "Meal B" in ev.summary


@pytest.mark.asyncio
async def test_calendar_serving_window_times(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    base = datetime.now(UTC).date()
    meals_by_date = { base.isoformat(): ["Meal A"] }
    coord.async_set_updated_data({
        "today_date": base.isoformat(),
        "today_meals": meals_by_date[base.isoformat()],
        "meals_by_date": meals_by_date,
    })
    cal = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id="entry",
        serving_start="09:30",
        serving_end="11:15",
        days_ahead=1,
        include_weekends=True,
    )
    start = datetime.combine(base, datetime.min.time(), UTC)
    end = start + timedelta(days=1)
    events = await cal.async_get_events(hass, start, end)
    assert len(events) == 1
    event = events[0]
    assert event.start.hour == 9 and event.start.minute == 30
    assert event.end.hour == 11 and event.end.minute == 15
