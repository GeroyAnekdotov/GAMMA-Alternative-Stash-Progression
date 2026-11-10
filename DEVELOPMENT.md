# Development

Keep the installable files in `gamedata/`. The checked-in XML uses Windows-1251 and LF line endings. See [Architecture](docs/ARCHITECTURE.md) for entry points, state and dependencies.

The original v1.1 archive is held locally in the ignored `_reference/` directory. Its SHA-256 is `1ddd548994a796830e675808559349c009389ec6635d56f0955ce9a4e197a705`. A clean checkout can use the [original ModDB download](https://www.moddb.com/mods/stalker-anomaly/addons/warfare-alternative-stash-progression) for historical comparison.

## Automated checks and packaging

Run from the repository root with Python 3.10 or later. The runtime tests use Lupa's Lua 5.1 binding to run the actual scripts with mocked Anomaly/GAMMA calls.

```sh
python -m pip install lupa
python -m unittest discover -s tests -v
python tools/build_release.py --check
python tools/build_release.py
```

`--check` validates the payload without writing a ZIP. `--test` builds an installable test edition. Omit it for a full release package. A build reads `VERSION.json`, verifies the ZIP and writes its SHA-256 sidecar in `dist/`. An identical existing ZIP is reused. Changed payloads require a new version. The builder delegates local MO2 delivery to the shared workspace helper when present.

Run the installed-source audit in LuaJIT as well. It uses the selected MO2 providers and a byte-verified Anomaly task manager. It runs native Lua functions and both installed wrapper bodies with mocked engine services and controlled RNG. The harness compares task counters, shared unlocks, location-specific loot, failure paths, save callbacks and debug parity. Native UI, VFS bindings and save serialization require in-game checks.

```powershell
$env:GASP_MO2_ROOT = '<MO2 instance directory>'
python -B -m unittest discover -s tests -v
python -B tests/research_gamma_stash_progression.py --mo2 "$env:GASP_MO2_ROOT" --task-script '<extracted task_manager.script>' --current-only
```

Omit `--current-only` to include the historical assertions. That mode also needs the v1.1 reference ZIP and the preserved v2.0.4 and v2.0.5 TEST ZIPs in `dist/`. See the [research record](docs/RESEARCH_GAMMA_STASH_PROGRESSION.md) for source fingerprints and context.

Setting `GASP_MO2_ROOT` also runs the installed MCM tests. They load the effective `ui_mcm.script` from the active providers for `GASP_MO2_PROFILE` (default `G.A.M.M.A`). The tests execute the native panel rebuild, option callbacks and persistence logic with simulated X-Ray controls and an in-memory settings store.

## In-game checklist

Use a disposable profile or backed-up saves. Record GAMMA, Anomaly, MCM and any WALO versions, enabled add-ons, and results. Exercise Story Mode, Warfare without WALO, Story + Warfare, and a WALO profile where available.

Open MCM in English and Russian at the usual resolution and at a smaller supported one. Check the introduction directly below the banner, the Chance Preset label, and the technical explanation below the yellow slider. Scroll to the last line and check paragraph spacing, wrapping and overlap.

1. Install through MO2. Disable all old copies and restart the game. Check both languages on a fresh profile, including the tooltips and the Very Fast default. Upgrade a v2.0.3 profile with a saved Very Fast index and 20% / 20% sliders. Confirm Custom appears, then select Very Fast twice and verify 16% / 16%. Cycle all four presets and drag one slider to 0% or 100%. Check that the other slider stays put and that returning to the matching value restores the named caption. Try Reset, Cancel with discard confirmation, and Restore Defaults with and without Apply. Reopen the panel, load a save and restart the game to verify the applied values. Verify a v1.1 profile keeps its custom rates and a v2.0.2 profile keeps both switches.
2. Test ordinary dead stalkers with both zombie settings, a zombified stalker with the setting OFF then ON, a mutant corpse, and both combinations with Enabled OFF. Use an eligible sample or temporary debug instrumentation in the test profile so chance misses are distinguishable from exclusion.
3. Save and reload after a corpse's first roll and check that it cannot roll again, including after flipping the zombie setting. Load a v1.1 save with an already rolled corpse and repeat.
4. Enable Debug Mode. With the stash chance at 100%, test yellow chance at 0% and 100% while task progress is already eligible. Check `Task progression unchanged: YES`, marker and cache confirmation, and the before/after values for the task counter and reward index. An ordinary stash leaves all toolkit flags alone. A confirmed rare stash with a newly unlocked repair toolkit reports its section and a new flag attributed to `CORPSE STASH`. Account for the separate native 5% corpse listener.
5. In a disposable profile with both copies enabled, verify the log reports the legacy script, only the old menu appears, and the renamed copy registers no callbacks. Disable the old copy and restart to verify the renamed version takes over.
6. Check Debug Mode with the main switch off and compare ordinary and rare outcomes with Debug Mode off. Look for `[GASP DEBUG]` in the console and the newest `Anomaly/appdata/logs/xray_*.log`. Include the attempt and the before/after lines when sharing a report. Logging uses Anomaly's `printf`, which calls the engine logger or the engine debug-message command. The engine log buffer is written when flushed. The LuaJIT harness verifies messages sent to `printf`; live display and file output remain manual checks. [Engine log buffer and flush](https://github.com/themrdemonized/xray-monolith/blob/master/src/xrCore/log.cpp)
7. In one save, generate Basic through a task and look for Advanced from a corpse on a suitable map. In a separate save, generate Basic or Advanced from a corpse, save and reload without visiting the cache, and verify that a subsequent native yellow stash can advance to the next tier where the map permits it. Compare a southern map and Jupiter Underground. Confirm that ammo or drug kits and failed allocations leave repair-toolkit flags alone.

## Release

Synchronize `VERSION.json`, Lua headers, both READMEs, the changelog and release notes. Run the checks and verify the MO2 ZIP and SHA-256 sidecar. Keep earlier ZIPs for rollback. Tag the release commit with an annotated `v<version>` tag after validation.

Before an authorized GitHub publication, confirm redistribution rights and review the files and Git metadata that will become public. Verify the dedicated `GeroyAnekdotov/GAMMA-Alternative-Stash-Progression` target and create a draft with the English notes, `_MO2.zip` and `.sha256`. Check the assets before publishing. Record automated and in-game checks separately.
