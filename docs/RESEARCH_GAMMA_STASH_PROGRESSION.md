# GAMMA stash progression compatibility audit

**10 November 2026** · Published v1.1 and development v2.0.4

This report preserves the pre-fix findings. The full harness loads the historical v1.1, v2.0.4 and v2.0.5 ZIPs and separately checks the current implementation. The current-source mode needs only the installed GAMMA providers and the verified Anomaly task script.

## Resolution in v2.1.0

The current addon bypasses the task rarity gate for ordinary requests. For rare requests it uses an isolated copy of the verified installed setter. Both paths leave the task count and reward index untouched. A confirmed rare cache may advance the shared toolkit flags for the actual repair kit in its contents. The current LuaJIT suite covers both toolkit progression directions, both audited wrapper bodies, rejected requests and failures. See [architecture](ARCHITECTURE.md) for the shipped behavior.

## Historical findings

Both versions can spend completed-task progress when the addon's ordinary corpse-stash roll succeeds. Setting Yellow Stash Chance to 0% disables the addon's forced-yellow roll, while GAMMA can still make the ordinary request rare. Forced-yellow requests restore the task count but can set GAMMA's persistent toolkit unlock flags and change what a later task stash contains. The flags, rather than `toolkit_reward_last`, govern that change in the examined profile.

## Installed implementation

The selected portable MO2 2.5.2 profile is `G.A.M.M.A`. The winning English and Russian version strings identify GAMMA **0.9.5**. Both launcher definition files contain `920`, which is a separate installer identifier. The profile enables v2.0.4 and WALO and disables the v1.1 copy and both installed Black Road Revisited alternatives. The v1.1 archive's MD5 `f1cb51274d06b9dde6d1b8aef6997dd1` matches ModDB. MO2 profile `modlist.txt` · GAMMA version string (`configs/text/eng/_game_version.xml:4`) · [Published v1.1](https://www.moddb.com/mods/stalker-anomaly/addons/warfare-alternative-stash-progression)

I resolved loose-file conflicts from the selected profile's enabled entries in priority order, checked Overwrite and the base game's loose files, and inspected the installed Anomaly script archives. This identifies the expected MO2 VFS provider from its inputs. The audit did not start a new process inside the game VFS.

| Resource | Provider and evidence |
| --- | --- |
| `scripts/treasure_manager.script` | **G.A.M.M.A. Rare Stashes Balance** wins over enabled 62 No Loot and 60 Stash Overhaul. SHA-256 `788f9c8a43eae96728ea8ddba3d67db8d9438f7adaa74600a11923d2c69fa65d`. Source (`scripts/treasure_manager.script:365`) |
| `items/settings/grok_treasure_manager.ltx` | **Rare Stashes Balance** wins over 63 BAS, 62 No Loot and 60 Stash Overhaul. SHA-256 `2c44075513efc039078d3b05e4c3253cb81d15a56f4c407b77cb51311985a8a9`. Rare settings (`configs/items/settings/grok_treasure_manager.ltx:160`) |
| `scripts/task_manager.script` | No loose override. I extracted the installed `db/configs/scripts.db0` into a temporary folder and verified that its task manager is byte-identical to the shared unpacked copy. SHA-256 `dc7131f946ca965503752ab356e3d4a3c801fdf0d7caa7971e917cb4611d0ebd`. The installed modded-exes archive has no copy of this file. Verified task callback (`scripts/task_manager.script:187`) |
| `scripts/xr_effects.script` | **G.A.M.M.A. Quests Rebalance** supplies `reward_stash`. An example task invokes `reward_stash(true)` in its completion effects. Reward function (`scripts/xr_effects.script:1403`) · Task example (`configs/misc/task/tm_escape.ltx:69`) |

