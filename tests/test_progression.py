import unittest
from pathlib import Path
from xml.etree import ElementTree

from lupa.lua51 import LuaRuntime

SCRIPTS = Path(__file__).resolve().parents[1] / "gamedata" / "scripts"
MODULE = "gamma_alternative_stash_progression"
MCM_PATH = MODULE + "/"
LEGACY_MCM_PATH = "warfare_stash_progression/"
SAVE_KEY = "warfare_stash_progression_used_corpses"

MOCKS = """
function load_module(name, source)
    local env = setmetatable({}, {__index = _G})
    setfenv(assert(loadstring(source, name)), env)()
    _G[name] = env
    return env
end
function getFS()
    return {exist = function(self, alias, filename)
        assert(alias == "$game_scripts$")
        assert(filename == "warfare_stash_progression.script")
        return legacy_file_present and {} or nil
    end}
end
settings = {}
config_saves = 0
axr_main = {config = {
    r_value = function(self, section, key, kind)
        assert(section == "mcm" and (kind == 1 or kind == 2))
        local value = settings[key]
        if kind == 2 then return tonumber(value) end
        assert(value == nil or type(value) == "boolean")
        return value
    end,
    w_value = function(self, section, key, value)
        assert(section == "mcm" and (type(value) == "boolean" or type(value) == "number"))
        settings[key] = value
    end,
    save = function(self) config_saves = config_saves + 1 end,
}}
ui_mcm = {get = function(key)
    assert(not gathering_mcm, "ui_mcm.get cannot be called during discovery")
    if settings[key] ~= nil then return settings[key] end
    local option = mcm_gui and mcm_gui.options[key]
    if option then return option.def end
end, get_gui = function() return mcm_gui end}
game = {translate_string = function(key) return key end}
function round_idp(value, precision)
    local scale = 10 ^ precision
    return math.floor(value * scale + 0.5) / scale
end
function gather_mcm(module)
    gathering_mcm = true
    local menu = module.on_mcm_load()
    gathering_mcm = false
    return menu
end
function render_mcm()
    local gui = mcm_gui
    local path = gui.path
    local preset = gui.options[path .. "/preset"]
    local combo = {
        items = {}, token = gui:GetValue(path, "preset", preset),
        ClearList = function(self) self.items = {}; self.token = 0; self.label = "" end,
        AddItem = function(self, label, index) self.items[index] = label end,
        SetText = function(self, label) self.label = label end,
        GetText = function(self) return self.label end,
    }
    gui.combo = combo
    preset.ui_hook_functor[1](nil, {ctrl = combo})
    for _, key in ipairs({"stash_chance", "yellow_chance"}) do
        local slider = gui.options[path .. "/" .. key]
        local display = {GetText = function() return tostring(gui:GetValue(path, key, slider)) end}
        slider.ui_hook_functor[1](nil, {txt = display}, slider, {path = path, opt = key})
    end
end
function open_mcm(menu)
    mcm_gui = {
        path = menu.id, options = {}, pending = {},
        GetOption = function(self, key) return self.options[key] end,
        GetValue = function(self, path, key, option)
            local full_path = path .. "/" .. key
            local value = self.pending[full_path]
            if value ~= nil then return value end
            if option.curr then return option.curr[1]() end
            value = settings[full_path]
            if value ~= nil then return value end
            return option.def
        end,
    }
    for _, option in ipairs(menu.gr) do mcm_gui.options[menu.id .. "/" .. option.id] = option end
    render_mcm()
    return mcm_gui
end
function edit_mcm(key, value)
    local gui = mcm_gui
    local full_path = gui.path .. "/" .. key
    local option = gui:GetOption(full_path)
    gui.pending[full_path] = value
    if option.on_selection_functor then
        option.on_selection_functor[1](gui.path, key, value, option)
    end
end
function select_mcm_preset(index)
    local gui = mcm_gui
    assert(gui.combo.items[index])
    if gui.combo.token == index then return end
    gui.combo.token = index
    edit_mcm("preset", index)
    local preset = gui:GetOption(gui.path .. "/preset")
    for key, value in pairs(preset.presets[index]) do edit_mcm(key, value) end
    render_mcm()
end
function apply_mcm()
    for key, value in pairs(mcm_gui.pending) do
        if not mcm_gui.options[key].curr then settings[key] = value end
    end
    mcm_gui = nil
end
callbacks = {}
callback_handlers = {}
function RegisterScriptCallback(name, handler)
    callback_handlers[name] = callback_handlers[name] or {}
    callback_handlers[name][handler] = true
    callbacks[name] = handler
end
function IsStalker(npc) return npc.stalker end
function character_community(npc)
    assert(IsStalker(npc), "only stalkers should reach the community check")
    return npc.community
end
function corpse(id, community, stalker, alive)
    return {
        id = function() return id end, community = community, stalker = stalker,
        alive = function() return alive end,
    }
end
actor = {}
db = {actor = actor}
reward = {toolkit_reward_count = 4, toolkit_reward_last = 2}
function load_var(obj, key)
    assert(obj == actor)
    return reward[key]
end
function save_var(obj, key, value)
    assert(obj == actor)
    reward[key] = value
end
roll_count = 0
function set_rolls(...)
    rolls = {...}
end
set_rolls()
function math.random(low, high)
    roll_count = roll_count + 1
    assert(#rolls > 0, "unexpected random roll")
    if low then assert(low == 1 and high == 100) end
    return table.remove(rolls, 1)
end
stash_count = 0
rare_count = 0
stash_attempts = 0
logs = {}
function printf(fmt, ...)
    table.insert(logs, string.format(fmt, ...))
end
treasure_manager = {}
function has_alife_info() return false end
gamma_alternative_stash_backend = {
    create = function(rare, observe)
        assert(math.random() > 0.75)
        stash_attempts = stash_attempts + 1
        if no_cache then return nil, "no available GAMMA cache" end
        if observe then observe(123) end
        if fail_stash then error("stash creation failed") end
        stash_count = stash_count + 1
        if rare then rare_count = rare_count + 1 end
        return 123
    end,
}
"""


