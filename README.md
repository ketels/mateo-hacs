# Mateo School Meals (HACS)

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

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

<!-- Badges -->
[releases-shield]: https://img.shields.io/github/v/release/ketels/mateo-hacs?style=for-the-badge
[releases]: https://github.com/ketels/mateo-hacs/releases
[license-shield]: https://img.shields.io/github/license/ketels/mateo-hacs?style=for-the-badge
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/ketels
