from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MateoConfig, MateoMealsCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
	data = entry.data
	# Allow options to override school selection
	school_id = int(entry.options.get("school_id", data["school_id"]))
	school_name = entry.options.get("school_name", data["school_name"])  # type: ignore[assignment]
	cfg = MateoConfig(
		slug=data["slug"],
		school_id=school_id,
		school_name=school_name,
		municipality_name=data.get("municipality_name", data["slug"]),
	)
	coordinator = MateoMealsCoordinator(hass, cfg)
	await coordinator.async_config_entry_first_refresh()
	entity = MateoMealsSensor(coordinator, cfg, entry.entry_id)
	async_add_entities([entity])


class MateoMealsSensor(CoordinatorEntity[MateoMealsCoordinator], SensorEntity):
	_attr_icon = "mdi:silverware-fork-knife"

	def __init__(self, coordinator: MateoMealsCoordinator, cfg: MateoConfig, entry_id: str) -> None:
		super().__init__(coordinator)
		self._cfg = cfg
		self._attr_unique_id = f"{DOMAIN}:{cfg.slug}:{cfg.school_id}"
		self._attr_name = f"Skollunch – {cfg.school_name}"
		self._attr_entity_registry_enabled_default = True

	@property
	def native_value(self) -> str:
		data = self.coordinator.data or {}
		meals = data.get("today_meals") or []
		if not meals:
			return "Ingen meny idag"
		names = [m.get("name") for m in meals if isinstance(m, dict) and m.get("name")]
		return "; ".join(names) if names else "Ingen meny idag"

	@property
	def extra_state_attributes(self) -> dict[str, Any] | None:
		data = self.coordinator.data or {}
		return data

	@property
	def entity_id(self) -> str:  # type: ignore[override]
		return f"sensor.mateo_meals_{self._cfg.slug}_{self._cfg.school_id}"
