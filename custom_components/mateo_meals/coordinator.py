from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
import logging

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
	except Exception:
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
		self._exception_days_cache: list[dict[str, Any]] | None = None

	async def _async_fetch_json(self, url: str) -> Any:
		session = aiohttp_client.async_get_clientsession(self.hass)
		async with session.get(url, timeout=20) as resp:
			if resp.status != 200:
				raise UpdateFailed(f"HTTP {resp.status} for {url}")
			return await resp.json(content_type=None)

	async def _async_get_exception_days(self) -> list[dict[str, Any]]:
		if self._exception_days_cache is not None:
			return self._exception_days_cache
		url = BASE_DISTRICTS.format(slug=self._cfg.slug)
		payload = await self._async_fetch_json(url)
		districts = payload.get("districts", []) if isinstance(payload, dict) else []
		# Merge all exception days for simplicity
		exc: list[dict[str, Any]] = []
		for d in districts:
			for ex in d.get("districts_exception_days", []) or []:
				start = ex.get("start")
				end = ex.get("end")
				# Normalize to YYYY-MM-DD if present
				if start:
					sdt = _local_date_from_iso(start)
					ex["start"] = sdt.isoformat() if sdt else start
				if end:
					edt = _local_date_from_iso(end)
					ex["end"] = edt.isoformat() if edt else end
				exc.append(ex)
		self._exception_days_cache = exc
		return exc

	async def _async_update_data(self) -> dict[str, Any]:
		# Current and next ISO week starting Monday
		now = datetime.now(timezone.utc).date()
		weekday = now.weekday()  # Mon=0
		monday = now - timedelta(days=weekday)
		next_monday = monday + timedelta(days=7)
		weeks = (_iso_week_string(monday), _iso_week_string(next_monday))

		urls = [
			BASE_MENU.format(slug=self._cfg.slug, school_id=self._cfg.school_id, week=w)
			for w in weeks
		]

		try:
			payloads = [await self._async_fetch_json(u) for u in urls]
		except Exception as err:  # noqa: BLE001
			raise UpdateFailed(str(err)) from err

		week_maps: list[dict[str, list[dict[str, Any]]]] = []
		for payload in payloads:
			daymap: dict[str, list[dict[str, Any]]] = {}
			if isinstance(payload, list):
				for day in payload:
					dts = day.get("date")
					d_local = _local_date_from_iso(dts) if dts else None
					if not d_local:
						continue
					if d_local.weekday() > 4:
						continue  # only Mon-Fri
					meals = day.get("meals") or []
					if meals:
						daymap[d_local.isoformat()] = meals
			week_maps.append(daymap)

		today_str = now.isoformat()
		today_meals = week_maps[0].get(today_str, []) if week_maps else []

		data: dict[str, Any] = {
			"municipality_slug": self._cfg.slug,
			"municipality_name": self._cfg.municipality_name,
			"school_id": self._cfg.school_id,
			"school_name": self._cfg.school_name,
			"today_date": today_str,
			"today_meals": today_meals,
			"week_iso": weeks[0],
			"week_meals": week_maps[0],
			"next_week_iso": weeks[1],
			"next_week_meals": week_maps[1],
			"exception_days": await self._async_get_exception_days(),
			"last_update": datetime.now(timezone.utc).isoformat(),
			"source": f"mateo.{self._cfg.slug}",
		}
		return data
