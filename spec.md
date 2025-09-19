

# Mateo School Meals — HACS Integration Specification

**Goal (Updated)**
Expose Swedish school lunches from Mateo’s public endpoints in Home Assistant (HA) with:
- One **base sensor**: state = today’s meals summary (fallback 'Ingen meny idag' if empty)
- A configurable set of **fixed day sensors** (today + N forward SCHOOL days; weekday-aware when weekends excluded)
- A **calendar entity** listing each meal as an event within a configurable serving window (optionally excluding weekends)
- Full week(s) meal data stored in coordinator state (attributes of base sensor) for automations / templates

Update interval is now **configurable (hours)** via the options flow (default 4h). Empty days/weeks are absent. Setup and all changes performed via UI.

---

## Data Sources

1. **Municipalities list**
   - `GET https://objects.dc-fbg1.glesys.net/mateo.shared/mateo-menu/municipalities.json`
   - Shape (excerpt):
     ```json
     [
       {"name":"Blekinge län","municipalities":[{"slug":"karlshamn","name":"Karlshamn"}]}
     ]
     ```

2. **Schools for a municipality**
   - `GET https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/districts.json`
   - Shape (excerpt):
     ```json
     {
       "organization":{"mateo_menu_information":"...","mateo_menu_pictures":false},
       "districts":[
         {
           "id":13,"name":"Jungfrustigens förskola","type":"preschool",
           "districts_exception_days":[{"id":340,"name":"Vegetariska världsdagen!","start":"2025-10-01T00:00:00.000Z","end":"2025-10-01T00:00:00.000Z"}]
         }
       ]
     }
     ```

3. **Meals per school + week**
   - `GET https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/{school_id}_{week}.json`
   - Shape (per day):
     ```json
     [
       {"date":"2025-09-15T00:00:00.000Z",
        "meals":[{"name":"Korv stroganoff serveras med ris","type":"Lunch 1",
                   "categories":[{"name":"Fågel","icon":"chicken"}],"allergens":[]}]}
     ]
     ```

---

## UX & Configuration (Config Flow)

Use HA **config entries** so setup is done in the UI.

**Step 1 – Choose municipality**
- Fetch municipalities and flatten `regions[*].municipalities` into a dropdown of `name (slug)`.
- Store selected `{slug, name}` temporarily in the flow.

**Step 2 – Choose school**
- Fetch `districts.json` for the chosen slug.
- Present dropdown of `districts[*].name` (value = `id`).
- On submit, create the config entry with:
  ```json
  {
    "slug": "molndal",
    "municipality_name": "Mölndal",
    "school_id": 13,
    "school_name": "Jungfrustigens förskola"
  }
  ```

**Options flow**
- Allow changing school (re-fetch districts) without re-adding the integration.

**Validation**
- During the final step, do a non-blocking probe: try loading **current ISO week** menu; if 404/empty is returned, still allow setup (some weeks are legitimately empty), but surface a warning in the flow summary.

---

## Entity Model (Updated)

Base Sensor (legacy unique_id preserved):
- `sensor.skollunch_{school}` – today’s meals summary

Fixed Day Sensors (dynamic count):
- `sensor.skollunch_{school}_today`, `sensor.skollunch_{school}_day1..dayN`
  - State: semicolon-separated meal names for that date or literal "No menu" if not published (avoid `unknown`)
  - Offsets count only weekdays when `include_weekends == False` (e.g. if today is Friday and weekends excluded, `day1` is Monday)
  - Attributes: `{ date: YYYY-MM-DD, offset: int, include_weekends: bool, has_meals: bool }`

Calendar Entity:
- `calendar.{school}_menu` – events per meal
  - Event summary: meal name(s) joined by '; '
  - Start/End: serving window applied to the date (configurable HH:MM)
  - Weekends skipped entirely when `include_weekends` is False
  - `event` property supplies next ongoing or upcoming meal

Base Sensor Attributes (unchanged core schema, still source of weekly data):
```yaml
municipality_slug: "molndal"
municipality_name: "Mölndal"
school_id: 13
school_name: "Jungfrustigens förskola"
today_date: "2025-09-15"
today_meals:
  - { name: "Korv stroganoff serveras med ris", type: "Lunch 1",
      categories: [{name:"Fågel", icon:"chicken"}], allergens: [] }
week_iso: 2025-W38
week_meals:
  "2025-09-15": [ ... ]
  "2025-09-16": [ ... ]
next_week_iso: 2025-W39
next_week_meals:
  "2025-09-22": [ ... ]
exception_days:
  - { id: 340, name: "Vegetariska världsdagen!", start: "2025-10-01", end: "2025-10-01" }
last_update: "2025-09-15T00:01:05Z"
source: "mateo.{slug}"
```
> Localization: keep Swedish text from the API; no translation layer.

