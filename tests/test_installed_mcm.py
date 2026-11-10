"""Exercise the installed MCM Lua with stand-ins for X-Ray controls and disk."""

import os
import unittest
from pathlib import Path

from test_progression import LEGACY_MCM_PATH, MCM_PATH, MOCKS, MODULE, SCRIPTS


ENGINE = """
local function noop() end
function ini_file() return {} end
ini_file_ex = ini_file
utils_xml = {get_color = noop, is_widescreen = function() return true end}
GetARGB, AddScriptCallback, SendScriptCallback, Unregister_UI = noop, noop, noop, noop
printe = error
local log = printf
function printf(fmt, ...)
    if select("#", ...) == 0 then return log("%s", fmt) end
    return log(fmt, ...)
end
CUIScriptWnd = {}
function class(name) return function() _G[name] = {} end end
DIK_keys = setmetatable({}, {__index = function() return 0 end})
ui_events = {LIST_ITEM_SELECT = 1, BUTTON_CLICKED = 2}
level = {present = function() return true end}
function clamp(value, min, max) return math.max(min, math.min(max, value)) end
function str_explode(value, separator)
    local parts = {}
    for part in value:gmatch("[^" .. separator .. "]+") do parts[#parts + 1] = part end
    return parts
end
function empty_table(t) for key in pairs(t) do t[key] = nil end end
function is_not_empty(t) return next(t) ~= nil end
function size_table(t)
    local n = 0
    for _ in pairs(t) do n = n + 1 end
    return n
end
strformat = string.format
function has_translation(key) return key ~= "ui_mm_warning_pending" end
function game.translate_string(key)
    return key == "ui_mm_warning_pending" and "%d pending" or key
end
function vector2() return {set = noop} end

local function widget()
    return setmetatable({
        SetText = function(self, text) self.text = text end,
        GetText = function(self) return self.text end,
        SetFValue = function(self, value) self.value = value end,
        GetFValue = function(self) return self.value end,
        SetCheck = function(self, value) self.checked = value end,
        GetCheck = function(self) return self.checked end,
        TextControl = function(self) return self end,
        AdjustHeightToText = function(self) self.adjusted = true end,
        IsShown = function() return true end,
        Show = noop,
        GetWidth = function() return 100 end,
        GetHeight = function() return 20 end,
    }, {__index = function(_, key)
        if key:match("^Set") then return noop end
    end})
end

local function combo()
    local ctrl = widget()
    ctrl.items, ctrl.token, ctrl.clears = {}, 0, 0
    ctrl.AddItem = function(self, label, id) self.items[id] = label end
    ctrl.ClearList = function(self)
        self.items, self.token, self.text = {}, 0, ""
        self.clears = self.clears + 1
    end
    ctrl.CurrentID = function(self) return self.token end
    ctrl.enable_id = noop
    ctrl.click = function(self, index)
        self.text = assert(self.items[index])
        if self.token == index then return end
        self.token = index
        self.action()
    end
    return ctrl
end

function open_installed_mcm(path)
    local gui = setmetatable({
        _Cap = {}, _Check = {}, _List = {}, _Input = {}, _Track = {}, _Radio = {}, _Hint = {},
        checks = {}, registered = {}, pending = widget(), mod_search = widget(), preset = combo(),
        preset_cap = widget(),
        owner = {ShowDialog = noop, Show = noop, SetMsg = noop},
        message_box = {InitMessageBox = noop, SetText = noop, ShowDialog = function(self) self.shown = true end},
        scroll_opt = {
            Clear = function(self) self.rows = {} end,
            AddWindow = function(self, row) self.rows[#self.rows + 1] = row end,
        },
        HideDialog = noop,
        Register_Tree = noop, Init_Wrapper_Box = noop,
        Register_Cap = function(self, _, _, id)
            self._Cap[id:gsub("/", "_")] = widget()
            return 20
        end,
        Register_Slide = function() return 50 end,
        Register = function(self, ctrl, id) self.registered[id] = ctrl end,
        AddCallback = function(self, id, _, callback)
            local ctrl = self.registered[id]
            ctrl.action = callback
            local option = id:match("/([^/]+)/%d+$")
            if option == "preset" then self.combo = ctrl else self.checks[option] = ctrl end
        end,
        xml = {
            InitComboBox = combo, InitStatic = widget, InitCheck = widget, InitTrackBar = widget,
            InitTextWnd = function(_, path, parent)
                local text = widget()
                if path == "elements:desc" then parent.description = text end
                return text
            end,
        },
    }, {__index = UI_MCM})
    gui:Open_to(nil)
    gui.last_path, gui.last_curr_tree = path, ui_mcm.options[1]
    gui:Reset_opt(gui.last_curr_tree, path)
    return gui
end

function edit_installed_track(gui, key, value)
    local path = gui.last_path
    local id = path .. "/" .. key
    local track = gui._Track[id]
    track.ctrl:SetFValue(value)
    track.value = value
    gui:Callback_Track(track.txt, path, key, gui:GetOption(id), value)
end
"""