Two enabled mods wrap `set_random_stash`. Descriptive Stash Coordinates delegates to the original function and replaces the notification with a location description. RNG Attach Kits v2.3 can add bonus items and make additional RNG calls before delegating. Neither wrapper writes the toolkit counters or flags in the examined path. The tests isolate the winning GAMMA functions and do not execute these wrappers. A late Lua exception could leave Descriptive Stash Coordinates' notification suppression flag set until another call reaches its cleanup. This is a source-level risk, with live impact unverified. Descriptive Stash Coordinates (`scripts/descriptive_stash_coordinates.script:31`) · RNG Attach Kits wrapper (`scripts/rng_attachments_core.script:130`)

## Task progression and cache creation

1. Anomaly's `task_callback` runs completion effects and calls `give_reward`, then adds one to `toolkit_reward_count`. A task with `reward_stash(true)` checks for a stash before the task's own increment. This effect has a separate 50% roll to offer a stash. Other tasks can have different effects or no stash reward. Task completion (`scripts/task_manager.script:224`) · Reward effect (`scripts/xr_effects.script:1403`)
2. `create_random_stash` calls `get_random_stash`, then calls `set_random_stash` if it finds an ID. The chooser takes available entries (`caches[id] == false`), applies the default marked-stash map filter and the nearby-level check, and draws a candidate. It forces local selection regardless of the caller's fourth argument. It returns early for an empty candidate list or an invalid server object. The wrapper does not propagate the ID returned by `set_random_stash`, so a normal return from `pcall` alone cannot confirm that a cache was created. `last_secret` can be set before a suitable candidate exists and is also unsuitable as a success check. Creation and location selection (`scripts/treasure_manager.script:365`)
3. The rare gate applies when the actor exists and `no_spot` is neither `true` nor a string. The static LTX threshold is **7** and the chance factor is `50 * count / 7`. A rare stash requires both `count >= 7` and a random integer from 1–100 **strictly below** the factor. That gives 49% at count 7, 99% at 14, and certainty at 15 or higher, conditional on reaching the gate. Neither the threshold nor the factor depends on location. Passing the gate resets the count to zero and advances `toolkit_reward_last` **before** loot generation or marker placement. A task reward that uses the count can consequently leave the count at one after the task's own increment. Rare gate (`scripts/treasure_manager.script:495`) · LTX values (`configs/items/settings/grok_treasure_manager.ltx:170`)
4. The manager draws ordinary or rare loot from configured item-kind and weight rules and the stash location's `map_tiers`. It may add ordinary extras, and for a rare stash with nonempty content it makes a separate toolkit draw. Successful creation saves the item sections in `caches[id]` and adds a map spot and notification where applicable. Opening the box materializes the saved contents. A finite set of nearby free caches and the shared RNG can still change subsequent stash locations or draws even when task progression state is isolated. Loot selection (`scripts/treasure_manager.script:523`) · Commit and opening (`scripts/treasure_manager.script:762`)

### Which state matters

| State | Meaning and persistence |
| --- | --- |
| `toolkit_reward_count` | Actor persistent variable. Completed tasks increase it. Eligible stash requests use it to determine rarity and successful rare decisions reset it. Missing is read as zero by GAMMA. |
| `toolkit_reward_last` | Actor persistent variable. A rare decision advances a one-based index that wraps at the length of `reward_bonus`. The code that would select and add `reward_bonus[new_index]` is commented out in this profile. The installed manager still updates the index, but it does not use that index to select the awarded toolkit. The other installed stash managers need separate evaluation if enabled. |
| `actor_find_basic_kit`, `actor_find_advanced_kit`, `actor_find_expert_kit` | Actor ALife info portions. The installed manager reads and sets them during loot generation, before the player opens the stash. They gate higher repair toolkits and survive in the actor's game state. |
| `treasure_manager.caches` and `caches_count` | GAMMA save/load callbacks store cache availability and queued contents. Map spots are engine state. |
| `warfare_stash_progression_used_corpses` | Shared v1.1 and development save field for addon corpse IDs. GAMMA's independent corpse listener uses `corpse_stashes`. |

Actor variables use `save_var` and `load_var` over `pstor`. The Lua tests model engine serialization of actor variables, info portions and map spots and invoke the actual Lua cache and addon save/load callbacks. Actor variable helpers (`scripts/_g.script:2568`) · GAMMA cache serialization (`scripts/treasure_manager.script:975`)

