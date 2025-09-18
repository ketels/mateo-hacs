from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mateo_meals.coordinator import MateoConfig, MateoMealsCoordinator
from custom_components.mateo_meals.sensor import MateoMealsSensor


@pytest.mark.asyncio
async def test_sensor_state_joined_names(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="Jungfrustigens förskola", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)

    # Inject coordinator data directly
    coord.async_set_updated_data({
        "today_meals": [{"name": "Korv stroganoff"}, {"name": "Salladsbuffé"}],
        "week_meals": {},
        "next_week_meals": {},
        "municipality_slug": "molndal",
        "municipality_name": "Mölndal",
        "school_id": 13,
        "school_name": "Jungfrustigens förskola",
        "today_date": "2025-09-15",
        "week_iso": "2025-W38",
        "next_week_iso": "2025-W39",
        "exception_days": [],
        "last_update": "2025-09-15T00:00:00Z",
        "source": "mateo.molndal",
    })

    sensor = MateoMealsSensor(coord, cfg, entry_id="test")
    assert sensor.native_value == "Korv stroganoff; Salladsbuffé"