class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(MOCKS)
        self.game = self.lua.globals()
        self.progression = self.load_script(MODULE)
        self.mcm = self.load_script(MODULE + "_mcm")
        self.load_script("gamma_alternative_stash_debug")
        self.progression.on_game_start()
        self.callbacks = self.game.callbacks
        self.zombie_setting = MCM_PATH + "include_zombified_stalkers"

    def load_script(self, module):
        return self.game.load_module(module, (SCRIPTS / (module + ".script")).read_text("ascii"))

    def discover_menu(self):
        return self.game.gather_mcm(self.mcm)

    def open_menu(self):
        return self.game.open_mcm(self.discover_menu())

    def assert_slider_values(self, gui, stash, yellow):
        for key, value in (("stash_chance", stash), ("yellow_chance", yellow)):
            self.assertEqual(gui.GetValue(gui, MODULE, key, gui.options[MCM_PATH + key]), value)

    def search(self, id=10, community="stalker", stalker=True, alive=False):
        self.callbacks.npc_on_use(self.game.corpse(id, community, stalker, alive))

    def test_registers_original_callbacks(self):
        self.progression.on_game_start()
        self.assertEqual(set(self.callbacks), {
            "npc_on_use", "actor_on_first_update", "server_entity_on_unregister", "save_state", "load_state",
        })
        self.assertTrue(all(len(list(handlers)) == 1 for handlers in self.game.callback_handlers.values()))

    def test_legacy_copy_owns_callbacks_in_both_startup_orders(self):
        old_start = self.lua.eval("""function()
            for _, name in ipairs({"npc_on_use", "server_entity_on_unregister", "save_state", "load_state"}) do
                RegisterScriptCallback(name, function() end)
            end
        end""")
        self.game.legacy_file_present = True
        self.game.settings[LEGACY_MCM_PATH + "enabled"] = False
        for order in ((old_start, self.progression.on_game_start), (self.progression.on_game_start, old_start)):
            self.lua.execute("callbacks = {}; callback_handlers = {}")
            for start in order:
                start()
            handlers = self.game.callback_handlers
            self.assertEqual(len(list(handlers)), 4)
            self.assertTrue(all(len(list(entries)) == 1 for entries in handlers.values()))
        self.assertIn("Disable the old MO2 mod", self.game.logs[1])
        self.assertIsNone(self.discover_menu())
        self.assertEqual(self.game.config_saves, 0)

    def test_mcm_migrates_legacy_switches_before_gameplay_lookup(self):
        self.game.settings[LEGACY_MCM_PATH + "enabled"] = False
        self.game.settings[LEGACY_MCM_PATH + "include_zombified_stalkers"] = True
        self.discover_menu()
        self.assertIs(self.game.settings[MCM_PATH + "enabled"], False)
        self.assertIs(self.game.settings[self.zombie_setting], True)
        self.search()
        self.assertEqual(self.game.roll_count, 0)
        self.game.settings[MCM_PATH + "enabled"] = True
        self.discover_menu()
        self.game.set_rolls(16, 17, 0.8)
        self.search(community="zombied")
        self.assertEqual(self.game.stash_count, 1)
        self.assertEqual(self.game.config_saves, 1)

    def test_mcm_preserves_v202_switches_and_migrates_v11_custom_rates(self):
        self.game.settings[MCM_PATH + "enabled"] = False
        self.game.settings[self.zombie_setting] = True
        self.game.settings[LEGACY_MCM_PATH + "enabled"] = True
        self.game.settings[LEGACY_MCM_PATH + "include_zombified_stalkers"] = False
        self.game.settings[LEGACY_MCM_PATH + "preset"] = 2
        self.game.settings[LEGACY_MCM_PATH + "stash_chance"] = 27
        self.game.settings[LEGACY_MCM_PATH + "yellow_chance"] = 0
        self.discover_menu()
        self.assertIs(self.game.settings[MCM_PATH + "enabled"], False)
        self.assertIs(self.game.settings[self.zombie_setting], True)
        self.assertIsNone(self.game.settings[MCM_PATH + "preset"])
        self.assertEqual(self.game.settings[MCM_PATH + "stash_chance"], 27)
        self.assertEqual(self.game.settings[MCM_PATH + "yellow_chance"], 0)
        self.assertEqual(self.game.config_saves, 1)

        self.game.settings[MCM_PATH + "stash_chance"] = 0
        self.discover_menu()
        self.assertEqual(self.game.settings[MCM_PATH + "stash_chance"], 0)
        self.assertEqual(self.game.config_saves, 1)

    def test_saved_preset_only_fills_missing_rates(self):
        self.game.settings[LEGACY_MCM_PATH + "preset"] = 2
        self.game.settings[LEGACY_MCM_PATH + "stash_chance"] = 0
        gui = self.open_menu()
        self.assert_slider_values(gui, 0, 16)
        self.assertTrue(gui.combo.label.endswith("gasp_preset_custom"))

    def test_v202_and_v203_show_custom_for_saved_very_fast_with_twenty_percent(self):
        for version, namespace in (("2.0.2", LEGACY_MCM_PATH), ("2.0.3", MCM_PATH)):
            with self.subTest(version=version):
                self.setUp()
                self.game.settings[MCM_PATH + "enabled"] = True
                self.game.settings[self.zombie_setting] = False
                self.game.settings[namespace + "preset"] = 4
                self.game.settings[namespace + "stash_chance"] = 20
                self.game.settings[namespace + "yellow_chance"] = 20
                gui = self.open_menu()
                self.assert_slider_values(gui, 20, 20)
                self.assertTrue(gui.combo.label.endswith("gasp_preset_custom"))
                self.assertEqual(len(gui.combo["items"]), 4)
                self.game.set_rolls(20, 20, 0.8)
                self.search()
                self.assertEqual(self.game.stash_count, 1)
                self.assertEqual(self.game.rare_count, 1)
                self.assertEqual(self.game.reward.toolkit_reward_last, 2)
                self.game.select_mcm_preset(4)
                self.assert_slider_values(gui, 16, 16)
                self.assertTrue(gui.combo.label.endswith("gasp_preset_very_fast"))
                self.game.apply_mcm()
                self.assert_slider_values(self.open_menu(), 16, 16)

    def test_manual_changes_apply_and_survive_reopen_and_restart(self):
        gui = self.open_menu()
        self.assert_slider_values(gui, 16, 16)
        self.assertTrue(gui.combo.label.endswith("gasp_preset_very_fast"))

        self.game.edit_mcm("stash_chance", 20)
        self.game.edit_mcm("yellow_chance", 20)
        self.assertTrue(gui.combo.label.endswith("gasp_preset_custom"))
        self.assertEqual(gui.combo.token, 0)
        self.game.set_rolls(17)
        self.search()  # Gameplay reads committed values while edits are pending.
        self.assertEqual(self.game.stash_count, 0)
        self.game.select_mcm_preset(4)
        self.assert_slider_values(gui, 16, 16)
        self.game.edit_mcm("stash_chance", 21)
        self.game.edit_mcm("yellow_chance", 37)
        self.game.apply_mcm()

        self.assert_slider_values(self.open_menu(), 21, 37)
        saved = dict(self.game.settings)
        self.setUp()
        self.game.settings = self.lua.table_from(saved)
        gui = self.open_menu()
        self.assert_slider_values(gui, 21, 37)
        self.assertTrue(gui.combo.label.endswith("gasp_preset_custom"))
        self.game.set_rolls(21, 37, 0.8)
        self.search()
        self.assertEqual(self.game.stash_count, 1)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_ordinary_stalker_eligible_with_either_setting(self):
        for id, value in enumerate((False, True)):
            with self.subTest(include_zombified=value):
                self.game.settings[self.zombie_setting] = value
                self.game.set_rolls(16, 17, 0.8)
                self.search(id)
                self.assertEqual(self.game.stash_count, id + 1)
                self.assertEqual(self.game.reward.toolkit_reward_count, 4)
                self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_zombified_stalker_excluded_with_setting_off_or_missing(self):
        for value in (None, False):
            with self.subTest(include_zombified=value):
                self.game.settings[self.zombie_setting] = value
                self.search(community="zombied")
                self.assertEqual(self.game.roll_count, 0)

    def test_opted_in_zombified_stalker_uses_same_rolls(self):
        self.game.settings[self.zombie_setting] = False
        self.search(community="zombied")
        self.game.settings[self.zombie_setting] = True
        self.game.set_rolls(17)
        self.search(community="zombied")
        self.assertEqual(self.game.stash_count, 0)
        self.game.set_rolls(16, 17, 0.8)
        self.search(id=11, community="zombied")
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)
        self.game.set_rolls(16, 16, 0.8)
        self.search(id=12, community="zombied")
        self.assertEqual(self.game.stash_count, 2)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)
        self.assertEqual(self.game.reward.toolkit_reward_count, 4)

    def test_mutants_and_living_stalkers_do_not_roll(self):
        for value in (False, True):
            with self.subTest(include_zombified=value):
                self.game.settings[self.zombie_setting] = value
                self.search(community="monster", stalker=False)
                self.search(community="zombied", stalker=False)
                self.search(alive=True)
                self.assertEqual(self.game.roll_count, 0)

    def test_disabled_blocks_both_types_with_either_setting(self):
        self.game.settings[MCM_PATH + "enabled"] = False
        for value in (False, True):
            with self.subTest(include_zombified=value):
                self.game.settings[self.zombie_setting] = value
                self.search()
                self.search(community="zombied")
                self.assertEqual(self.game.roll_count, 0)

    def test_defaults_and_activation_ignore_legacy_mode_switch(self):
        self.game.settings[LEGACY_MCM_PATH + "enable_non_warfare"] = True
        self.discover_menu()
        self.assertIsNone(self.game.settings[self.zombie_setting])
        self.assertIsNone(self.game.settings[MCM_PATH + "enable_non_warfare"])
        self.assertEqual(self.game.config_saves, 0)
        self.lua.execute("alife_storage_manager = {get_state = function() error('mode queried') end}")
        self.search(community="zombied")
        self.assertEqual(self.game.roll_count, 0)
        self.game.set_rolls(17)
        self.search()
        self.assertEqual(self.game.stash_count, 0)
        self.game.set_rolls(16, 16, 0.8)
        self.search(id=11)
        self.assertEqual(self.game.stash_count, 1)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_manual_slider_changes_control_both_rolls(self):
        self.game.settings[MCM_PATH + "stash_chance"] = 31
        self.game.settings[MCM_PATH + "yellow_chance"] = 47
        self.game.set_rolls(32)
        self.search()
        self.assertEqual(self.game.stash_count, 0)
        self.game.set_rolls(31, 48, 0.8)
        self.search(id=11)
        self.assertEqual(self.game.stash_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)
        self.game.set_rolls(31, 47, 0.8)
        self.search(id=12)
        self.assertEqual(self.game.stash_count, 2)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_slider_endpoints(self):
        self.game.settings[MCM_PATH + "stash_chance"] = 0
        self.search()
        self.assertEqual(self.game.roll_count, 0)

        self.game.settings[MCM_PATH + "stash_chance"] = 100
        self.game.settings[MCM_PATH + "yellow_chance"] = 0
        self.game.set_rolls(100, 0.8)
        self.search(id=11)
        self.assertEqual(self.game.stash_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

        self.game.settings[MCM_PATH + "yellow_chance"] = 100
        self.game.set_rolls(100, 100, 0.8)
        self.search(id=12)
        self.assertEqual(self.game.stash_count, 2)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_once_per_corpse_even_after_failed_roll_and_reload(self):
        self.game.settings[self.zombie_setting] = True
        self.game.set_rolls(17, 17)
        self.search()
        self.search(11, community="zombied")
        self.search()
        self.search(11, community="zombied")
        state = self.lua.table()
        self.callbacks.save_state(state)
        self.assertEqual(dict(state[SAVE_KEY]), {10: True, 11: True})

        self.callbacks.load_state(self.lua.table())
        self.callbacks.load_state(self.lua.table_from({
            SAVE_KEY: self.lua.table_from(dict(state[SAVE_KEY])),
        }))
        self.game.settings[self.zombie_setting] = False
        self.search()
        self.game.settings[self.zombie_setting] = True
        self.search(11, community="zombied")
        self.assertEqual(self.game.roll_count, 2)

    def test_legacy_save_and_stalker_unregister(self):
        self.callbacks.load_state(self.lua.table_from({SAVE_KEY: self.lua.table_from({10: True})}))
        entity = self.lua.table_from({"id": 10})
        self.search()
        self.callbacks.server_entity_on_unregister(entity, "se_monster")
        self.search()
        self.callbacks.server_entity_on_unregister(entity, "se_stalker")
        self.game.set_rolls(17)
        self.search()
        self.assertEqual(self.game.roll_count, 1)

    def test_progress_unchanged_after_stash_creation_error_and_no_retry(self):
        self.game.fail_stash = True
        self.game.set_rolls(16, 16, 0.8)
        self.search()
        self.search()
        self.assertEqual(self.game.reward.toolkit_reward_count, 4)
        self.assertIn("stash creation failed", self.game.logs[1])
        self.assertEqual(self.game.stash_count, 0)
        self.assertEqual(self.game.stash_attempts, 1)

    def test_missing_counter_unchanged_on_success_and_no_location(self):
        self.game.reward.toolkit_reward_count = None
        self.game.set_rolls(16, 16, 0.8)
        self.search()
        self.assertIsNone(self.game.reward.toolkit_reward_count)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

        self.game.no_cache = True
        self.game.set_rolls(16, 16, 0.8)
        self.search(id=11)
        self.assertIsNone(self.game.reward.toolkit_reward_count)
        self.assertEqual(self.game.rare_count, 1)
        self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_debug_reports_exclusion_when_disabled_without_rolling(self):
        self.game.settings[MCM_PATH + "enabled"] = False
        self.game.settings[MCM_PATH + "debug_mode"] = True
        self.callbacks.actor_on_first_update()
        self.search()
        messages = "\n".join(self.game.logs.values())
        self.assertIn("[GASP DEBUG] === INITIAL GAMMA PROGRESSION ===", messages)
        self.assertIn("eligible: NO; reason: mod disabled", messages)
        self.assertIn("First and second rolls: N/A", messages)
        self.assertEqual(self.game.roll_count, 0)

    def test_debug_distinguishes_shared_toolkit_unlock_from_task_progression(self):
        self.game.settings[MCM_PATH + "debug_mode"] = True
        self.lua.execute("""
            local unlocked = false
            local basic = "actor_find_basic_kit"
            function has_alife_info(key) return key == basic and unlocked end
            treasure_manager.caches = {}
            local create = gamma_alternative_stash_backend.create
            gamma_alternative_stash_backend.create = function(rare, observe)
                local id = create(rare, observe)
                treasure_manager.caches[id] = "itm_basickit"
                unlocked = true
                return id, nil, {[basic] = true}
            end
        """)
        self.game.set_rolls(16, 16, 0.8)
        self.search()
        messages = "\n".join(self.game.logs.values())
        self.assertIn("Generated toolkit: itm_basickit; source: CORPSE STASH", messages)
        self.assertIn("actor_find_basic_kit: false -> true", messages)
        self.assertIn("Toolkit unlocked: actor_find_basic_kit; source: CORPSE STASH", messages)
        self.assertIn("toolkit_reward_count: 4 -> 4", messages)
        self.assertIn("toolkit_reward_last: 2 -> 2", messages)
        self.assertIn("Task progression unchanged: YES", messages)
        self.assertNotIn("WARNING", messages)

    def test_mcm_layout_and_fresh_defaults(self):
        menu = self.discover_menu()
        self.assertEqual(menu.id, MODULE)
        items = list(menu.gr.values())
        self.assertEqual([(item.id, item.type) for item in items], [
            ("title", "slide"), ("progression_info", "desc"), ("enabled", "check"),
            ("include_zombified_stalkers", "check"), ("debug_mode", "check"), ("preset", "preset"),
            ("stash_chance", "track"), ("yellow_chance", "track"), ("mechanics_info", "desc"),
        ])
        self.assertEqual([item["def"] for item in items[2:-1]], [True, False, False, 4, 16, 16])
        self.assertIs(items[2]["def"], True)
        self.assertIs(items[3]["def"], False)
        self.assertIs(items[4]["def"], False)
        for slider in items[-3:-1]:
            self.assertEqual((slider.min, slider.max, slider.step, slider.val), (0, 100, 1, 2))
        self.assertEqual(self.game.config_saves, 0)

    def test_each_preset_supplies_both_slider_values(self):
        gui = self.open_menu()
        preset = gui.options[MCM_PATH + "preset"]
        options = list(preset.content.values())
        self.assertEqual([option[1] for option in options], [1, 2, 3, 4])
        for option, (stash, yellow) in zip(options, ((3, 12), (5, 16), (8, 16), (16, 16)), strict=True):
            with self.subTest(preset=option[2]):
                index = option[1]
                changes = dict(preset.presets[index])
                self.assertEqual(changes, {"stash_chance": stash, "yellow_chance": yellow})
                self.game.select_mcm_preset(index)
                self.assert_slider_values(gui, stash, yellow)
                self.assertTrue(gui.combo.label.endswith(option[2]))
                self.game.apply_mcm()
                gui = self.open_menu()
                self.assert_slider_values(gui, stash, yellow)
                self.game.set_rolls(stash, yellow, 0.8)
                self.search(id=index)
                self.assertEqual(self.game.stash_count, index)
                self.assertEqual(self.game.rare_count, index)
                self.assertEqual(self.game.reward.toolkit_reward_last, 2)

    def test_mcm_labels_and_tooltips_resolve_for_both_languages(self):
        menu = self.discover_menu()
        required = {f"ui_mcm_menu_{menu.id}"}
        for item in menu.gr.values():
            if item.type in {"check", "preset", "track"}:
                name = f"ui_mcm_{menu.id}_{item.id}"
                required.update((name, name + "_desc", name + "_hint"))
            else:
                required.add(item.text)
            if item.type == "preset":
                for option in item.content.values():
                    required.add(f"{menu.id}_preset_lst_{option[2]}")
                required.add(f"{menu.id}_preset_lst_gasp_preset_custom")
        for language in ("eng", "rus"):
            with self.subTest(language=language):
                path = SCRIPTS.parent / "configs" / "text" / language / f"st_{MODULE}.xml"
                strings = ElementTree.fromstring(path.read_text(encoding="cp1251"))
                self.assertCountEqual([item.get("id") for item in strings], required)
                text = {item.get("id"): item.findtext("text") for item in strings}
                self.assertTrue(all(value.strip() and "warfare" not in value.lower() for value in text.values()))
                prefix = f"ui_mcm_{menu.id}_"
                self.assertEqual(text[prefix + "preset"], "Chance Preset" if language == "eng" else "Пресет шансов")
                self.assertEqual(text[prefix + "stash_chance"],
                                 "Stash Chance (%)" if language == "eng" else "Шанс тайника с трупа (%)")
                intro, mechanics = (text[prefix + key] for key in ("progression_info", "mechanics_info"))
                self.assertEqual(intro.count(r"\n\n"), 1)
                self.assertEqual(mechanics.count(r"\n\n"), 2)
                self.assertNotIn("walo", intro.lower())
                self.assertIn("UNISG", intro)
                self.assertNotIn(mechanics, intro)
                self.assertEqual(text[prefix + "debug_mode"], "Debug Mode" if language == "eng" else "Режим отладки")
                for key in ("preset_desc", "stash_chance_desc", "yellow_chance_desc"):
                    self.assertIn(r"\n\n", text[prefix + key])
                default_label = "Default" if language == "eng" else "по умолчанию"
                decimal = "." if language == "eng" else ","
                self.assertIn(default_label, text[f"{menu.id}_preset_lst_gasp_preset_very_fast"])
                self.assertEqual(text[f"{menu.id}_preset_lst_gasp_preset_custom"],
                                 "Custom" if language == "eng" else "Свои настройки")
                self.assertEqual(any("А" <= c <= "я" for c in text[prefix + "progression_info"]), language == "rus")
                for key, rates in zip(("slow", "medium", "fast", "very_fast"),
                                      ("3% x 12%", "5% x 16%", "8% x 16%", "16% x 16%"), strict=True):
                    self.assertIn(rates, text[f"{menu.id}_preset_lst_gasp_preset_{key}"])
                for rate in ("0.36", "0.80", "1.28", "2.56"):
                    self.assertIn(rate.replace(".", decimal) + "%", text[prefix + "preset_desc"])


if __name__ == "__main__":
    unittest.main()
