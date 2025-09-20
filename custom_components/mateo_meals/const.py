DOMAIN = "mateo_meals"
DEFAULT_NAME = "Skollunch"
BASE_SHARED = "https://objects.dc-fbg1.glesys.net/mateo.shared/mateo-menu/municipalities.json"
BASE_DISTRICTS = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/districts.json"
BASE_MENU = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/{school_id}_{weeknum}.json"

# Option keys
CONF_DAYS_AHEAD = "days_ahead"
CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"
CONF_SERVING_START = "serving_start"  # HH:MM local time
CONF_SERVING_END = "serving_end"  # HH:MM local time
CONF_INCLUDE_WEEKENDS = "include_weekends"

# Defaults
DEFAULT_DAYS_AHEAD = 5  # today + following 4 days
DEFAULT_UPDATE_INTERVAL_HOURS = 4
DEFAULT_SERVING_START = "10:30"
DEFAULT_SERVING_END = "13:30"
DEFAULT_INCLUDE_WEEKENDS = False
