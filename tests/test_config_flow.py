from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mateo_meals import config_flow as cf

DOMAIN = "mateo_meals"


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_config_flow_happy_path(hass: HomeAssistant) -> None:
    municipalities_payload = [
        {"name": "Region", "municipalities": [{"slug": "molndal", "name": "Mölndal"}]}
    ]
    districts_payload = {
        "districts": [
            {"id": 13, "name": "Jungfrustigens förskola", "districts_exception_days": []}
        ]
    }
    # Empty menu list acts as successful probe
    menu_payload: list[Any] = []

    async def _fake_http_json(hass_obj, url: str):  # type: ignore[unused-ignore]
        if url.endswith("municipalities.json"):
            return municipalities_payload
        if url.endswith("districts.json"):
            return districts_payload
        if url.endswith("_" + "W00.json"):
            return []  # unlikely pattern safeguard
        return menu_payload

    # Patch network helper before starting flow so first step uses fixtures
    with patch.object(cf, "_http_json", side_effect=_fake_http_json):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        # Choose municipality
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"municipality": "molndal"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "school"

        # Choose school
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"school": 13}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        data = result["data"]
        assert data["slug"] == "molndal"
        assert data["school_id"] == 13
        assert data["school_name"] == "Jungfrustigens förskola"
