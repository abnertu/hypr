# Hyprland Lua configuration

Hyprland configuration with Vicinae menus, Noctalia colors, selectable profiles and checked desktop helpers.

[![Validate Desktop Configuration](https://github.com/abnertu/hypr/actions/workflows/validate-desktop-configuration.yml/badge.svg?branch=main)](https://github.com/abnertu/hypr/actions/workflows/validate-desktop-configuration.yml) [![Hyprland](https://img.shields.io/badge/Hyprland-0.55%2B-58E1FF?logo=hyprland&logoColor=white)](https://hypr.land/)

## Install

Use Hyprland 0.55+ on Arch Linux. Install these helper dependencies separately:

- Lua.
- Vicinae, Noctalia and Quickshell.
- YAD, Ghostty and Thunar.
- grim, slurp, swappy and wl-clipboard.
- libnotify and xdg-user-dirs.
- pw-play or paplay.

Place this repo at `~/.config/hypr`, or link that path to a checkout.

## Usage

Hyprland loads `hyprland.lua`. Use these bindings to open the main tools:

| Binding | Action |
| --- | --- |
| `SUPER + /` | Open the cheat sheet |
| `SUPER + SHIFT + /` | Search bindings |
| `SUPER + SHIFT + E` | Open quick settings |

Run a helper from a shell:

```sh
lua ~/.config/hypr/lua/bin/hypr.lua key-hints
```

Run the helper without arguments to list its commands.

- `screenshot` saves a PNG in the `Screenshots` subdirectory of the XDG Pictures directory. It also copies the image to the clipboard. A clipboard failure keeps the saved image.
- `portal-hyprland` restarts the backend and broker through systemd user units.

Helpers report native failures with a nonzero status. Interactive menus, notification choices and image editing can wait for user input. Other native commands have a finite timeout. Mutating helpers share a nonblocking lock. Retry a busy operation after its writer finishes.

## Configuration

| Change | Source |
| --- | --- |
| Applications, paths, search URL and touchpad device | `lua/hyprconf/context.lua` |
| Bindings and window rules | `lua/hyprconf/binds.lua`, `lua/hyprconf/rules.lua` |
| Input, layout and appearance | `lua/hyprconf/options.lua` |
| Menus, effects and defaults | `lua/config/*.toml` |
| Animation and monitor presets | `profiles/<category>/*.lua` |

Quick settings edits need a writable checkout. Noctalia generates `noctalia.lua` through its theme templates.

Use a writable checkout as the configuration root for live development. For managed deployments, set that root through your deployment tool.

Automatic reload can read an intermediate multi-file checkout. Before you update a live checkout:

1. Record the current boolean with `hyprctl -j getoption misc:disable_autoreload`.
2. Run `hyprctl eval 'hl.config({ misc = { disable_autoreload = true } })'`.
3. Require an `ok` reply before you apply the complete update.
4. Run `hyprctl reload`.
5. Run `hyprctl -j configerrors` and check for nonblank entries.
6. Restore the recorded value with `hyprctl eval 'hl.config({ misc = { disable_autoreload = <value> } })'`.

Use a Lua boolean literal, `true` or `false`, for `<value>`. Convert an `int` reply of 0 or 1 to `false` or `true`. An empty or blank diagnostic entry means no configuration error. Require an `ok` reply when you restore the setting.

## Ownership

Give each application one startup owner. Remove its previous startup declaration before you assign a new owner.

| Task | Owner |
| --- | --- |
| Session applications | Your session manager or user services |
| Compositor startup work | `lua/config/autostart.toml` |
| Generated theme colors | Noctalia templates |
| Profile selections and effect choices | Helpers under the runtime state root |

## State and recovery

Runtime choices live in `$XDG_STATE_HOME/hypr`, or `~/.local/state/hypr` by default:

- `profiles/selected/<category>` records a profile name.
- `effects/rainbow-border-mode` records the border mode.

Remove a selection to restore its TOML default. `HYPR_CONFIG_DIR` and `HYPR_STATE_DIR` override the configuration and state roots.

A profile change verifies its reload before acceptance. A failure restores the previous selection and reloads the configuration. A recovery failure reports both errors.

Touchpad state lasts for the session in `$XDG_RUNTIME_DIR/touchpad.status`. A change saves the state after the compositor acknowledges it. Versions without native device-state reporting use the last acknowledged receipt.

Game mode captures compositor values under `$XDG_RUNTIME_DIR/hypr/`. Disabling it restores those values, including originally disabled animations.
