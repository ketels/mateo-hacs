# Mateo School Meals (HACS)

Home Assistant integration to expose Swedish school lunches from Mateo public endpoints.


See `spec.md` for full specification and `tasks.md` for the build plan.

## Installation (dev)

## Development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -U homeassistant aiohttp pytest pytest-asyncio pytest-homeassistant-custom-component ruff mypy
```
Run HA pointing to a local config: `hass -c ./_ha_config`.

Run tests:
```bash
pytest -q
```

### Manual Refresh Service
Force an immediate data fetch for all configured entries via Developer Tools → Services:

Service: `mateo_meals.refresh`

Optional service data to target a single entry:
```yaml
entry_id: <config_entry_id>
```

Contributions welcome — see `CONTRIBUTING.md`.
