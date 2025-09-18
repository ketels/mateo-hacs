# Mateo School Meals integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This is a cutom integration for Home Assistant to expose Swedish school lunches from Mateo public endpoints.


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



<!-- Badges -->
[releases-shield]: https://img.shields.io/github/v/release/ketels/mateo-hacs?style=for-the-badge
[releases]: https://github.com/ketels/mateo-hacs/releases
[license-shield]: https://img.shields.io/github/license/ketels/mateo-hacs?style=for-the-badge
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/ketels