---

## Update Strategy (Revised)

- **DataUpdateCoordinator** with `update_interval = timedelta(hours=update_interval_hours)` (options, default 4).
- Refresh triggered on HA start and then every configured interval.
- Same dual-week fetch logic; meals merged into `meals_by_date`.
- Day sensors derive their states from `meals_by_date` on access (no extra I/O).
- Calendar entity builds events lazily per update and caches next event.

**Network hygiene**
- Use `aiohttp` session from HA.
- If the backend returns `ETag`/`Cache-Control`, honor it (store `etag` in coordinator) to avoid redundant fetches.
- Exponential backoff on transient errors.

---

## Error Handling (Unchanged + Extensions)

- If any fetch fails (network/5xx): entity becomes `unavailable` until next run.
- If a week exists but is an empty JSON array: keep attributes for that week **absent** (do not synthesize placeholders).
- If today has no meals: base sensor state `"Ingen meny idag"` (fallback English 'No menu today') and `today_meals: []`.
- Future day sensors without meals use literal `"No menu"` (never `unknown`).
- If municipality or school becomes invalid (e.g., repeated 404 on districts), create a persistent notification with an action to open Options and reselect.

---

## Repository / File Structure (HACS-ready)

```
custom_components/mateo_meals/
  __init__.py
  manifest.json
  config_flow.py
  coordinator.py
  sensor.py
  const.py
  strings.json
  translations/
    en.json
    sv.json
hacs.json                # HACS metadata
README.md
LICENSE
```

**manifest.json** (keys): `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners`, `config_flow: true`, `iot_class: cloud_polling`.

**hacs.json** example: `{ "name": "Mateo Meals", "country": "SE", "homeassistant": "2024.12.0" }`.

---

## Implementation Notes (Changes Highlighted)

**const.py**
```python
DOMAIN = "mateo_meals"
DEFAULT_NAME = "Skollunch"
BASE_SHARED = "https://objects.dc-fbg1.glesys.net/mateo.shared/mateo-menu/municipalities.json"
BASE_DISTRICTS = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/districts.json"
BASE_MENU = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/{school_id}_{week}.json"
```

**coordinator.py**
- Subclass `DataUpdateCoordinator` with an `async_refresh_data()` method that:
  - Calculates ISO week numbers (`date.isocalendar()`).
  - Builds two URLs; fetch concurrently; normalize to `{date: [meals...]}`.
  - Optionally read `districts.json` once per boot to hydrate `exception_days` (cache per slug).

**sensor.py**
- `MateoMealsSensor` (base) unchanged semantics.
- `MateoMealsFixedDaySensor` new class for offset days.

**config_flow.py**
- Adds options for: `days_ahead`, `update_interval_hours`, `serving_start`, `serving_end`, `include_weekends` alongside school change.
- Static `async_get_options_flow` method for HA to discover options handler.

**strings / translations**
- Keep UI texts in English + Swedish (`translations/en.json`, `sv.json`).

**Branding**
- If publishing broadly, register in `home-assistant/brands` for icons and logos.

---

## Testing & QA

- **Unit tests**: config flow (happy path; network fail then recover), coordinator parsing (week switch edge cases; empty week), sensor state derivation (no meals today + weekday skipping), calendar events (serving window, weekend exclusion, next event selection). Current coverage ~83% (>75% target).
- **Time edge cases**: Sundays and Mondays around ISO week rollover; New Year ISO week 1; Sweden timezone (`Europe/Stockholm`).
- **Network**: simulate 404 for next week (not yet published), empty array responses, and transient TLS/network errors.
- **HACS**: validate `hacs.json` + repo layout recognized by HACS; run basic HA integration validation.

---

## Acceptance Criteria (Updated Done)

- Integration install & initial config unchanged (municipality + school).
- Base sensor state reflects today’s meals (or "Ingen meny idag").
- Configurable forward day sensors created (correct count reflects options changes).
- Calendar entity lists events within serving window; `event` surfaces next upcoming meal.
- Options adjustments (interval, serving window, days ahead, weekends) propagate without re-adding integration.
- Coordinator obeys updated polling interval after option change.
- All legacy automations referencing old sensor continue to work.