## Toolkit odds by location

The location of the **stash box** supplies a weighted vector from `tools_map_tiers`. GAMMA draws a tier and then draws or selects a kit from that tier. Tier 1 is a 50/50 ammo/medical split. Tier 2 has 3 Basic, 2 medical and 1 ammo entry. Tier 3 has 5 Basic, 2 Advanced, 1 medical and 3 ammo entries. Tier 4 targets Advanced and tier 5 targets Expert. A tier 3 or 4 Advanced result becomes Basic if the Basic flag is missing. A tier 5 result becomes Basic if Basic is missing or Advanced if Basic exists and Advanced is missing. Ammo and medical results can leave repair progression unchanged. Thus a player may receive repeated Basic kits, and a map with no tier 5 cannot produce an Expert through this draw. Map vectors (`scripts/treasure_manager.script:92`) · Toolkit and flag branches (`scripts/treasure_manager.script:654`)

I compared all 33 installed map vectors with the public 0.9.5 table's underlying JSON. The rounded **Basic, Advanced and Expert** percentages match for all 33 maps when the actor has the prerequisite flags. All five columns match for 10 maps. The published medical and ammo columns are equal in the examples below, while the local tier pools are asymmetric. Their combined rates agree within one percentage point for all 33 maps, consistent with published integer rounding. The reason for the split in the published data was not established. These are conditional toolkit distributions for rare caches with content, rather than per-task odds. [Public 0.9.5 table](https://stalker-gamma-db.com/db/gamma-0.9.5/toolkit-rates?lang=en&view=table) · [Table data](https://raw.githubusercontent.com/simonwdev/stalker-anomaly-gamma-db/main/site/public/data/gamma-0.9.5/toolkit-rates.json)

| Map | Installed raw rates, % (Basic / Advanced / Expert / Medical / Ammo) | Published rates, % |
| --- | --- | --- |
| Cordon | 40 / 0 / 0 / 36.67 / 23.33 | 40 / 0 / 0 / 30 / 30 |
| Garbage | 42.61 / 4.55 / 0 / 29.36 / 23.48 | 43 / 5 / 0 / 26 / 26 |
| Jupiter | 9.09 / 53.64 / 30 / 1.82 / 5.45 | 9 / 54 / 30 / 4 / 4 |
| Jupiter Underground | 0 / 80 / 20 / 0 / 0 | 0 / 80 / 20 / 0 / 0 |

For example, with neither repair flag set, every Advanced or Expert draw in Jupiter Underground initially yields Basic. With only Basic set, both yield Advanced. With both flags, the underlying 80/20 split applies. The task counter changes the chance to reach this draw. The actor flags change its result.

## v1.1 and development compared

The v1.1 archive's `warfare_stash_progression.script` lines 32–51 gate the feature by Warfare by default, with the old opt-in for other modes. Lines 55–90 temporarily raise the count to 1,000,000 only for forced yellow and restore it after the protected call. Ordinary requests leave the actual count visible. The original comment describes advancing the toolkit reward sequence, but the installed manager's actual toolkit selection depends on the box location and info portions.

Development v2.0.4 retains the same rare interaction. It snapshots the actor, preserves an originally absent count as `nil` rather than v1.1's explicit `0`, and puts the temporary write in the protected call. It retains the same corpse save key and attempt-before-roll behavior. Removing the Warfare gate and allowing zombified stalkers by opt-in expand where the inherited issue can occur. The renamed scripts and duplicate-registration guard address coexistence with v1.1. They leave the native GAMMA corpse listener independent.

The installed **Rare Stashes Balance** also provides `grok_stashes_on_corpses.script`. It independently registers `npc_on_use`, rolls 5% and calls the same stash manager. It can spend the task count with this addon absent. With either addon enabled, a single eligible search can succeed in both handlers and use two different free caches. The audit reproduced two markers when both rolls were forced to succeed. The order in which a live game invokes the callbacks and the actual duplicate frequency remain unverified. Perk-Based Artefacts can additionally filter loot at box opening, downstream of these progression writes. Native corpse listener (`scripts/grok_stashes_on_corpses.script:21`) · Perk-Based Artefacts (`scripts/zz_treasure_manager_pba_less_artys.script:65`)

