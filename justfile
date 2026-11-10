set shell := ["bash", "-euo", "pipefail", "-c"]

lua := env("LUA", "lua")
ruff := env("RUFF", "ruff")

# Format Lua, then run every validation check.
all: fmt check

# Run the same checks as CI without changing formatting.
check: fmt-check lint py-lint typecheck keymap config test helpers data profiles

# Rewrite Lua and Python formatting.
fmt: (_lua-check "stylua")
    {{ quote(ruff) }} format tests

# Check Lua formatting.
fmt-check: (_lua-check "stylua" "--check")

# Check Lua style and undefined names.
lint: (_lua-check "luacheck")

# Check Python test style, complexity and formatting.
py-lint:
    {{ quote(ruff) }} check tests
    {{ quote(ruff) }} format --check tests

# Check annotations against Hyprland's installed stubs.
typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    luals="${LUALS:-}"
    if [[ -z "$luals" ]]; then
        luals=$(command -v lua-language-server || true)
        luals="${luals:-$HOME/.local/share/nvim/mason/bin/lua-language-server}"
    fi
    log=$(mktemp -d)
    trap 'rm -rf "$log"' EXIT
    "$luals" --check=. --checklevel=Warning --logpath="$log" >"$log/out" 2>&1 || {
        status=$?
        cat "$log/out"
        exit "$status"
    }

# Check frozen bindings and compositor callbacks.
keymap:
    #!/usr/bin/env bash
    set -euo pipefail
    {{ quote(lua) }} tests/keymap_callbacks.lua
    {{ quote(lua) }} tests/hotplug.lua
    actual=$(mktemp)
    trap 'rm -f "$actual"' EXIT
    {{ quote(lua) }} tests/keymap.lua >"$actual"
    diff -u tests/keymap.snapshot "$actual"

# Reject process execution while loading the configuration.
config:
    #!/usr/bin/env bash
    set -euo pipefail
    state=$(mktemp -d)
    trap 'rm -rf "$state"' EXIT
    {{ quote(lua) }} tests/config.lua "$state"

# Parse this checkout without a live compositor session.
test:
    #!/usr/bin/env bash
    set -euo pipefail
    fixture_home=$(mktemp -d)
    runtime=$(mktemp -d)
    trap 'rm -rf "$fixture_home" "$runtime"' EXIT
    env -i HOME="$fixture_home" PATH="$PATH" XDG_RUNTIME_DIR="$runtime" \
        hyprland --verify-config --config "{{ justfile_directory() }}/hyprland.lua"

# Exercise helpers with isolated state and fake native commands.
helpers:
    python3 tests/helpers_test.py

# Reject malformed JSON, TOML and helper declarations.
data:
    {{ quote(lua) }} tests/data.lua

# Parse every shipped profile with native Hyprland.
profiles:
    python3 tests/profiles_test.py

[positional-arguments]
[private]
_lua-check command *args:
    #!/usr/bin/env bash
    set -euo pipefail
    files=$(mktemp)
    trap 'rm -f "$files"' EXIT
    git ls-files -z --cached --others --exclude-standard -- '*.lua' ':!:noctalia.lua' >"$files"
    sources=()
    while IFS= read -r -d '' source; do
        if [[ -f "$source" ]]; then sources+=("$source"); fi
    done <"$files"
    [[ ${#sources[@]} -gt 0 ]]
    "$@" "${sources[@]}"
