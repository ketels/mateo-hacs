from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mateo_meals.coordinator import (
    MateoConfig,
    MateoMealsCoordinator,
)
from custom_components.mateo_meals.sensor import MateoMealsSensor, MateoMealsFixedDaySensor
from datetime import date


@pytest.mark.asyncio
async def test_sensor_state_joined_names(hass: HomeAssistant) -> None:
    cfg = MateoConfig(
        slug="molndal",
        school_id=13,
        school_name="Jungfrustigens förskola",
        municipality_name="Mölndal",
    )
    coord = MateoMealsCoordinator(hass, cfg)

    # Inject coordinator data directly
    coord.async_set_updated_data({
        "today_date": "2025-09-15",
        "today_meals": ["Korv stroganoff", "Salladsbuffé"],
        "meals_by_date": {"2025-09-15": ["Korv stroganoff", "Salladsbuffé"]},
    })

    sensor = MateoMealsSensor(coord, cfg, entry_id="test")
    assert sensor.native_value == "Korv stroganoff; Salladsbuffé"


@pytest.mark.asyncio
async def test_fixed_day_weekend_skip(hass: HomeAssistant, monkeypatch) -> None:
    # Friday base date (2025-09-19 is a Friday)
    base = date(2025, 9, 19)
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="Test", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    # Provide meals for Monday 2025-09-22
    coord.async_set_updated_data({
        "today_date": base.isoformat(),
        "today_meals": ["Fredagslunch"],
        "meals_by_date": {
            base.isoformat(): ["Fredagslunch"],
            "2025-09-22": ["Måndagslunch"],
        },
    })

    # Freeze datetime.now to Friday
    class FauxDateTime:
        @classmethod
        def now(cls, tz=None):
            from datetime import datetime, time
            return datetime.combine(base, time(12,0), tz)

    monkeypatch.setattr("custom_components.mateo_meals.sensor.datetime", FauxDateTime)

    today_sensor = MateoMealsFixedDaySensor(coord, cfg, entry_id="e1", day_offset=0, include_weekends=False)
    day1_sensor = MateoMealsFixedDaySensor(coord, cfg, entry_id="e1", day_offset=1, include_weekends=False)

    # Today (Friday) should show Friday meal
    assert today_sensor.native_value == "Fredagslunch"
    # day_offset=1 should skip weekend and land on Monday with its meal
    assert day1_sensor.native_value == "Måndagslunch"


@pytest.mark.asyncio
async def test_fixed_day_no_menu_future_weekday(hass: HomeAssistant, monkeypatch) -> None:
    from datetime import date
    base = date(2025, 9, 18)  # Thursday
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="Test", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    coord.async_set_updated_data({
        "today_date": base.isoformat(),
        "today_meals": ["Torsdagslunch"],
        "meals_by_date": {base.isoformat(): ["Torsdagslunch"]},
    })

    class FauxDateTime2:
        @classmethod
        def now(cls, tz=None):
            from datetime import datetime, time
            return datetime.combine(base, time(11,0), tz)

    monkeypatch.setattr("custom_components.mateo_meals.sensor.datetime", FauxDateTime2)

    # day1 is Friday - no data provided -> should return 'No menu'
    day1_sensor = MateoMealsFixedDaySensor(coord, cfg, entry_id="x", day_offset=1, include_weekends=False)
    assert day1_sensor.native_value == "No menu"
