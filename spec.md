

# Mateo School Meals — HACS Integration Specification

**Goal**
Expose Swedish school lunches from Mateo’s public endpoints in Home Assistant (HA). A single **sensor entity** per configured school provides:
- **state**: a compact summary of **today’s** meals
- **attributes**: full meals for the **current** and **next** ISO week, plus exception days (if any)

Updates **once per day**. Empty days/weeks are simply absent (not cached or kept). Setup is done via the HA UI (config flow). Images are ignored.

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

## Entity Model

Create **one sensor** per config entry:
- **entity_id**: `sensor.mateo_meals_{slug}_{school_id}`
- **name**: `Skollunch – {school_name}`

**State (string, Swedish as-is)**
- Join today’s meal names (e.g., `"Korv stroganoff; Salladsbuffé"`).
- If no meals for today: `"Ingen meny idag"` (do **not** reuse old data).

**Attributes**
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

## Update Strategy

- Use **DataUpdateCoordinator** and a **CoordinatorEntity** sensor. Poll **daily** at local midnight (system tz) and on HA start.
- On each refresh:
  1. Compute current ISO week `YYYY-Www` and next ISO week (weeks start Monday).
  2. Fetch 2 payloads: `{school_id}_{week}` for current and next week.
  3. Normalize dates to local date (no time) and filter to Mon–Fri.
  4. Build attributes; **do not** persist or surface absent days/weeks.
  5. Derive state from **today** only.

**Network hygiene**
- Use `aiohttp` session from HA.
- If the backend returns `ETag`/`Cache-Control`, honor it (store `etag` in coordinator) to avoid redundant fetches.
- Exponential backoff on transient errors.

---

## Error Handling

- If any fetch fails (network/5xx): entity becomes `unavailable` until next run.
- If a week exists but is an empty JSON array: keep attributes for that week **absent** (do not synthesize placeholders).
- If today has no meals: state `"Ingen meny idag"` and `today_meals: []`.
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

## Implementation Notes

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
- `MateoMealsSensor(CoordinatorEntity, SensorEntity)`:
  - `native_value`: join today’s `meals[*].name` or `"Ingen meny idag"`.
  - `extra_state_attributes`: dict described above.

**config_flow.py**
- 2 steps as described; network probe on finish; map errors to HA flow errors (`cannot_connect`, `unknown`).
- `unique_id = f"mateo_meals:{slug}:{school_id}"` to avoid duplicates.

**strings / translations**
- Keep UI texts in English + Swedish (`translations/en.json`, `sv.json`).

**Branding**
- If publishing broadly, register in `home-assistant/brands` for icons and logos.

---

## Testing & QA

- **Unit tests**: config flow (happy path; network fail then recover), coordinator parsing (week switch edge cases; empty week), sensor state derivation (no meals today). Aim for full config-flow coverage.
- **Time edge cases**: Sundays and Mondays around ISO week rollover; New Year ISO week 1; Sweden timezone (`Europe/Stockholm`).
- **Network**: simulate 404 for next week (not yet published), empty array responses, and transient TLS/network errors.
- **HACS**: validate `hacs.json` + repo layout recognized by HACS; run basic HA integration validation.

---

## Acceptance Criteria (Done)

- Add integration via UI → pick municipality → pick school → sensor created.
- After creation (and after next daily tick or restart), sensor shows today’s meals in **state** and week data in **attributes**.
- Empty days/weeks are not present in attributes.
- Entity reliably updates daily and on HA restart.
- HACS recognizes the repo (installs, shows metadata) and HA has no blocking validation warnings.