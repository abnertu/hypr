-- Run each `just check` recipe as one telemetry suite.
-- Usage: nvim --headless --clean -l scripts/test.lua
--
-- The recipes stay the source of every check. This script only runs them,
-- so it uses plain Lua and no Neovim API.
local root = debug.getinfo(1, "S").source:sub(2):gsub("/?scripts/test%.lua$", "")
root = root == "" and "." or root

local library = root .. "/.deps/telemetry.lua/lua"
package.path = library .. "/?.lua;" .. library .. "/?/init.lua;" .. package.path

local telemetry = require("telemetry")

local recipes = {
  "fmt-check",
  "lint",
  "py-lint",
  "typecheck",
  "keymap",
  "config",
  "test",
  "helpers",
  "data",
  "profiles",
}

---@type Telemetry.Suite[]
local suites = {}
for _, recipe in ipairs(recipes) do
  suites[#suites + 1] = { name = recipe, argv = { "just", recipe }, cwd = root }
end

telemetry.exit(telemetry.run({ title = "check", suites = suites }))
