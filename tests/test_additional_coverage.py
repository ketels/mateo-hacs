from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mateo_meals import config_flow as cf
from custom_components.mateo_meals.calendar import MateoMealsCalendarEntity
from custom_components.mateo_meals.coordinator import MateoMealsCoordinator, MateoConfig
from custom_components.mateo_meals.sensor import MateoMealsSensor

DOMAIN = "mateo_meals"


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_config_flow_options_extra_fields(hass: HomeAssistant) -> None:
    municipalities_payload = [
        {"name": "Region", "municipalities": [{"slug": "molndal", "name": "Mölndal"}]}
    ]
    districts_payload = {
        "districts": [
            {"id": 13, "name": "Jungfrustigens förskola", "districts_exception_days": []}
        ]
    }

    async def _fake_http_json(hass_obj, url: str):  # type: ignore[unused-ignore]
        if url.endswith("municipalities.json"):
            return municipalities_payload
        if url.endswith("districts.json"):
            return districts_payload
        return []

    with patch.object(cf, "_http_json", side_effect=_fake_http_json):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"municipality": "molndal"}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"school": 13})
        assert result["type"] == FlowResultType.CREATE_ENTRY
        entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Options flow with extra fields
    with patch.object(cf, "_http_json", side_effect=_fake_http_json):
        opt_flow = await hass.config_entries.options.async_init(entry.entry_id)
        assert opt_flow["type"] == FlowResultType.FORM
        updated = await hass.config_entries.options.async_configure(
            opt_flow["flow_id"],
            {
                "school": 13,
                "days_ahead": 3,
                "update_interval_hours": 2,
                "serving_start": "09:00",
                "serving_end": "12:30",
                "include_weekends": True,
            },
        )
        assert updated["type"] == FlowResultType.CREATE_ENTRY
        assert updated["data"]["days_ahead"] == 3
        assert updated["data"]["update_interval_hours"] == 2


@pytest.mark.asyncio
async def test_calendar_selects_next_event(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=1, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    today = datetime.now(UTC).date()
    meals_by_date = {today.isoformat(): ["Meal A"], (today + timedelta(days=1)).isoformat(): ["Meal B"]}
    coord.async_set_updated_data(
        {
            "today_date": today.isoformat(),
            "today_meals": meals_by_date[today.isoformat()],
            "meals_by_date": meals_by_date,
        }
    )
    cal = MateoMealsCalendarEntity(
        coordinator=coord,
        cfg=cfg,
        entry_id="entry",
        serving_start="10:00",
        serving_end="12:00",
        days_ahead=2,
        include_weekends=True,
    )
    # Access property to trigger cache update
    ev = cal.event
    assert ev is not None
    assert "Meal" in ev.summary


@pytest.mark.asyncio
async def test_sensor_no_menu_branch(hass: HomeAssistant) -> None:
    cfg = MateoConfig(slug="molndal", school_id=2, school_name="School", municipality_name="Mölndal")
    coord = MateoMealsCoordinator(hass, cfg)
    # No meals for today
    today = datetime.now(UTC).date().isoformat()
    coord.async_set_updated_data({"today_date": today, "today_meals": [], "meals_by_date": {}})
    sensor = MateoMealsSensor(coord, cfg, entry_id="x")
    assert sensor.native_value in {"Ingen meny idag", "No menu today"}
