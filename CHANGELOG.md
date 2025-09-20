# Changelog

## 1.2.1b - 2025-09-20
Bugfix / beta patch:
- Fix options flow: changing non-interval options (days ahead, school, serving window, include weekends) now triggers an automatic config entry reload so entities are recreated correctly.
- Maintain in-place update when only the polling interval changes (no unnecessary entity reload).
- Internal snapshot tracking of options to detect meaningful changes.
- Improves reliability of day sensor count updates without requiring a manual restart.

## 1.2.0 - 2025-09-20
- Add calendar platform exposing upcoming meals as events.
- Add day offset sensors (e.g., today + next days) with weekend skipping logic.
- Introduce options flow (days ahead, update interval hours, serving window, include weekends).
- Dynamic polling interval updates without full reload.
- Implement proper unload handling and service deregistration when last entry removed.
- Reduce sensor attribute size; improve meal data normalization.
- Translation schema fixes; manifest and hacs.json compliance adjustments.
- Developer convenience scripts for resetting and running HA dev instance.
 
## 1.0.0 - 2025-09-15
- First stable feature set.
- Core meal sensor with daily data retrieval.
- Basic attribute formatting and error handling.
- Initial DataUpdateCoordinator implementation.
- Added refresh service for manual updates.
 
## 0.1.0
- Initial scaffold for HACS integration
