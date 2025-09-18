from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_DISTRICTS, BASE_MENU


def _iso_week_string(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def _local_date_from_iso(dt_str: str) -> date | None:
    try:
        # API returns e.g. 2025-09-15T00:00:00.000Z
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # Convert to local timezone via Home Assistant core later; here assume UTC date component
        return dt.date()
    except Exception:  # noqa: BLE001
        return None


@dataclass
class MateoConfig:
    slug: str
    school_id: int
    school_name: str
    municipality_name: str


class MateoMealsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, cfg: MateoConfig) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name="MateoMealsCoordinator",
            update_interval=timedelta(hours=24),
        )
        self._cfg = cfg

    async def _async_fetch_json(self, url: str) -> Any:
        session = aiohttp_client.async_get_clientsession(self.hass)
        headers = {"User-Agent": "homeassistant-mateo-meals/0.1"}
        async with session.get(url, timeout=20, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise UpdateFailed(f"HTTP {resp.status} for {url} body={text[:120]}")
            return await resp.json(content_type=None)

    async def _async_get_exception_days(self) -> list[dict[str, Any]]:  # noqa: D401 (internal helper)
        url = BASE_DISTRICTS.format(slug=self._cfg.slug)
        try:
            payload = await self._async_fetch_json(url)
        except Exception:  # noqa: BLE001
            return []
        districts = payload.get("districts", []) if isinstance(payload, dict) else []
        exc: list[dict[str, Any]] = []
        for d in districts:
            for ex in d.get("districts_exception_days", []) or []:
                start = ex.get("start")
                end = ex.get("end")
                if start:
                    sdt = _local_date_from_iso(start)
                    ex["start"] = sdt.isoformat() if sdt else start
                if end:
                    edt = _local_date_from_iso(end)
                    ex["end"] = edt.isoformat() if edt else end
                exc.append(ex)
        return exc

    async def _async_update_data(self) -> dict[str, Any]:
        # Current and next week (simple week numbers used in filename pattern school_week.json)
        # Compatibility: Python <3.11 uses timezone.utc; 3.11+ offers datetime.UTC alias.
        try:
            utc = datetime.UTC  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover - older runtime
            utc = timezone.utc
        now = datetime.now(utc).date()
        weekday = now.weekday()  # Mon=0
        monday = now - timedelta(days=weekday)
        next_monday = monday + timedelta(days=7)
        _year, week_cur, _ = monday.isocalendar()
        _year_next, week_next, _ = next_monday.isocalendar()
        week_numbers = (week_cur, week_next)
        urls = [
            BASE_MENU.format(slug=self._cfg.slug, school_id=self._cfg.school_id, weeknum=w)
            for w in week_numbers
        ]
        try:
            payloads = [await self._async_fetch_json(u) for u in urls]
        except Exception as primary_err:  # noqa: BLE001
            try:
                legacy_urls = [
                    f"https://objects.dc-fbg1.glesys.net/mateo.{self._cfg.slug}/menus/app/{self._cfg.school_id}_{_iso_week_string(monday)}.json",
                    f"https://objects.dc-fbg1.glesys.net/mateo.{self._cfg.slug}/menus/app/{self._cfg.school_id}_{_iso_week_string(next_monday)}.json",
                ]
                payloads = [await self._async_fetch_json(u) for u in legacy_urls]
            except Exception:  # noqa: BLE001
                raise UpdateFailed(str(primary_err)) from primary_err
        week_maps: list[dict[str, list[dict[str, Any]]]] = []
        for payload in payloads:
            daymap: dict[str, list[dict[str, Any]]] = {}
            if isinstance(payload, list):
                for day in payload:
                    dts = day.get("date")
                    d_local = _local_date_from_iso(dts) if dts else None
                    if not d_local or d_local.weekday() > 4:
                        continue
                    meals = day.get("meals") or []
                    if meals:
                        daymap[d_local.isoformat()] = meals
            week_maps.append(daymap)
        today_str = now.isoformat()
        meals_by_date: dict[str, list[str]] = {}
        for wm in week_maps:
            for d, meals in wm.items():
                names_raw = [m.get("name") for m in meals if isinstance(m, dict) and m.get("name")]
                names = [n.strip() for n in names_raw if isinstance(n, str) and n.strip()]
                if names:
                    meals_by_date[d] = names
        meal_names_today = meals_by_date.get(today_str, [])
        exception_days = await self._async_get_exception_days()
        return {
            "today_date": today_str,
            "today_meals": meal_names_today,
            "meals_by_date": meals_by_date,
            "exception_days": exception_days,
        }