## Reproduction

[Isolated Lua audit](../tests/research_gamma_stash_progression.py) reads the selected profile, the original v1.1 archive, the current tree and a byte-verified `task_manager.script`. It executes the installed cache chooser, stash generator, task callback, task reward effect and cache save/load functions in Lua 5.1. Deterministic RNG inputs, a synthetic nearby map graph, free boxes and a minimal loot pool make state changes comparable. The toolkit test uses the actual Jupiter Underground tier vector and selects its tier 4 entry. For task cases, the harness dispatches the named completion effect; it does not emulate quest conditions or dialogue. JSON lines record counts, index, flags, contents, spots, used IDs and errors. Run explicitly with Lupa installed.

```powershell
python -B tests/research_gamma_stash_progression.py --mo2 '<MO2 instance directory>' --profile 'G.A.M.M.A' --task-script '<extracted task_manager.script>'
```

All audit assertions passed. In the table, **C** is the task count and **L** is the legacy index. The paired v1.1 and v2.0.4 outcomes agree except where noted. The main baseline isolates task rewards with no corpse listener running. A separate comparison enables the native GAMMA listener to account for the real profile's independent corpse chance.

| Scenario | Baseline | v1.1 and development |
| --- | --- | --- |
| A. Standard task reward | From C6/L1, first stash ordinary and count becomes 7. Second stash rare, Basic flag set, C1/L2 after completion. | Same with no corpse search. |
| B and F. Ordinary corpse request at 0% yellow | Search leaves C7/L1 and no flags. | With a winning GAMMA rare roll, search gives a yellow Basic stash, C0/L2 and Basic flag. Below threshold at C6 or with a losing rare roll at C7, it stays ordinary and preserves the count and index. |
| C and G. Forced yellow at 100% | Search leaves C7/L1 and no flags. | Search gives a yellow Basic stash, C7/L2 and Basic flag even with the controlled random roll that would miss at C7. |
| D. Next task immediately after B or C | Yellow Basic stash, C1/L2. | After B, ordinary task stash and C1/L2. After C, yellow Advanced stash and C1/L3, since Basic was already set by the corpse. |
| E. Three searches, three completed tasks without stashes, then a task with a stash | C7 → C7 → C10 → C1, yellow Basic. | Ordinary branch: C7 → C0 → C3 → C4, next task stash ordinary. Forced branch: C7 → C7 → C10 → C1, next task stash yellow Advanced. Three forced stashes wrap L1 → L1 before that final task, while the repair flags remain set. |
| H. Save and reload after forced yellow | C7/L1 and no flags survive the mocked round trip. Next task gives Basic. | C7/L2, Basic flag, queued cache contents, marker and used corpse ID survive. Re-search gives no addon stash. Next task gives Advanced. |

Failure probes used the same source functions:

- **No available cache:** no rare decision and no counter or flag change. The addon still records the corpse attempt. The native wrapper logs the missing ID and gives the caller no success value.
- **Empty generated contents:** a zero-weight fixture reaches the rare gate but yields no item or marker. The ordinary branch can leave C0/L2. The forced branch restores C7 but leaves L2. Neither branch sets a toolkit flag in this fixture. How often empty contents occur with the real loot pool is unknown.
- **Late exception:** an injected failure during marker placement left no cache loot or marker in the fixture. The ordinary branch left C0/L2 and Basic set. The forced branch restored C7 and left L2 and Basic set. The existing `pcall` catches the exception but cannot undo those writes.
- **Previously absent counter:** forced yellow leaves explicit zero in v1.1 and restores absence in development.

The confirmed issue is progression interference, with no evidence of save corruption. The ordinary path can redirect accrued tasks to a corpse reward or spend them before a late failure. Forced yellow preserves the count and therefore the same native rare gate probability for an equivalent future request, but changes repair eligibility and can consume a nearby cache. Other loot and RNG changes are possible. Timing and frequency in a real playthrough were not measured. Live engine serialization, marker behavior and wrappers still need in-game testing.