@unittest.skipUnless(os.environ.get("GASP_MO2_ROOT"), "set GASP_MO2_ROOT for the installed MCM audit")
class InstalledMCMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from research_gamma_stash_progression import active_providers

        root = Path(os.environ["GASP_MO2_ROOT"])
        profile = os.environ.get("GASP_MO2_PROFILE", "G.A.M.M.A")
        source, *_ = active_providers(root, profile, "scripts/ui_mcm.script")
        cls.source = source.read_text(encoding="latin1")

    def setUp(self):
        from lupa.luajit21 import LuaRuntime

        self.lua = LuaRuntime()
        self.lua.execute(MOCKS)
        self.lua.execute(ENGINE)
        self.game = self.lua.globals()
        self.mcm = self.game.load_module("ui_mcm", self.source)
        for name in (MODULE, MODULE + "_mcm", "gamma_alternative_stash_debug"):
            self.game.load_module(name, (SCRIPTS / f"{name}.script").read_text("ascii"))
        self.game[MODULE].on_game_start()

    def open_panel(self):
        if self.mcm.options[1] is None:
            self.mcm.options[1] = self.game[MODULE + "_mcm"].on_mcm_load()
            self.mcm.init_opt_coder()
        return self.game.open_installed_mcm(MODULE)

    def edit_pair(self, gui, stash, yellow):
        self.game.edit_installed_track(gui, "stash_chance", stash)
        self.game.edit_installed_track(gui, "yellow_chance", yellow)

    def assert_pair(self, gui, stash, yellow, label):
        for key, value in (("stash_chance", stash), ("yellow_chance", yellow)):
            track = gui._Track[MCM_PATH + key]
            self.assertEqual(track.ctrl.value, value)
            self.assertEqual(track.txt.text, value)
        self.assertTrue(gui.combo.text.endswith(f"_gasp_preset_{label}"))
        self.assertEqual(len(gui.combo["items"]), 4)
        self.assertEqual(gui.combo.clears, 1)

    def test_native_description_order_and_height_adjustment(self):
        rows = list(self.open_panel().scroll_opt.rows.values())
        self.assertEqual(len(rows), 9)
        descriptions = [(index, row.description) for index, row in enumerate(rows, 1) if row.description]
        self.assertEqual([(index, desc.text) for index, desc in descriptions], [
            (2, f"ui_mcm_{MODULE}_progression_info"),
            (9, f"ui_mcm_{MODULE}_mechanics_info"),
        ])
        self.assertTrue(all(desc.adjusted for _, desc in descriptions))

    def test_native_preset_switching_and_custom_edits(self):
        gui = self.open_panel()
        self.assert_pair(gui, 16, 16, "very_fast")
        self.assertIsNone(self.game.settings[MCM_PATH + "preset"])
        for index, stash, yellow, label in (
            (1, 3, 12, "slow"), (2, 5, 16, "medium"), (3, 8, 16, "fast"),
            (4, 16, 16, "very_fast"), (1, 3, 12, "slow"),
        ):
            self.edit_pair(gui, 100, 50)
            self.assert_pair(gui, 100, 50, "custom")
            old_control = gui.combo
            gui.combo.click(gui.combo, index)
            self.assertEqual(old_control.clears, 1)
            self.assert_pair(gui, stash, yellow, label)
            gui.combo.click(gui.combo, index)
            self.assert_pair(gui, stash, yellow, label)
        self.game.edit_installed_track(gui, "stash_chance", 0)
        self.assert_pair(gui, 0, 12, "custom")
        self.game.edit_installed_track(gui, "stash_chance", 3)
        self.assert_pair(gui, 3, 12, "slow")
        for stash, yellow in ((0, 0), (100, 100), (100, 50)):
            self.edit_pair(gui, stash, yellow)
            self.assert_pair(gui, stash, yellow, "custom")
        self.assertEqual(self.mcm.get(MCM_PATH + "stash_chance"), 16)
        self.assertEqual(self.mcm.get(MCM_PATH + "yellow_chance"), 16)

    def test_apply_cancel_reset_and_default_use_native_pending_values(self):
        for key, value in (("stash_chance", 100), ("yellow_chance", 50), ("preset", 4),
                           ("enabled", False), ("debug_mode", True)):
            self.game.settings[MCM_PATH + key] = value
        gui = self.open_panel()
        self.assert_pair(gui, 100, 50, "custom")
        gui.OnButton_Default(gui)
        self.assert_pair(gui, 16, 16, "very_fast")
        self.assertTrue(gui.checks.enabled.checked)
        self.assertFalse(gui.checks.include_zombified_stalkers.checked)
        self.assertFalse(gui.checks.debug_mode.checked)
        gui.OnButton_Reset(gui)
        self.assert_pair(gui, 100, 50, "custom")
        self.assertFalse(gui.checks.enabled.checked)
        self.assertTrue(gui.checks.debug_mode.checked)
        gui.combo.click(gui.combo, 2)
        gui.OnButton_Cancel(gui)
        self.assertTrue(gui.message_box.shown)
        gui.On_Discard(gui)
        gui = self.open_panel()
        self.assert_pair(gui, 100, 50, "custom")
        gui.combo.click(gui.combo, 1)
        for key in ("enabled", "include_zombified_stalkers", "debug_mode"):
            check = gui.checks[key]
            check.checked = not check.checked
            check.action()
        gui.OnButton_Accept(gui)
        gui = self.open_panel()
        self.assert_pair(gui, 3, 12, "slow")
        self.assertTrue(gui.checks.enabled.checked)
        self.assertTrue(gui.checks.include_zombified_stalkers.checked)
        self.assertFalse(gui.checks.debug_mode.checked)
        self.assertEqual(self.mcm.get(MCM_PATH + "preset"), 4)
        gui.OnButton_Default(gui)
        gui.OnButton_Cancel(gui)
        gui.On_Discard(gui)
        gui = self.open_panel()
        self.assert_pair(gui, 3, 12, "slow")
        gui.OnButton_Default(gui)
        gui.OnButton_Accept(gui)
        self.assert_pair(self.open_panel(), 16, 16, "very_fast")

    def test_legacy_migration_restart_save_load_and_gameplay_thresholds(self):
        self.game.settings[MCM_PATH + "stash_chance"] = 0
        self.game.settings[MCM_PATH + "enabled"] = False
        self.game.settings[LEGACY_MCM_PATH + "enabled"] = True
        self.game.settings[LEGACY_MCM_PATH + "preset"] = 1
        self.game.settings[LEGACY_MCM_PATH + "stash_chance"] = 55
        self.game.settings[LEGACY_MCM_PATH + "yellow_chance"] = 100
        gui = self.open_panel()
        self.assert_pair(gui, 0, 100, "custom")
        self.assertFalse(gui.checks.enabled.checked)
        check = gui.checks.enabled
        check.checked = True
        check.action()
        gui.combo.click(gui.combo, 3)
        gui.OnButton_Accept(gui)
        saved_settings = dict(self.game.settings)
        self.setUp()
        self.game.settings = self.lua.table_from(saved_settings)
        gui = self.open_panel()
        self.assert_pair(gui, 8, 16, "fast")
        gui.combo.click(gui.combo, 4)
        callbacks = self.game.callbacks
        callbacks.load_state(self.lua.table())
        self.game.set_rolls(9)
        callbacks.npc_on_use(self.game.corpse(1, "stalker", True, False))
        self.assertEqual(self.game.stash_count, 0)
        self.game.set_rolls(8, 17, 0.8)
        callbacks.npc_on_use(self.game.corpse(2, "stalker", True, False))
        self.assertEqual((self.game.stash_count, self.game.rare_count), (1, 0))
        self.game.set_rolls(8, 16, 0.8)
        callbacks.npc_on_use(self.game.corpse(3, "stalker", True, False))
        self.assertEqual((self.game.stash_count, self.game.rare_count), (2, 1))
        gui.OnButton_Accept(gui)
        self.assert_pair(self.open_panel(), 16, 16, "very_fast")
        self.game.set_rolls(16, 16, 0.8)
        callbacks.npc_on_use(self.game.corpse(4, "stalker", True, False))
        self.assertEqual((self.game.stash_count, self.game.rare_count), (3, 2))
