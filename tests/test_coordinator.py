from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.mateo_meals.coordinator import MateoConfig, MateoMealsCoordinator


@pytest.mark.asyncio
async def test_coordinator_parses_weeks(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=13, school_name="Jungfrustigens förskola", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)

    async def fake_fetch(url: str) -> Any:
        if url.endswith("districts.json"):
            return {"districts": []}
        # Return a minimal week payload with one day
        return [
            {"date": "2025-09-15T00:00:00.000Z", "meals": [{"name": "Korv stroganoff"}]}
        ]

    with patch.object(coord, "_async_fetch_json", side_effect=fake_fetch):
        data = await coord._async_update_data()

    # meals_by_date should contain normalized names
    assert data["meals_by_date"]["2025-09-15"][0] == "Korv stroganoff"
    assert isinstance(data["today_meals"], list)