## Integration options

| Approach | Changes and trade-offs |
| --- | --- |
| **A. Isolate and restore state** | Suppress the native rare gate during ordinary corpse requests and snapshot actor variables and toolkit info portions for forced requests. Restoring count and index alone is insufficient. Restoring info portions after callbacks or marker work has begun cannot reliably undo observers, delayed work or nested changes by another mod. This approach needs no save schema change and keeps the current loot algorithm, but has high compatibility and maintenance risk. It also leaves the independent native corpse roll. |
| **B. Use the existing cache API** | Select with `get_random_stash(nil, ...)` to retain the normal marked-stash map filter, then call `set_random_stash("treasure", ...)` for ordinary corpse stashes. The string bypasses task rarity and sets the marker. The audit confirmed C7/L1 and no flags changed. Passing `"treasure_searched"` also leaves progression unchanged, but only paints a yellow marker over **ordinary** loot. The existing `bonus_items` parameter can add an explicitly selected toolkit, but duplicates the toolkit rules if used as a replacement for native rare generation. No new save state is needed. Keep both existing wrappers and the shared cache allocator in the path, and validate return values and box reuse before any retries. |
| **C. Add a narrow context at the native rarity decision** | Ask upstream for, or maintain a version-checked compatibility adapter around, a single request context with explicit common/rare mode. Scope its changes to the rarity and task-counter block and the toolkit flag writes. Keep the existing location and loot code. In isolated rare mode, read the current actor toolkit flags for eligibility and leave them unchanged. Commit the cache once, return its ID only after success, and let ordinary task requests retain all existing behavior. This preserves toolkit distribution for a given map and existing flag state, though repeated isolated corpse stashes may remain restricted to Basic until normal progression advances. Existing save fields suffice. Wrappers currently forward five arguments, so an extra argument needs forwarding tests or a narrowly scoped request context consumed by the intended call. A full replacement would increase maintenance and conflict with other mods. |

**Recommendation.** Use B for independent ordinary stashes and C for true rare corpse stashes with GAMMA's loot and gate rules. Prefer an upstream entry point that preserves wrappers. Treat the version and capabilities of the manager as a condition for enabling the rare route. Until that interface is validated, limit an independent implementation to ordinary stashes or defer release. Keep the existing corpse save key. Decide explicitly whether the native GAMMA corpse roll should remain as a separate chance. Suppressing it would change base GAMMA behavior, while keeping it allows two rewards if both rolls succeed.

The historical proposal to isolate all toolkit flags was implemented in v2.0.5. Starting in v2.0.6, the addon intentionally commits shared flags for matching repair kits in confirmed caches. Keep the historical and current expectations separate when rerunning the audit. Use the [in-game checklist](../DEVELOPMENT.md#in-game-checklist) for engine and profile coverage.

## ModDB v1.1 recommendation

The listing's statement that task-based progression remains unchanged is unsupported for the examined implementation. Tasks still give their normal rewards, but an addon corpse stash can spend their count or set flags used by later task rewards. Mark v1.1 as having a known compatibility issue. It can remain available as a clearly marked legacy download if the warning is visible before download. If ModDB offers a reversible pause for this addon and a warning cannot be made sufficiently visible, a temporary pause until the corrected ZIP is verified is reasonable. Public ModDB material documents archiving for mod profiles, but does not establish a temporary suspend control for this particular addon. [Published listing](https://www.moddb.com/mods/stalker-anomaly/addons/warfare-alternative-stash-progression) · [ModDB editor on archiving](https://www.moddb.com/forum/thread/how-to-archive-my-own-mod)

A new versioned ZIP with a corrected description and a clean MO2 replacement is sufficient to prevent new addon side effects once the implementation passes validation. Retain historical files and preserve the existing corpse key. No save migration is indicated. Previously spent task progress and set flags cannot be attributed safely after the fact, so automatic restoration could award progress twice or erase legitimate task-earned unlocks. No publication changes were made during this audit.
