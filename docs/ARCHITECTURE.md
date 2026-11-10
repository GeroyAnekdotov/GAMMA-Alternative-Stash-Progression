# GAMMA Alternative Stash Progression architecture

The verified target is GAMMA 0.9.5 with Rare Stashes Balance and Anomaly MCM 1.7.1. The [research record](RESEARCH_GAMMA_STASH_PROGRESSION.md) identifies the manager and wrappers used for compatibility checks.

## Files and initialization

| File | Responsibility |
| --- | --- |
| `gamedata/scripts/gamma_alternative_stash_progression.script` | Registers Anomaly callbacks, checks corpse eligibility, requests GAMMA stashes and tracks used corpse IDs. |
| `gamedata/scripts/gamma_alternative_stash_backend.script` | Verifies the native manager and wrapper chain, allocates one cache and invokes ordinary or isolated rare generation. |
| `gamedata/scripts/gamma_alternative_stash_debug.script` | Reads actor state, config, location and markers for event-driven diagnostics. |
| `gamedata/scripts/gamma_alternative_stash_progression_mcm.script` | Supplies the localized switches, presets, sliders and shared defaults. Imports stored values from the old MCM namespace and registers no gameplay callbacks. |
| `gamedata/configs/text/{eng,rus}/st_gamma_alternative_stash_progression.xml` | Supplies the MCM title, labels and descriptions in Windows-1251. |
| `tests/` and `tools/build_release.py` | Exercise Lua entry points and installed GAMMA and MCM functions, and validate the six-file MO2 payload. |

Anomaly discovers `on_game_start` by scanning the script directory. The gameplay module registers `npc_on_use`, `actor_on_first_update`, `server_entity_on_unregister`, `save_state` and `load_state` with `RegisterScriptCallback`. Anomaly's callback registry keys handlers by function identity. MCM independently discovers `*_mcm.script` and calls `on_mcm_load`. Both entry points check the virtual script directory for the old gameplay script. If present, the renamed version logs an upgrade instruction at startup, registers no callbacks and omits its MCM menu. Disable the old MO2 mod and restart to activate the renamed version.

## Settings and upgrade

Gameplay reads `enabled`, `include_zombified_stalkers`, `debug_mode`, `stash_chance` and `yellow_chance` through `ui_mcm.get` under `gamma_alternative_stash_progression/`. The three switches default to ON, OFF and OFF respectively. Both sliders default to 16% from Very Fast. MCM applies a selected preset to both sliders through its native preset handler. Gameplay reads the committed slider values. There is no game-mode gate.

Before MCM receives the menu, the MCM module copies each supported switch or rate from the old path only if the new path is missing. It uses the same `axr_main.config` store and `[mcm]` section as MCM. Stored OFF and 0% count as values. A valid previously saved preset may fill an unset slider when neither namespace has a saved value for it. The old settings remain in the profile for rollback.

The selector uses MCM's `curr` functor for an initial read of the saved rates. The slider construction hooks take the values shown by `Register_Track`. Later edits receive the value from `Callback_Track` via `on_selection_functor` and update just the caption. This avoids the installed MCM 1.7.1 `get_gui()` scope bug, where the accessor reads a different variable from the one assigned by the GUI. **Custom** is a caption and the list offers four choices.

