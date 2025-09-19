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
