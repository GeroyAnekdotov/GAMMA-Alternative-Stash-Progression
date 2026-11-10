"""Read-only audit against installed GAMMA Lua. Run explicitly with --help."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

from lupa.luajit21 import LuaRuntime

from test_progression import LEGACY_MCM_PATH, MCM_PATH, MOCKS, MODULE, SAVE_KEY

ROOT = Path(__file__).resolve().parents[1]
MANAGER = "scripts/treasure_manager.script"
TASK_MANAGER = "scripts/task_manager.script"
RARE_CONFIG = "configs/items/settings/grok_treasure_manager.ltx"
TASK_EFFECTS = "scripts/xr_effects.script"
NATIVE_CORPSES = "scripts/grok_stashes_on_corpses.script"
DESCRIPTIVE = "scripts/descriptive_stash_coordinates.script"
ATTACHMENTS = "scripts/rng_attachments_core.script"
LEGACY = "warfare_stash_progression"
BASELINE_TASK_SHA256 = "dc7131f946ca965503752ab356e3d4a3c801fdf0d7caa7971e917cb4611d0ebd"

# Engine services only. Reward logic, map vectors, cache allocation and the task
# callback are taken from the installed scripts at run time.
ENGINE = """
local previous_save_var = save_var
progress_writes = {}
function save_var(actor, key, value)
    if key == "toolkit_reward_count" or key == "toolkit_reward_last" then
        progress_writes[#progress_writes + 1] = key
    end
    previous_save_var(actor, key, value)
end
db.actor.give_info_portion = function(self, key)
    progress_writes[#progress_writes + 1] = key
    info[key] = true
end
db.actor.is_talking = function() return false end
db.actor.give_game_news = function() notices = notices + 1 end
xr_sound = {set_sound_play = function() end}
dynamic_news_helper = {GetPointDescription = function() return "description fixture" end}
rng_attachments_pools = {get_random_item = function() return "fixture_attachment" end}
function has_alife_info(key) return info[key] end
function is_empty(t) return next(t) == nil end
function shuffle_table(t) end
function random_key_table(t) return math.min(#t, tier_index) end
function alife_object(id)
    return {name = function() return "test_stash" end, m_game_vertex_id = id}
end
function alife()
    return {level_name = function() return map_name end, actor = function() return db.actor end}
end
function game_graph()
    return {vertex = function() return {level_id = function() return 1 end} end}
end
simulation_objects = {is_on_the_nearby_level = function() return true end}
game.translate_string = function(s) return s end
game_achievements = {has_achievement = function() return false end}
game_statistics = {increment_statistic = function() end}
news_manager = {send_treasure = function() end}
function printe(fmt, value) errors[#errors + 1] = string.format(fmt, tostring(value)) end
level = {
    map_has_object_spot = function(id, spot) return spots[id] == spot and 1 or 0 end,
    map_add_object_spot_ser = function(id, spot)
        if fail_after_reward then error("injected map-marker failure") end
        spots[id] = spot
    end,
}
task = {completed = 1, fail = 2}
local tasks = {task_info = {}}
function get_task_manager() return tasks end
xr_logic = {pick_section_from_condlist = function(actor, npc, effect)
    assert(effect == "reward_stash")
    reward_stash(actor, npc, {"true"})
end}
function complete_task(with_stash)
    tasks.task_info.test = {
        on_complete = with_stash and "reward_stash",
        give_reward = function() end,
    }
    task_callback({get_id = function() return "test" end}, task.completed)
end
function math.random(low, high)
    roll_count = roll_count + 1
    if not low then return float_roll end
    if low == 1 and high == 100 and corpse_roll then return corpse_roll end
    if high then return low end
    if low == 100 then return rare_roll end
    if low == 2 or low == 6 then return math.min(low, kit_index) end
    return 1
end
local base = {
    min_weight = 1, max_weight = 1, kind_val = {food = {chance = 101, weight = 1}},
    tier_val = {food = {}}, kind_list = {"food"}, tier_list = {1, 2, 3, 4, 5},
}
stash_rare = setmetatable({}, {__index = base})
stash_rare.kind_list = {"rare_food"}
stash_rare.kind_val = {rare_food = {chance = 101, weight = 1}}
stash_rare.tier_val = {rare_food = {}}
stash_common = base
item_list = {food = {}, rare_food = {}}
dbg_items = {}
for i = 1, 5 do
    base.tier_val.food[i] = {}
    item_list.food[i] = {"bread"}
    stash_rare.tier_val.rare_food[i] = {}
    item_list.rare_food[i] = {"rare_fixture_item"}
end
blacklisted_maps, caches_rare = {}, {}
caches, spots, info, errors = {}, {}, {}, {}
caches_count = 12
for i = 1, caches_count do caches[i] = false end
map_name = "jupiter_underground"
float_roll = 0.8
tier_index, kit_index, notices = 1, 1, 0
"""


def active_providers(root, profile, path):
    """MO2's modlist is high to low priority. Overwrite precedes enabled mods."""
    modlist = (root / "profiles" / profile / "modlist.txt").read_text(encoding="utf-8-sig")
    active = (root / "mods" / row[1:] for row in modlist.splitlines() if row.startswith("+"))
    return [candidate for origin in (root / "overwrite", *active)
            if (candidate := origin / "gamedata" / path).is_file()]


def source_function(source, name):
    match = re.search(rf"(?ms)^(?:local )?function {name}\(.*?^end[ \t]*$", source)
    if not match:
        raise ValueError(f"Function not found: {name}")
    return match[0].removeprefix("local ")


def source_table(source, name):
    match = re.search(rf"(?ms)^local {name} = \{{.*?^\}}", source)
    if not match:
        raise ValueError(f"Table not found: {name}")
    return match[0]


def addon_sources(history):
    current = {path.stem: path.read_text(encoding="ascii")
               for path in (ROOT / "gamedata/scripts").glob("gamma_alternative_stash_*.script")}
    builds = {"baseline": {}, "development": current}
    if not history:
        return builds

    archive = ROOT / "_reference/Warfare_Alternative_Stash_Progression_v1.1.zip"
    with ZipFile(archive) as package:
        legacy = next(name for name in package.namelist() if name.endswith(f"/scripts/{LEGACY}.script"))
        previous = package.read(legacy).decode("ascii")
    with ZipFile(ROOT / "dist/GAMMA_Alternative_Stash_Progression_v2.0.4_TEST_MO2.zip") as package:
        v204 = {name: package.read(f"gamedata/scripts/{name}.script").decode("ascii")
                for name in (MODULE, MODULE + "_mcm")}
    with ZipFile(ROOT / "dist/GAMMA_Alternative_Stash_Progression_v2.0.5_TEST_MO2.zip") as package:
        v205 = {Path(name).stem: package.read(name).decode("ascii")
                for name in package.namelist() if name.endswith(".script")}
    builds.update({"v1.1": {LEGACY: previous}, "v2.0.4": v204, "v2.0.5": v205})
    return builds


class Audit:
    def __init__(self, manager, task_manager, rare_config, task_effects, native_corpses, sources, wrappers, *, history):
        self.addons = addon_sources(history)
        self.native_corpses = native_corpses
        self.sources = {path.name: str(path) for path in sources}
        rare = rare_config.split("[settings_rare]", 1)[1].split("\n[", 1)[0]
        self.threshold = int(re.search(r"(?m)^completed_task_num\s*=\s*(\d+)", rare)[1])
        self.start_chance = int(re.search(r"(?m)^start_chance\s*=\s*(\d+)", rare)[1])
        self.bonus = [item.strip() for item in re.search(r"(?m)^reward_bonus\s*=\s*([^\n;]+)", rare)[1].split(",")]
        self.native = ["local stash_rare, stash_common, item_list, dbg_items = stash_rare, stash_common, item_list, dbg_items"]
        self.native += [source_table(manager, name) for name in ("map_tiers", "tools_map_tiers")]
        self.native += [source_function(manager, name) for name in (
            "box_in_same_map", "box_in_valid_map", "get_random_stash", "create_random_stash",
            "set_random_stash", "save_state", "load_state",
        )]
        self.tasks = [source_function(task_manager, "task_callback"), source_function(task_effects, "reward_stash")]
        descriptive, attachments = wrappers
        self.wrappers = {
            "descriptive_stash_coordinates.script": (
                "local ignore, was_func_called, showcase_treasure_caption = false, false, {}\n"
                + source_function(descriptive, r"news_manager\.send_treasure") + "\n"
                "local treasure_manager_set_random_stash = treasure_manager.set_random_stash\n"
                + source_function(descriptive, r"treasure_manager\.set_random_stash")
            ),
            "rng_attachments_core.script": (
                "local original_set_random_stash = treasure_manager.set_random_stash\n"
                "local attach_chance, silencer_chance, kit_chance, custom_chance = 100, 0, 0, 0\n"
                "local north_maps, reputation_mode = {}, false\n"
                "local function is_cheese_paid_stash() return false end\nlocal "
                + source_function(attachments, "patched_set_random_stash") + "\n"
                "treasure_manager.set_random_stash = patched_set_random_stash"
            ),
        }

    def session(self, build, *, yellow=0, count=None, rare_roll=1, last=1, map_name=None, wrapped=False):
        return Session(self, build, yellow, count, rare_roll, last, map_name, wrapped)


class Session:
    def __init__(self, audit, build, yellow, count, rare_roll, last, map_name, wrapped):
        self.audit, self.build = audit, build
        self.lua = LuaRuntime()
        self.lua.execute(MOCKS)
        self.lua.execute(ENGINE)
        self.game = self.lua.globals()
        game = self.game
        game.source_paths = self.lua.table_from(audit.sources)
        self.lua.execute("""
            local previous_getFS = getFS
            function getFS()
                local fs = previous_getFS()
                fs.update_path = function(self, alias, name)
                    assert(alias == "$game_scripts$")
                    return source_paths[name]
                end
                return fs
            end
            function manager_module(source)
                local env = setmetatable({caches = caches}, {__index = _G})
                setfenv(assert(loadstring(source, "@gamedata/scripts/treasure_manager.script")), env)()
                treasure_manager = env
            end
        """)
        game.manager_module("\n".join(audit.native))
        self.lua.execute("\n".join(audit.tasks))
        self.manager = game.treasure_manager
        self.manager_save, self.manager_load = self.manager.save_state, self.manager.load_state
        game.stash_rare.task_num = audit.threshold
        game.stash_rare.start_chance = audit.start_chance
        game.stash_rare.reward_bonus = self.lua.table_from(audit.bonus)
        self.manager.ini_treasure = self.lua.eval("""{r_float_ex = function(self, section, key)
            assert(section == "settings_rare")
            if key == "completed_task_num" then return stash_rare.task_num end
            if key == "start_chance" then return stash_rare.start_chance end
        end}""")
        game.reward.toolkit_reward_count = count
        game.reward.toolkit_reward_last = last
        game.rare_roll = rare_roll
        if map_name is not None:
            game.map_name = map_name
        if wrapped:
            for name, source in audit.wrappers.items():
                self.lua.execute(source, name="@" + name)
        for name, source in audit.addons[build].items():
            game.load_module(name, source)
        if build != "baseline":
            name, path = (LEGACY, LEGACY_MCM_PATH) if build == "v1.1" else (MODULE, MCM_PATH)
            game.settings[path + "stash_chance"] = 100
            game.settings[path + "yellow_chance"] = yellow
            game.alife_storage_manager = self.lua.table_from({
                "get_state": self.lua.eval("function() return {enable_warfare_mode = true} end"),
            })
            game[name].on_game_start()

    def corpse(self, id=100):
        if self.game.callbacks.npc_on_use:
            self.game.callbacks.npc_on_use(self.game.corpse(id, "stalker", True, False))

    def native_corpse(self, id=100):
        module = self.game.load_module("grok_stashes_on_corpses", self.audit.native_corpses)
        self.game.float_roll = 0.01
        module.npc_on_use(self.game.corpse(id, "stalker", True, False))
        self.game.float_roll = 0.8

    def complete_task(self, with_stash=False):
        self.game.complete_task(with_stash)

    def state(self):
        data = self.lua.table()
        if self.game.callbacks.save_state:
            self.game.callbacks.save_state(data)
        return {
            "count": self.game.reward.toolkit_reward_count,
            "last": self.game.reward.toolkit_reward_last,
            "info": sorted(self.game.info),
            "stashes": {key: self.manager.caches[key] for key in sorted(self.manager.caches) if self.manager.caches[key]},
            "markers": dict(sorted(self.game.spots.items())),
            "used": sorted(data[SAVE_KEY]) if data[SAVE_KEY] is not None else [],
            "errors": [*self.game.errors.values(), *self.game.logs.values()],
        }

    def reload(self, yellow):
        data = self.lua.table()
        self.manager_save(data)
        if self.game.callbacks.save_state:
            self.game.callbacks.save_state(data)
        other = self.audit.session(self.build, yellow=yellow, rare_roll=self.game.rare_roll)
        saved = other.lua.table()
        manager = data["treasure_manager"]
        if manager is not None:
            saved["treasure_manager"] = other.lua.table_from({
                "caches_count": manager["caches_count"],
                "caches": other.lua.table_from(dict(manager["caches"])),
            })
        if data[SAVE_KEY] is not None:
            saved[SAVE_KEY] = other.lua.table_from(dict(data[SAVE_KEY]))
        other.manager_load(saved)
        if other.game.callbacks.load_state:
            other.game.callbacks.load_state(saved)
        # Stand-ins for actor pstor, ALife info portions and serialized map spots.
        for key in ("reward", "info", "spots"):
            other.game[key] = other.lua.table_from(dict(self.game[key]))
        return other


def record(case, session, phase):
    print(json.dumps({"case": case, "build": session.build, "phase": phase, **session.state()}))


def run(audit):
    start = audit.threshold
    assert start == 7 and audit.start_chance == 50
    for build in ("baseline", "v1.1", "v2.0.4"):
        if build not in audit.addons:
            continue
        # A covers the completion order and the ordinary GAMMA baseline.
        s = audit.session(build, count=start - 1)
        record("A", s, "before")
        s.complete_task(with_stash=True)
        assert s.state()["count"] == start and s.state()["markers"] == {1: "treasure"}
        record("A", s, "after first task completion")
        s.complete_task(with_stash=True)
        assert s.state()["count"] == 1 and s.state()["markers"][2] == "treasure_searched"
        record("A", s, "after two task completions")

        for case, yellow in (("B/F", 0), ("C/G", 100)):
            s = audit.session(build, yellow=yellow, count=start)
            record(case, s, "before")
            s.corpse()
            state = s.state()
            if build == "baseline":
                assert not state["markers"] and state["count"] == start
            else:
                assert state["markers"] == {1: "treasure_searched"} and state["last"] == 2
                assert state["count"] == (0 if yellow == 0 else start)
                assert state["info"] == ["actor_find_basic_kit"]
            record(case, s, "after corpse")

            s.complete_task(with_stash=True)
            state = s.state()
            if build == "baseline":
                assert state["stashes"][1].endswith("itm_basickit") and state["count"] == 1
            elif yellow == 0:
                assert state["markers"][2] == "treasure" and state["count"] == 1
            else:
                assert state["stashes"][2].endswith("itm_advancedkit") and state["count"] == 1
            record("D", s, f"after task with prior yellow slider {yellow}")

        for yellow in (0, 100):
            s = audit.session(build, yellow=yellow, count=start)
            record("E", s, f"before, slider {yellow}")
            for id in (100, 101, 102):
                s.corpse(id)
            record("E", s, f"after three corpses, slider {yellow}")
            for _ in range(3):
                s.complete_task()
            record("E", s, f"after three more tasks, slider {yellow}")
            assert s.state()["count"] == (3 if build != "baseline" and yellow == 0 else start + 3)
            s.complete_task(with_stash=True)
            state = s.state()
            assert state["count"] == (4 if build != "baseline" and yellow == 0 else 1)
            record("E", s, f"after next task with a stash, slider {yellow}")

        s = audit.session(build, yellow=100, count=start)
        s.corpse()
        before = s.state()
        record("H", s, "before reload")
        s = s.reload(yellow=100)
        assert s.state() == before
        s.corpse()
        assert s.state() == before
        s.complete_task(with_stash=True)
        state = s.state()
        next_id, expected_kit = (1, "itm_basickit") if build == "baseline" else (2, "itm_advancedkit")
        assert state["count"] == 1 and state["stashes"][next_id].endswith(expected_kit)
        record("H", s, "after reload, repeat search and task stash")

        if build == "baseline":
            continue
        for count, rare_roll in ((start - 1, 1), (start, 100)):
            s = audit.session(build, yellow=0, count=count, rare_roll=rare_roll)
            record("below threshold or rare miss", s, "before")
            s.corpse()
            assert s.state()["markers"] == {1: "treasure"} and s.state()["count"] == count
            record("below threshold or rare miss", s, "after")
        for yellow in (0, 100):
            for outcome in ("no free cache", "empty loot", "late exception"):
                s = audit.session(build, yellow=yellow, count=start)
                record(outcome, s, f"before, slider {yellow}")
                if outcome == "no free cache":
                    s.manager.caches = s.lua.table()
                elif outcome == "empty loot":
                    for config in (s.game.stash_rare, s.game.stash_common):
                        config.min_weight = config.max_weight = 0
                else:
                    s.game.fail_after_reward = True
                s.corpse()
                state = s.state()
                assert not state["markers"] and state["used"] == [100]
                assert state["last"] == (1 if outcome == "no free cache" else 2)
                assert state["count"] == (start if yellow == 100 or outcome == "no free cache" else 0)
                assert bool(state["info"]) == (outcome == "late exception")
                assert bool(state["errors"]) == (outcome != "empty loot")
                record(outcome, s, f"after, slider {yellow}")
        s = audit.session(build, yellow=100, count=None)
        record("unset counter", s, "before")
        s.corpse()
        assert s.state()["count"] == (0 if build == "v1.1" else None)
        record("unset counter", s, "after")

    for build in ("baseline", "v1.1", "v2.0.4", "development"):
        if build not in audit.addons:
            continue
        s = audit.session(build, count=start)
        record("native corpse listener", s, "before")
        s.native_corpse()
        s.corpse()
        state = s.state()
        assert state["count"] == 0 and state["markers"][1] == "treasure_searched"
        assert len(state["markers"]) == (1 if build == "baseline" else 2)
        record("native corpse listener", s, "after one search")

    for marker in ("treasure", "treasure_searched"):
        s = audit.session("baseline", count=start)
        record("explicit marker API", s, "before " + marker)
        id, *_ = s.manager.get_random_stash()
        assert s.manager.set_random_stash(marker, None, None, id) == id
        state = s.state()
        assert state["count"] == start and state["last"] == 1 and not state["info"]
        assert state["markers"] == {id: marker}
        assert all("itm_" not in loot for loot in state["stashes"].values())
        record("explicit marker API", s, "after " + marker)


def progression(session):
    state = session.state()
    return state["count"], state["last"], state["info"]


def run_corpse_backend(audit, build):
    shared = build == "development"
    basic, advanced, expert = ("actor_find_basic_kit", "actor_find_advanced_kit", "actor_find_expert_kit")
    count = audit.threshold
    baseline = audit.session("baseline", count=count)
    baseline.complete_task(with_stash=True)
    expected_task = baseline.state()["stashes"][1]
    expected_state = progression(baseline)
    for yellow in (0, 100):
        s = audit.session(build, count=count, yellow=yellow)
        before = progression(s)
        record("isolated addon and next task", s, "before")
        s.corpse()
        state = s.state()
        new_flags = [basic] if shared and yellow else []
        assert not state["errors"] and list(s.game.progress_writes.values()) == new_flags
        assert progression(s) == (*before[:2], new_flags)
        assert state["markers"] == {1: "treasure_searched" if yellow else "treasure"}
        if yellow:
            assert state["stashes"][1] == "rare_fixture_item,itm_basickit"
        else:
            control = audit.session("baseline", count=count - 1)
            control.complete_task(with_stash=True)
            assert state["stashes"][1] == control.state()["stashes"][1]
        record("isolated addon and next task", s, "after corpse")
        restored = s.reload(yellow)
        restored.corpse()
        assert restored.state() == s.state()
        restored.complete_task(with_stash=True)
        if new_flags:
            assert restored.state()["stashes"][2] == "rare_fixture_item,itm_advancedkit"
            assert progression(restored) == (*expected_state[:2], sorted((basic, advanced)))
        else:
            assert restored.state()["stashes"][2] == expected_task and progression(restored) == expected_state
        record("isolated addon and next task", restored, "after reload and next task")

    for map_name, tier, kit, flags, expected, unlock in (
        ("l01_escape", 1, 1, (), "itm_ammokit", None),
        ("l01_escape", 1, 2, (), "itm_drugkit", None),
        ("l01_escape", 2, 4, (), "itm_basickit", basic),
        ("jupiter_underground", 5, 1, (), "itm_basickit", basic),
        ("jupiter_underground", 5, 1, (basic,), "itm_advancedkit", advanced),
        ("jupiter_underground", 5, 1, (basic, advanced), "itm_expertkit", expert),
        ("jupiter_underground", 5, 1, (basic, advanced, expert), "itm_expertkit", expert),
    ):
        s = audit.session(build, count=count, yellow=100, map_name=map_name)
        native = audit.session("baseline", count=count, map_name=map_name)
        for session in (s, native):
            session.game.tier_index, session.game.kit_index = tier, kit
            for flag in flags:
                session.game.info[flag] = True
        before = progression(s)
        s.corpse()
        native.complete_task(with_stash=True)
        assert s.state()["stashes"][1].endswith(expected), (map_name, tier, kit, flags, s.state())
        assert s.state()["stashes"] == native.state()["stashes"]
        new_flags = [unlock] if shared and unlock and unlock not in flags else []
        assert progression(s) == (*before[:2], sorted([*flags, *new_flags]))
        assert list(s.game.progress_writes.values()) == new_flags
        record("native toolkit distribution", s, f"{map_name}, tier-vector index {tier}, {flags}")

    for yellow in (0, 100):
        for outcome in ("missed roll", "no cache", "empty loot", "late exception", "unknown wrapper", "unknown source"):
            s = audit.session(build, count=count, yellow=yellow, wrapped=outcome == "late exception")
            if outcome == "missed roll":
                s.game.settings[MCM_PATH + "stash_chance"] = 16
                s.game.corpse_roll = 17
            elif outcome == "no cache":
                s.manager.caches = s.lua.table()
            elif outcome == "empty loot":
                for config in (s.game.stash_rare, s.game.stash_common):
                    config.min_weight = config.max_weight = 0
            elif outcome == "late exception":
                s.game.fail_after_reward = True
            elif outcome == "unknown wrapper":
                s.lua.execute("treasure_manager.set_random_stash = function() error('unexpected dispatch') end")
            else:
                s.game.source_paths["treasure_manager.script"] = audit.sources["rng_attachments_core.script"]
            before = progression(s)
            s.corpse()
            assert progression(s) == before and not list(s.game.progress_writes)
            assert not s.state()["markers"] and not s.state()["stashes"]
            assert bool(s.state()["errors"]) == (outcome != "missed roll")
            after = s.state()
            s.corpse()
            assert s.state() == after
            record("isolated failure", s, f"{outcome}, slider {yellow}")
            if outcome == "late exception":
                # The actual Descriptive wrapper must no longer suppress
                # notifications, and the next task must use its original delegate.
                s.game.news_manager.send_treasure(0)
                assert s.game.notices == 1
                s.game.fail_after_reward = False
                s.complete_task(with_stash=True)
                assert progression(s) == expected_state

    for yellow in (0, 100):
        results = []
        for debug in (False, True):
            s = audit.session(build, count=count, yellow=yellow, wrapped=True)
            s.game.settings[MCM_PATH + "debug_mode"] = debug
            s.game.callbacks.actor_on_first_update()
            s.corpse()
            state = s.state()
            log = "\n".join(state.pop("errors"))
            assert "fixture_attachment" in state["stashes"][1] and s.game.notices == 1
            assert progression(s) == (count, 1, [basic] if shared and yellow else [])
            if debug:
                assert "Task progression unchanged: YES" in log and "native gate chance: 49%" in log
                assert "Cache creation: CONFIRMED" in log and "marker creation: YES" in log
                assert "First roll: 1 / 100" in log
                assert "WARNING" not in log
                if shared and yellow:
                    assert "Generated toolkit: itm_basickit; source: CORPSE STASH" in log
                    assert f"Toolkit unlocked: {basic}; source: CORPSE STASH" in log
            else:
                assert not log
            results.append((state, s.game.roll_count))
        assert results[0] == results[1]
        record("installed wrappers and debug parity", s, f"slider {yellow}")

    s = audit.session(build, count=count, yellow=100)
    s.game.settings[MCM_PATH + "debug_mode"] = True
    s.lua.execute("news_manager.send_treasure = function() error('injected notification failure') end")
    s.corpse()
    state = s.state()
    assert state["markers"] == {1: "treasure_searched"} and not state["stashes"]
    log = "\n".join(state["errors"])
    assert "marker creation: YES" in log and "Cache creation: UNCONFIRMED" in log
    assert progression(s) == (count, 1, []) and not list(s.game.progress_writes)

    s = audit.session(build, count=count, yellow=100)
    s.lua.execute("""
        local concat = table.concat
        table.concat = function(items, separator, ...)
            if separator == "," and items[#items] == "itm_basickit" then
                return "rare_fixture_item,itm_basickit_suffix"
            end
            return concat(items, separator, ...)
        end
    """)
    s.corpse()
    assert s.state()["stashes"][1] == "rare_fixture_item,itm_basickit_suffix"
    assert progression(s) == (count, 1, []) and not list(s.game.progress_writes)

    s = audit.session(build, count=count, yellow=100)
    s.game.settings[MCM_PATH + "debug_mode"] = True
    s.lua.execute('news_manager.send_treasure = function() save_var(db.actor, "toolkit_reward_count", 13) end')
    s.corpse()
    log = "\n".join(s.state()["errors"])
    assert f"WARNING: protected state changed: toolkit_reward_count ({count} -> 13)" in log
    assert "Task progression unchanged: NO" in log


def run_shared_chain(audit):
    basic, advanced, expert = ("actor_find_basic_kit", "actor_find_advanced_kit", "actor_find_expert_kit")
    s = audit.session("development", count=audit.threshold, yellow=100)
    s.complete_task(with_stash=True)
    assert s.state()["stashes"][1].endswith("itm_basickit")
    count, last, flags = progression(s)
    assert flags == [basic]

    s.game.progress_writes = s.lua.table()
    s.corpse()
    assert s.state()["stashes"][2].endswith("itm_advancedkit")
    assert progression(s) == (count, last, sorted((basic, advanced)))
    s.corpse(101)
    assert s.state()["stashes"][3].endswith("itm_advancedkit")
    assert progression(s) == (count, last, sorted((basic, advanced)))
    assert list(s.game.progress_writes.values()) == [advanced]
    record("native Basic, corpse Advanced", s, "after repeated rare stashes")

    s = s.reload(100)
    assert progression(s) == (count, last, sorted((basic, advanced)))
    before = s.state()
    s.corpse()
    assert s.state() == before
    s.corpse(102)
    assert s.state()["stashes"][4].endswith("itm_advancedkit")
    assert progression(s) == (count, last, sorted((basic, advanced)))
    assert not list(s.game.progress_writes)
    s.game.tier_index = 5
    for _ in range(audit.threshold - count):
        s.complete_task()
    s.complete_task(with_stash=True)
    assert s.state()["stashes"][5].endswith("itm_expertkit")
    assert progression(s)[2] == sorted((basic, advanced, expert))
    record("native Basic, corpse Advanced, native Expert", s, "after reload and next eligible task")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mo2", type=Path, required=True)
    parser.add_argument("--profile", default="G.A.M.M.A")
    parser.add_argument("--task-script", type=Path, required=True, help="Installed task_manager.script or verified byte copy")
    parser.add_argument("--current-only", action="store_true", help="Run current and native cases without historical ZIPs")
    args = parser.parse_args()
    manager, *other_managers = active_providers(args.mo2, args.profile, MANAGER)
    config, *other_configs = active_providers(args.mo2, args.profile, RARE_CONFIG)
    effects, *_ = active_providers(args.mo2, args.profile, TASK_EFFECTS)
    corpses, *_ = active_providers(args.mo2, args.profile, NATIVE_CORPSES)
    descriptive, *_ = active_providers(args.mo2, args.profile, DESCRIPTIVE)
    attachments, *_ = active_providers(args.mo2, args.profile, ATTACHMENTS)
    if active_providers(args.mo2, args.profile, TASK_MANAGER):
        raise ValueError("A loose task manager overrides the baseline used by this audit")
    if hashlib.sha256(args.task_script.read_bytes()).hexdigest() != BASELINE_TASK_SHA256:
        raise ValueError("Task script differs from the Anomaly archive verified for this audit")
    print(json.dumps({
        "profile": args.profile, "manager": str(manager), "settings": str(config),
        "task_effects": str(effects), "native_corpses": str(corpses),
        "other_managers": list(map(str, other_managers)), "other_configs": list(map(str, other_configs)),
    }))
    audit = Audit(*(path.read_text(encoding="latin1") for path in (
        manager, args.task_script, config, effects, corpses,
    )), sources=(manager, descriptive, attachments),
        wrappers=tuple(path.read_text(encoding="latin1") for path in (descriptive, attachments)),
        history=not args.current_only)
    run(audit)
    if "v2.0.5" in audit.addons:
        run_corpse_backend(audit, "v2.0.5")
    run_corpse_backend(audit, "development")
    run_shared_chain(audit)
    print("All audit assertions passed.")


if __name__ == "__main__":
    main()