X-Ray emits a selection event only when the item token changes. The hook neutralizes that token once per newly built combo using `ClearList` and restores the four choices. The native preset handler stages each rate in turn and rebuilds the panel once. Caption updates wait for both sliders on that rebuild. [X-Ray combo box source](https://github.com/themrdemonized/xray-monolith/blob/master/src/xrGame/ui/UIComboBox.cpp)

Apply commits the pending sliders and switches through MCM. The derived caption uses `curr`, so the old preset key remains a migration input. Cancel discards pending changes after confirmation. Reset clears pending changes on the current page. Restore Defaults stages the page defaults for Apply. Gameplay reads only the committed settings.

These are the intentionally retained legacy identifiers:

| Identifier | Purpose |
| --- | --- |
| `warfare_stash_progression_used_corpses` | Save table field read and written directly by both versions. |
| `warfare_stash_progression/` with `enabled`, `include_zombified_stalkers`, `preset`, `stash_chance` or `yellow_chance` | Read-only inputs for MCM settings migration. The obsolete game-mode option is ignored. |
| `warfare_stash_progression.script` | Virtual filesystem lookup to prevent duplicate gameplay and save handlers. |

## Corpse and stash flow

```text
Anomaly npc_on_use
  -> Enabled + dead entity classified as a stalker by IsStalker
  -> character_community: require opt-in for "zombied"
  -> skip a used ID, otherwise mark it used
  -> roll using Stash Chance from Corpse
  -> on success, use Yellow Stash Chance to request a yellow/toolkit stash
  -> choose one GAMMA cache with the normal map filters
  -> run the ordinary or isolated rare setter and verify its cache result
  -> for a confirmed rare cache, commit staged flags for matching repair toolkits
```

The engine's stalker classification runs before the community check. A zombified stalker can use the existing path when opted in. Mutant-class entities never reach the community filter. The corpse is marked before rolling, so a miss or stash failure still consumes its attempt. The save field stores a table of numeric server IDs mapped to `true`. Loading a save replaces the active table, with an empty table for saves that predate the addon. Unregistering a `se_stalker` removes its ID so a future entity can reuse it.

The backend reads the effective script through the MO2 game path and checks normalized source fingerprints and function origins. Ordinary requests use `get_random_stash(nil, ...)` with the default map filter, then `set_random_stash("treasure", ...)` to bypass the rarity gate. The backend confirms the returned ID and nonempty contents in GAMMA's cache table. A failed attempt consumes the corpse roll and has no automatic retry. A late exception can leave a marker without confirmed contents if the engine has already placed it.

Rare requests compile a private copy of the verified native setter. The adapter forces the rare branch, removes the task rarity block, and redirects nine native toolkit writes into a per-request table. Reads within that call see both staged flags and the live actor's flags. The adapter binds the manager's live loot tables and uses its shared cache table. The installed location vectors and native fallback branches still determine the contents. The public task setter stays in place. When the audited wrappers are active, a scoped delegate routes only the selected cache through the adapter and is restored after the call. The original wrappers still add attachments and describe locations. If the engine cannot inspect the functions or the script versions differ, addon requests fail closed.

Both paths leave `toolkit_reward_count` and `toolkit_reward_last` alone. Once the rare setter returns the allocated ID and a nonempty cache, the backend checks exact item sections before committing matching staged flags through the same actor API used by GAMMA. Failed requests, ordinary caches and ammo or drug kits leave the unlocks alone. The next task or corpse yellow stash reads the same native `actor_find_basic_kit`, `actor_find_advanced_kit` and `actor_find_expert_kit` flags. Unlocks happen at cache generation, ahead of collection, and use the actor's existing save data.

Cache availability and shared RNG can still vary after an extra stash. GAMMA's native 5% corpse listener has its own roll and save key. Both listeners can reward the same corpse, and the native listener can still spend task progress. The addon preserves historical counters and flags.

## Diagnostics

Debug Mode logs eligibility and actual RNG results at corpse use time. It also reports a snapshot on the actor's first update when enabled, including with the main switch off. Cache allocation, confirmed creation and observed marker creation are separate log fields. It reads generated toolkit sections from confirmed rare cache contents and labels committed false-to-true flags as `CORPSE STASH`. `Task progression unchanged` compares the task counter and reward index. Unexpected flag changes are reported separately. Native task unlocks are visible in the next snapshot. Missing actor state and unavailable marker reads are reported as unknown. It reads the verified manager's LTX threshold and chance factor to estimate increments until eligibility. Individual task effects determine whether a stash is offered, and a completion effect can run before the task increments the counter.

## Compatibility and extension points

- Keep the save field and table shape. Test a save from the previous version if changing eligibility, unregister handling or persistence.
- Keep the menu ID, runtime paths and both XML files in sync. Changes to MCM discovery or Anomaly's config store can affect migration. Keep migration ahead of default writes.
- Keep cache requests synchronous. Verify source fingerprints, wrapper behavior, and task-state parity again when GAMMA changes the native manager.
- Add eligibility rules before marking the corpse used. Keep ordinary and opted-in zombified stalkers on the same roll path. [In-game checklist](../DEVELOPMENT.md#in-game-checklist)
