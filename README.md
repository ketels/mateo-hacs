# Mateo School Meals integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This is a cutom integration for Home Assistant to expose Swedish school lunches from Mateo public endpoints.

## Features

- Base sensor with state = today's meal name (or Swedish fallback 'Ingen meny idag')
- Configurable set of fixed day sensors (today + N forward school days)
- Weekend skipping logic (if weekends excluded, day offsets count only weekdays)
- Calendar entity exposing each meal as an event within a serving window
- Configurable: days ahead, update interval (hours), serving start/end, include/exclude weekends
- Graceful fallback state "No menu" for future day sensors without published meals (instead of `unknown`)

## Entities

After configuring a school you will get:

- `sensor.skollunch_<school>` – today meal summary (legacy base sensor)
- `sensor.skollunch_<school>_today` and `sensor.skollunch_<school>_day1..dayN` – per‑day menu (semicolon‑separated meal names; state "No menu" if that day currently has no meals published)
- `calendar.<school>_menu` – calendar events for each meal (summary = meal name, start/end within configured serving window; weekends omitted when excluded)

## Options

Accessible via the integration's Configure button:

| Option | Description | Default |
| ------ | ----------- | ------- |
| Days ahead (`days_ahead`) | Number of forward days (today +) for which fixed sensors are created (max 14). When weekends excluded, this counts school days, not raw days. | 5 |
| Update interval hours (`update_interval_hours`) | How often to poll Mateo endpoints | 4 |
| Serving start (`serving_start`) | HH:MM start time applied to calendar events | 10:30 |
| Serving end (`serving_end`) | HH:MM end time applied to calendar events | 13:30 |
| Include weekends (`include_weekends`) | If true include Sat/Sun in calendar + sensors; otherwise day offsets skip weekends | False |

Changing options triggers a reload of entities (new day sensors added/removed as needed).

## Calendar Usage

Use any HA calendar consumer (e.g. Calendar panel, automations) to react to upcoming meals. The next (ongoing or upcoming) event is exposed via the entity's `event` property. When weekends are excluded, Saturday/Sunday are filtered out entirely. Each event spans the configured serving window.

## Localization

Meal names are shown as-is (Swedish). The base sensor shows 'Ingen meny idag' when today has no meals. Future day sensors show 'No menu' until meals are published.


### HACS (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ketels&repository=mateo-hacs&category=integration)

-- or --

2. Add this repository as a custom repository in HACS:
   - Open HACS in Home Assistant.
   - Go to **Integrations**.
   - Click on the three dots in the top-right corner and select **Custom repositories**.
   - Add the following URL: `https://github.com/ketels/mateo-hacs`.
   - Select **Integration** as the category.
3. Search for "Mateo School Meals" in the HACS integrations list and install it.

### Manual Installation

1. Download the latest release from the [GitHub Releases page](https://github.com/ketels/mateo-hacs/releases).
2. Extract the downloaded archive.
3. Copy the `custom_components/mateo-hacs` folder to your Home Assistant `custom_components` directory.
   - Example: `/config/custom_components/mateo-hacs`
4. Restart Home Assistant.

## Development / Tests

Run tests with:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

Coverage target: 75%+



<!-- Badges -->
[releases-shield]: https://img.shields.io/github/v/release/ketels/mateo-hacs?style=for-the-badge
[releases]: https://github.com/ketels/mateo-hacs/releases
[license-shield]: https://img.shields.io/github/license/ketels/mateo-hacs?style=for-the-badge
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/ketels
