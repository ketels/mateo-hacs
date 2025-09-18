from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mateo_meals.coordinator import (
    MateoConfig,
    MateoMealsCoordinator,
)
from custom_components.mateo_meals.sensor import MateoMealsSensor


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
