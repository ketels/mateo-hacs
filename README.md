# Mateo School Meals (HACS)

Home Assistant integration to expose Swedish school lunches from Mateo public endpoints.

- One sensor per configured school
- State: today's meals summary
- Attributes: current and next ISO week meals, exception days

See `spec.md` for full specification and `tasks.md` for the build plan.

## Installation (dev)
- Add this repo as a custom repository in HACS, or copy `custom_components/mateo_meals` into your HA config.

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

Contributions welcome — see `CONTRIBUTING.md`.
