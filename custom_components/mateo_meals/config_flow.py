from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import BASE_DISTRICTS, BASE_MENU, BASE_SHARED, DOMAIN


def _iso_week_string(dt: datetime) -> str:
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


async def _http_json(hass: HomeAssistant, url: str) -> Any:
    session = aiohttp_client.async_get_clientsession(hass)
    async with session.get(url, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return await resp.json(content_type=None)


_LOGGER = logging.getLogger(__name__)


class MateoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._municipalities: list[dict[str, Any]] | None = None
        self._selected_slug: str | None = None
        self._selected_municipality_name: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            slug = user_input["municipality"]
            assert self._municipalities is not None
            name_map = {m["slug"]: m["name"] for m in self._municipalities}
            self._selected_slug = slug
            self._selected_municipality_name = name_map.get(slug, slug)
            return await self.async_step_school()

        try:
            data = await _http_json(self.hass, BASE_SHARED)
            municipalities: list[dict[str, Any]] = []
            for region in data or []:
                for m in region.get("municipalities", []):
                    if "slug" in m and "name" in m:
                        municipalities.append({"slug": m["slug"], "name": m["name"]})
            seen: set[str] = set()
            unique_m: list[dict[str, Any]] = []
            for m in municipalities:
                if m["slug"] not in seen:
                    unique_m.append(m)
                    seen.add(m["slug"])
            self._municipalities = sorted(unique_m, key=lambda x: x["name"].lower())
        except Exception:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("municipality"): str}),
                errors={"base": "cannot_connect"},
            )

        options = {m["slug"]: f"{m['name']} ({m['slug']})" for m in self._municipalities}
        schema = vol.Schema({vol.Required("municipality"): vol.In(options)})
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_school(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        assert self._selected_slug is not None
        assert self._selected_municipality_name is not None
        slug = self._selected_slug
        districts_url = BASE_DISTRICTS.format(slug=slug)

        if user_input is not None:
            school_id = int(user_input["school"])
            try:
                districts_payload = await _http_json(self.hass, districts_url)
            except Exception:
                return self.async_show_form(
                    step_id="school",
                    data_schema=vol.Schema({vol.Required("school"): int}),
                    errors={"base": "cannot_connect"},
                )
            districts = (
                districts_payload.get("districts", [])
                if isinstance(districts_payload, dict)
                else []
            )
            id_to_name = {
                int(d.get("id")): d.get("name")
                for d in districts
                if d.get("id") is not None
            }
            school_name = id_to_name.get(school_id, str(school_id))
            unique_id = f"{DOMAIN}:{slug}:{school_id}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            try:
                now_utc = datetime.now(UTC)
                week = _iso_week_string(now_utc)
                await _http_json(
                    self.hass,
                    BASE_MENU.format(slug=slug, school_id=school_id, week=week),
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Optional initial menu fetch failed for %s/%s", slug, school_id
                )
            title = f"{self._selected_municipality_name} – {school_name}"
            data = {
                "slug": slug,
                "municipality_name": self._selected_municipality_name,
                "school_id": school_id,
                "school_name": school_name,
            }
            return self.async_create_entry(title=title, data=data)

        try:
            districts_payload = await _http_json(self.hass, districts_url)
        except Exception:
            return self.async_show_form(
                step_id="school",
                data_schema=vol.Schema({vol.Required("school"): int}),
                errors={"base": "cannot_connect"},
            )
        districts = (
            districts_payload.get("districts", [])
            if isinstance(districts_payload, dict)
            else []
        )
        id_to_name = {int(d.get("id")): d.get("name") for d in districts if d.get("id") is not None}
        if id_to_name:
            schema = vol.Schema({vol.Required("school"): vol.In(id_to_name)})
        else:
            schema = vol.Schema({vol.Required("school"): int})
        return self.async_show_form(step_id="school", data_schema=schema)


class MateoOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return await self.async_step_school(user_input)
        return await self.async_step_school()

    async def async_step_school(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        hass = self.hass
        slug = self.config_entry.data.get("slug")
        if not slug:
            return self.async_abort(reason="unknown")
        districts_url = BASE_DISTRICTS.format(slug=slug)
        try:
            payload = await _http_json(hass, districts_url)
        except Exception:
            return self.async_show_form(
                step_id="school",
                data_schema=vol.Schema({vol.Required("school"): int}),
                errors={"base": "cannot_connect"},
            )
        districts = payload.get("districts", []) if isinstance(payload, dict) else []
        id_to_name = {int(d.get("id")): d.get("name") for d in districts if d.get("id") is not None}
        if user_input is None:
            current_id = self.config_entry.data.get("school_id")
            schema = (
                vol.Schema({vol.Required("school", default=current_id): vol.In(id_to_name)})
                if id_to_name
                else vol.Schema({vol.Required("school"): int})
            )
            return self.async_show_form(step_id="school", data_schema=schema)
        school_id = int(user_input["school"])
        school_name = id_to_name.get(school_id, str(school_id))
        return self.async_create_entry(
            title="",
            data={"school_id": school_id, "school_name": school_name},
        )


async def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> MateoOptionsFlowHandler:  # noqa: D401
    return MateoOptionsFlowHandler(config_entry)
