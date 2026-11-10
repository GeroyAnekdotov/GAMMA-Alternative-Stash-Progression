# Changelog

## 2.1.0

- Finalized the standalone addon for GAMMA 0.9.5 with ordinary and yellow corpse stashes, independent task rewards and shared native toolkit unlocks.
- Preserved the v2.0.8 MCM layout, English and Russian localization, settings migration and existing saves.
- Documented all distributed Lua modules and their functions. Added a current-source audit mode for checkouts without historical archives.

## 2.0.8 (test build)

- Added an introduction below the MCM banner and placed the mechanics explanation below the probability sliders in English and Russian.
- Renamed the preset label to Chance Preset / Пресет шансов and shortened the English first slider label to Stash Chance (%).

## 2.0.7 (test build)

- Kept preset and Custom labels in sync with both pending slider values. Repeated selection uses the native preset handler without rebuilding the combo during slider edits.
- Verified Apply, Cancel, Reset and Restore Defaults against the installed MCM Lua. Existing percentages and checkbox values carry forward.
- Updated English and Russian descriptions of shared toolkit unlocks, location-dependent rewards and yellow stash odds.

## 2.0.6 (test build)

- Shared Basic, Advanced and Expert toolkit unlocks between task-earned and addon yellow stashes. The addon commits an unlock when GAMMA confirms a cache containing the corresponding toolkit.
- Kept task counters and reward indices independent and retained GAMMA's location-based loot selection and fallback rules.
- Debug Mode reports generated toolkit sections and new corpse-stash unlocks separately from task-counter changes.
- Extended the LuaJIT audit to cover both directions of shared progression, failed allocations, reload and debug parity.

## 2.0.5 (test build)

- Isolated ordinary and rare corpse stashes from GAMMA's task count, toolkit index and toolkit flags.
- Kept native cache selection and rare loot in the audited GAMMA 0.9.5 manager. Unsupported manager or wrapper versions fail closed.
- Added bilingual Debug Mode for corpse eligibility, rolls, cache results and progression snapshots.

## 2.0.4 (test build)

- Display the preset that matches both current slider values, or Custom. Keep saved custom rates and allow a preset to be selected again after a manual edit.
- Revised English and Russian MCM text and preset labels.

## 2.0.3 (test build)

- Restored all four v1.1 progression presets and both 0–100% sliders. Very Fast (16% / 16%) is now the fresh default.
- Restored detailed English and Russian MCM descriptions, tooltip text and probability examples for all modes.
- Retained the two switches and imported supported v1.1 settings when the corresponding current setting is unset.

## 2.0.2 (test build)

- Renamed the gameplay, MCM and localization files to match the GAMMA Alternative Stash Progression name.
- Migrate the two stored switches to the new MCM namespace while preserving any existing values there. Keep the original corpse save field.
- Defer to the old gameplay script if it is still visible in MO2, avoiding duplicate callbacks. Document the script architecture and upgrade behavior.

## 2.0.1

- Corrected the MCM description keys so the tooltips for both switches display in English and Russian.

## 2.0.0

- Established GAMMA Alternative Stash Progression as an independent project.
- Made the Enabled switch apply across game modes. Fixed both roll rates at 16% and retired the presets, sliders and non-Warfare switch.
- Added the opt-in **Include Zombified Stalkers** toggle. It defaults to OFF and gives eligible zombified stalkers the existing roll when enabled.
- Kept the existing save and MCM identifiers. Restore the original task reward counter after a forced-yellow request, including when the stash call raises or the counter was absent.
- Updated English and Russian strings and added automated tests and an MO2 builder.

## 1.1

- Released as Warfare Alternative Stash Progression with Warfare-first defaults, an optional non-Warfare switch and adjustable roll rates. The Medium preset defaulted to 5% stash and 16% yellow.
- Cleaned up public naming and added an MCM explanation of task and corpse progression. The packaged history records no gameplay changes from the preceding tested build.

The original [v1.1 ModDB listing](https://www.moddb.com/mods/stalker-anomaly/addons/warfare-alternative-stash-progression) records the public release.
