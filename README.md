# GAMMA Alternative Stash Progression

[Русская версия](README_RU.md)

**v2.1.0** · Developed and tested for **S.T.A.L.K.E.R. GAMMA 0.9.5** with Rare Stashes Balance and Anomaly MCM. The addon works in Story Mode, Warfare and combined play. GAMMA and its bundled MCM are the only requirements. Other GAMMA versions remain unverified.

Corpse searches offer an alternative when tasks are scarce, particularly for isolated factions such as UNISG, Renegades and Zombified.

Searching an eligible dead stalker can reveal a stash. After a successful roll, a second roll can request a yellow toolkit stash. The Very Fast preset defaults both chances to 16%, for a theoretical 2.56% forced-yellow roll rate per eligible corpse. GAMMA still handles stash placement and task rewards. Each eligible corpse can roll once through this addon, including across saves and loads.
At those defaults, the corresponding ordinary stash request rate is 13.44%. Both rates are before cache availability and loot generation.

## Installation and upgrade

1. Close the game and back up the save you plan to use.
2. Disable the superseded Warfare Alternative Stash Progression and all earlier copies in the active profile. Install `GAMMA_Alternative_Stash_Progression_v2.1.0_MO2.zip` in Mod Organizer 2 as a new mod. The old script takes precedence while it remains visible.
3. Enable the new mod, start GAMMA and open **Mod Configuration Menu → GAMMA Alternative Stash Progression**.

- **Enable Mod** defaults to ON and controls corpse rolls in every mode.
- **Include Zombified Stalkers** defaults to OFF, including for existing profiles with no saved value. Turn it ON to include dead stalker-class NPCs in the zombified community. Mutant loot follows the game's usual behavior.
- **Debug Mode** defaults to OFF. It logs eligibility, the actual rolls, cache and marker outcomes, generated toolkit sections, and progression before and after a request. New unlocks are attributed to `CORPSE STASH`. `Task progression unchanged: YES` refers to the task counter and toolkit reward index. The initial snapshot works even with corpse rolls disabled.
- **Chance Preset** sets both chances. Slow is 3% / 12%, Medium is 5% / 16%, Fast is 8% / 16%, and Very Fast is 16% / 16%. The selector shows **Custom** when the slider values differ from every preset.
- **Stash Chance (%)** and **Yellow Stash Chance (%)** can each be set from 0% to 100%, in steps of 1%, after selecting a preset.

Existing preferences in the current MCM namespace carry forward. Stored v1.1 values fill missing switches and rates. A saved preset can fill a rate only if it is unset in both namespaces. The old game-mode switch has no effect. Used-corpse data remains readable by both versions.

Apply saves the slider and checkbox values. Cancel discards pending edits after confirmation. Reset restores the page's saved values, while Restore Defaults stages Very Fast and the default switches for Apply. A yellow roll can produce ammo or medical supplies instead of repair tools.

## Task progression and compatibility

Tasks and corpse searches earn stashes independently. Ordinary corpse stashes bypass GAMMA's task rarity gate. Both ordinary and yellow corpse stashes preserve the task counter and toolkit reward index.

Yellow stashes from either source share GAMMA's Basic, Advanced and Expert unlocks. A repair toolkit unlocks its tier as soon as the stash contents are generated and confirmed. A task stash can therefore unlock a tier for a later corpse stash and vice versa. The native loot rules still use the stash location's toolkit probabilities and the actor's current unlocks. Progress already spent or unlocked by older builds remains in your save.

The adapter checks the manager and wrapper versions and stops the addon's request if they are unsupported. GAMMA's built-in 5% corpse listener remains active and can independently award a second stash or use the task count as usual. Both systems draw from the same pool of available boxes, so a successful roll may still find no free cache.

For a bug report, enable Debug Mode and share the relevant `[GASP DEBUG]` lines from `Anomaly/appdata/logs/xray_*.log` or the configured log location. The debug estimate shows how many more task-count increments reach eligibility. A task must still offer a stash, and the rarity roll can fail.

## Credits

Addon by **GeroyAnekdotov**. Corpse-looting concept and original script by strelloc (strelocc on ModDB), with inspiration from Black Road Revisited. Thanks to the Anomaly, GAMMA and Anomaly MCM contributors. [Third-party notices](THIRD_PARTY_NOTICES.md)

See [release notes](RELEASE_NOTES.md), [script architecture](docs/ARCHITECTURE.md) and [development and testing](DEVELOPMENT.md).
