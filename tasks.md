# Build Tasks — Mateo School Meals (HACS)

This checklist turns `spec.md` into shippable code. Tick items as you go.

> Target: Home Assistant 2024.12+ · Python 3.12 · Europe/Stockholm

---

## 0) One-time setup

- [x] Create venv & install tooling
  ```bash
  uv venv || python3 -m venv .venv
  source .venv/bin/activate
  pip install -U pip wheel
  pip install -U homeassistant pytest pytest-asyncio pytest-cov aiohttp mypy ruff pre-commit
  ```
- [ ] Enable pre-commit hooks
  ```bash
  pre-commit install
  ```
- [ ] Decide repo visibility & license (MIT suggested)

---

## 1) Repo scaffold (files & folders)

- [ ] Create HACS/HA structure
  ```text
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
  hacs.json
  README.md
  CHANGELOG.md
  CONTRIBUTING.md
  spec.md (already exists)
  tests/
    conftest.py
    test_config_flow.py
    test_coordinator.py
    test_sensor.py
  ```
- [ ] `manifest.json` minimal content
  ```json
  {
    "domain": "mateo_meals",
    "name": "Mateo School Meals",
    "version": "0.1.0",
    "documentation": "https://github.com/YOUR_REPO/mateo-hacs",
    "issue_tracker": "https://github.com/YOUR_REPO/mateo-hacs/issues",
    "codeowners": ["@YOUR_GH"],
    "config_flow": true,
    "iot_class": "cloud_polling",
    "requirements": []
  }
  ```
- [ ] `hacs.json` minimal content
  ```json
  { "name": "Mateo Meals", "country": "SE", "homeassistant": "2024.12.0" }
  ```
- [ ] `const.py` constants from spec
  ```python
  DOMAIN = "mateo_meals"
  DEFAULT_NAME = "Skollunch"
  BASE_SHARED = "https://objects.dc-fbg1.glesys.net/mateo.shared/mateo-menu/municipalities.json"
  BASE_DISTRICTS = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/districts.json"
  BASE_MENU = "https://objects.dc-fbg1.glesys.net/mateo.{slug}/menus/app/{school_id}_{week}.json"
  ```
- [ ] `strings.json` (en) and translations (sv)
  ```json
  // strings.json
  {
    "title": "Mateo School Meals",
    "config": {
      "step": {
        "user": {
          "title": "Choose municipality",
          "data": { "municipality": "Municipality" }
        },
        "school": {
          "title": "Choose school",
          "data": { "school": "School" }
        }
      },
      "error": {
        "cannot_connect": "Cannot connect",
        "unknown": "Unknown error"
      }
    }
  }
  ```
  ```json
  // translations/sv.json
  {
    "title": "Mateo Skollunch",
    "config": {
      "step": {
        "user": {
          "title": "Välj kommun",
          "data": { "municipality": "Kommun" }
        },
        "school": {
          "title": "Välj skola",
          "data": { "school": "Skola" }
        }
      },
      "error": {
        "cannot_connect": "Kan inte ansluta",
        "unknown": "Okänt fel"
      }
    }
  }
  ```

---

## 2) Config Flow (UI setup)

- [ ] Implement `config_flow.py`
  - [ ] Step 1: fetch municipalities (`BASE_SHARED`), flatten to list; show select.
  - [ ] Step 2: fetch districts for selected slug, map `name -> id`; show select.
  - [ ] On submit: create entry with `{slug, municipality_name, school_id, school_name}`.
  - [ ] `unique_id = f"{DOMAIN}:{slug}:{school_id}"`; abort if exists.
  - [ ] OptionsFlow to change school later (re-fetch districts).
  - [ ] Non-blocking probe (current ISO week) → show warning on empty/404 but allow finish.

**Acceptance**
- [ ] Can add integration via UI and select municipality + school.
- [ ] Duplicate setup prevented.

---

## 3) Coordinator & Fetch Logic

- [ ] `coordinator.py` with `DataUpdateCoordinator`
  - [ ] Calculate current ISO week and next week.
  - [ ] Build two URLs `{school_id}_{week}.json` and fetch concurrently via HA `aiohttp_client`.
  - [ ] Normalize to `{date: [meals...]}` using local timezone (Europe/Stockholm).
  - [ ] Filter to Mon–Fri; keep Swedish text as-is.
  - [ ] Optionally cache `districts.json` once per boot to expose `exception_days`.
  - [ ] Store `last_update`, `week_iso`, `next_week_iso`.
  - [ ] Backoff and error handling; surface `UpdateFailed` appropriately.

**Acceptance**
- [ ] Two-week window populated when data exists; absent days/weeks not included.
- [ ] Handles empty week (array) without errors.

---

## 4) Sensor Entity

- [ ] `sensor.py`
  - [ ] `MateoMealsSensor(CoordinatorEntity, SensorEntity)`
  - [ ] `name` → `Skollunch – {school_name}`
  - [ ] `native_value` → `"; ".join(today meal names)` or `"Ingen meny idag"` if none.
  - [ ] `extra_state_attributes` → as defined in `spec.md`.

**Acceptance**
- [ ] Entity id `sensor.mateo_meals_{slug}_{school_id}` created and updates daily.

---

## 5) Documentation

- [ ] `README.md`
  - [ ] What it does, requirements, installation (HACS/custom), configuration flow screenshots, example entity output.
  - [ ] Link to `spec.md`.
- [ ] `CONTRIBUTING.md`
  - [ ] Dev env, tests, linting (`ruff`, `mypy`), commit style.
- [ ] `CHANGELOG.md`
  - [ ] Add `0.1.0` with initial release notes.

---

## 6) Testing

- [ ] `tests/conftest.py` → HA test harness, fixtures for aiohttp mocked responses.
- [ ] `test_config_flow.py` → happy path, network failure, empty-week probe, options flow.
- [ ] `test_coordinator.py` → parsing, tz handling, ISO week rollover, empty arrays, backoff.
- [ ] `test_sensor.py` → state text for various days; attributes presence/absence.
- [ ] Coverage target: 85%+ (focus on config flow and coordinator).

**Run tests**
```bash
pytest -q --cov=custom_components/mateo_meals --cov-report=term-missing
```

---

## 7) Quality Gates & CI (optional but recommended)

- [ ] Add `ruff` and `mypy` configs; run on CI
  ```bash
  ruff check .
  mypy custom_components/mateo_meals
  ```
- [ ] GitHub Actions workflow for lint + tests on PRs
- [ ] Optionally add `hassfest` action for HA integration validation

---

## 8) Release Prep

- [ ] Update `CHANGELOG.md` and bump `version` in `manifest.json`
- [ ] Tag release `v0.1.0`
- [ ] Verify HACS can add by custom repo URL

---

## 9) Stretch Goals (later)

- [ ] Calendar entity exposure (optional parallel platform)
- [ ] Multiple schools per config entry (multi-select)
- [ ] Caching with ETag/If-None-Match if backend supports it
- [ ] Exception days surfaced as calendar events
- [ ] Diagnostics (`diagnostics.py`) dump for troubleshooting

---

## Quick Dev Loop

```bash
# 1) Start HA pointing to this repo (adjust config path as needed)
hass -c ./_ha_config

# 2) After code changes, reload integration from HA Dev Tools

# 3) Run tests frequently
pytest -q
```

> Reference design details live in `spec.md`. Treat `tasks.md` as the working plan.
