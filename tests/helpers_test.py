# pyright: standard
"""Exercise the helper CLI without connecting to a desktop session."""

import fcntl
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hypr helper ' ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "config"
        self.copy_configuration()
        self.install_native_fakes()
        self.prepare_environment()

    def copy_configuration(self):
        shutil.copytree(REPOSITORY / "lua", self.config / "lua")
        shutil.copytree(REPOSITORY / "profiles", self.config / "profiles")
        shutil.copyfile(REPOSITORY / "tests/fixtures/noctalia.lua", self.config / "noctalia.lua")

    def install_native_fakes(self):
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in (
            "hyprctl",
            "notify-send",
            "vicinae",
            "grim",
            "slurp",
            "wl-copy",
            "xdg-user-dir",
            "systemctl",
            "pkill",
            "swappy",
            "kill",
            "qs",
        ):
            (self.bin / name).symlink_to(REPOSITORY / "tests/native.py")

    def prepare_environment(self):
        (self.root / "runtime").mkdir()
        self.environment = {
            "HOME": str(self.root / "home"),
            "PATH": str(self.bin) + os.pathsep + os.defpath,
            "XDG_RUNTIME_DIR": str(self.root / "runtime"),
            "XDG_STATE_HOME": str(self.root / "state"),
            "HYPR_CONFIG_DIR": str(self.config),
            "HYPR_TEST_ROOT": str(self.root),
            "TMPDIR": str(self.root / "runtime"),
            "HYPRLAND_INSTANCE_SIGNATURE": "fixture",
        }
        self.scenario = {}

    def run_helper(self, *arguments):
        (self.root / "scenario.json").write_text(json.dumps(self.scenario))
        return subprocess.run(
            ["lua", str(self.config / "lua/bin/hypr.lua"), *arguments],
            check=False,
            cwd=self.config,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def calls(self, program):
        path = self.root / "calls.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [row["args"] for row in rows if row["program"] == program]

    def test_layout_uses_compositor_state_and_reports_the_applied_layout(self):
        self.scenario["hyprctl"] = {"stdout": '{"str":"dwindle"}'}
        result = self.run_helper("change-layout")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            any('["layout"]="master"' in " ".join(args) for args in self.calls("hyprctl"))
        )
        self.assertIn("Master", self.calls("notify-send")[-1])

    def test_generated_zoom_command_applies_lua_config_with_the_existing_scale(self):
        for operator, current, multiplier, expected in (
            ("*", 2, "2.0", 4),
            ("/", 2, "2.0", 1),
            ("/", 0.5, "2.0", 0.5),
            ("*", 2, "1.5", 3),
        ):
            with self.subTest(operator=operator, current=current, multiplier=multiplier):
                self.scenario["hyprctl"] = {
                    "operations": {
                        "getoption cursor:zoom_factor": {"stdout": json.dumps({"float": current})},
                        "keyword": {
                            "code": 1,
                            "stderr": "keyword can't work with non-legacy parsers",
                        },
                    }
                }
                (self.root / "scenario.json").write_text(json.dumps(self.scenario))
                generated = subprocess.run(
                    ["lua", "-", str(self.config), operator, multiplier],
                    input="""package.path=arg[1]..'/lua/?.lua;'..package.path
print(require('hyprconf.binding').zoom_command(arg[2], arg[3]))
""",
                    check=False,
                    env=self.environment,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self.assertEqual(generated.returncode, 0, generated.stderr)
                result = subprocess.run(
                    ["sh", "-c", generated.stdout.strip()],
                    check=False,
                    env=self.environment,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                evaluations = [args[1] for args in self.calls("hyprctl") if args[0] == "eval"]
                self.assertTrue(evaluations, "zoom never reached Lua configuration")
                value = re.search(r'\["zoom_factor"\]=([0-9.eE+-]+)', evaluations[-1])
                self.assertIsNotNone(value)
                self.assertEqual(float(value.group(1)), expected)
                self.assertEqual(self.calls("hyprctl")[-1], ["-j", "configerrors"])

    def test_cancelled_profile_selection_does_not_write_a_selection(self):
        self.scenario["vicinae"] = {"code": 1}
        result = self.run_helper("profile-selector", "animation")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "state/hypr/profiles/selected/animation").exists())
        self.assertEqual(self.calls("hyprctl"), [])

    def test_missing_profile_directory_reports_the_native_failure(self):
        shutil.rmtree(self.config / "profiles/animation")
        result = self.run_helper("profile-selector", "animation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("profiles/animation", result.stderr)
        self.assertEqual(self.calls("vicinae"), [])

    def test_native_failure_keeps_stderr_and_never_announces_applied_layout(self):
        self.scenario["hyprctl"] = {"code": 7, "stderr": "synthetic compositor failure"}
        result = self.run_helper("change-layout")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("synthetic compositor failure", result.stderr)
        self.assertFalse(any("Master" in args for args in self.calls("notify-send")))

    def test_blank_config_diagnostic_is_success_but_nonempty_errors_still_fail(self):
        for diagnostics, successful in (([""], True), (["", "synthetic config error"], False)):
            self.scenario["hyprctl"] = {
                "stdout": '{"str":"dwindle"}',
                "operations": {"configerrors": {"stdout": json.dumps(diagnostics)}},
            }
            result = self.run_helper("change-layout")
            if successful:
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("synthetic config error", result.stderr)

    def test_compositor_error_reply_is_a_failure_even_with_successful_transport(self):
        self.scenario["hyprctl"] = {
            "stdout": '{"str":"dwindle"}',
            "operations": {"eval": {"stdout": "semantic failure"}},
        }
        result = self.run_helper("change-layout")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("semantic failure", result.stderr)
        self.assertFalse(any("Master" in args for args in self.calls("notify-send")))

    def test_process_timeout_preserves_both_partial_streams_and_cleans_temporary_files(self):
        result = subprocess.run(
            ["lua", "-", str(self.config)],
            check=False,
            input="""package.path=arg[1]..'/lua/?.lua;'..package.path
local command={'sh','-c','printf partial; printf diagnostic >&2; sleep 1'}
local result=require('hyprconf.runtime.process').run(command, {timeout=0.1})
assert(not result.ok and result.timed_out)
assert(result.stdout=='partial' and result.stderr=='diagnostic')
""",
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list((self.root / "runtime").iterdir()), [])

    def test_native_exit_code_survives_lua_system_errno(self):
        result = subprocess.run(
            ["lua", "-", str(self.config)],
            check=False,
            input="""package.path=arg[1]..'/lua/?.lua;'..package.path
local execute=os.execute
os.execute=function(command)
  local ok, reason, code=execute(command)
  if not ok then return nil, 'Function not implemented', 38 end
  return ok, reason, code
end
local command={'sh','-c','printf partial; printf diagnostic >&2; exit 7'}
local result=require('hyprconf.runtime.process').run(command)
assert(not result.ok and result.code==7, tostring(result.code))
assert(result.stdout=='partial' and result.stderr=='diagnostic')
""",
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_session_failures_keep_native_diagnostics(self):
        for command, native in (("overview", "qs"), ("kill-active", "kill")):
            self.scenario = {
                native: {"code": 9, "stderr": "session command failed"},
                "hyprctl": {"stdout": '{"pid":12345}'},
            }
            result = self.run_helper(command)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session command failed", result.stderr)

    def test_notification_failure_does_not_discard_a_successful_capture(self):
        self.scenario["notify-send"] = {"code": 5, "stderr": "notification unavailable"}
        result = self.run_helper("screenshot")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.screenshots()), 1)
        self.assertIn("notification unavailable", result.stderr)

    def test_keybind_menu_only_closes_its_own_instance_hint_dialog(self):
        self.scenario["vicinae"] = {"code": 1}
        result = self.run_helper("keybinds")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.calls("pkill"), [["-f", "--", "^yad --class=hypr-key-hints-fixture( |$)"]]
        )

    def screenshots(self):
        return list((self.root / "home/Pictures/Screenshots").glob("*.png"))

    def test_failed_capture_never_publishes_or_copies_an_empty_image(self):
        self.scenario["grim"] = {"code": 1, "stdout": "", "stderr": "capture refused"}
        result = self.run_helper("screenshot", "--now")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capture refused", result.stderr)
        self.assertEqual(self.screenshots(), [])
        self.assertEqual(self.calls("wl-copy"), [])

    def test_cancelled_selection_never_runs_capture(self):
        self.scenario["slurp"] = {"code": 1}
        result = self.run_helper("screenshot", "--area")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("grim"), [])

    def test_clipboard_failure_keeps_the_saved_image_and_reports_failure(self):
        self.scenario["wl-copy"] = {"code": 1, "stderr": "clipboard refused"}
        result = self.run_helper("screenshot", "--now")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.screenshots()), 1)
        self.assertTrue(self.screenshots()[0].read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_active_window_capture_sanitizes_names_and_copies_the_image(self):
        self.scenario["hyprctl"] = {"stdout": '{"at":[-5,10],"size":[20,30],"class":"../../test"}'}
        result = self.run_helper("screenshot", "--active")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls("grim"), [["-g", "-5,10 20x30", "-"]])
        self.assertEqual(len(self.screenshots()), 1)
        self.assertEqual(len(self.calls("wl-copy")), 1)

    def test_swappy_temporary_image_is_removed_when_notification_is_dismissed(self):
        self.scenario["slurp"] = {"stdout": "0,0 20x30\n"}
        result = self.run_helper("screenshot", "--swappy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list((self.root / "home/Pictures/Screenshots").iterdir()), [])

    def test_failed_device_application_keeps_the_previous_receipt(self):
        receipt = self.root / "runtime/touchpad.status"
        receipt.write_text("true")
        self.scenario["hyprctl"] = {"operations": {"eval": {"code": 1, "stderr": "device refused"}}}
        result = self.run_helper("touchpad")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt.read_text(), "true")
        self.assertFalse(any("Disabled" in args for args in self.calls("notify-send")))

    def test_receipt_failure_restores_the_previous_device_state(self):
        self.scenario["hyprctl"] = {"operations": {"eval": {"refuse_receipt": True}}}
        result = self.run_helper("touchpad")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous device state restored", result.stderr)
        self.assertEqual((self.root / "device-state").read_text(), "true")

    def test_native_disabled_state_takes_precedence_over_a_stale_receipt(self):
        (self.root / "device-state").write_text("false")
        (self.root / "runtime/touchpad.status").write_text("true")
        result = self.run_helper("touchpad")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "runtime/touchpad.status").read_text(), "true")
        self.assertIn("Enabled", self.calls("notify-send")[-1])

    def test_profile_failure_restores_selection_before_recovery_reload(self):
        for name in ("original", "candidate"):
            (self.config / f"profiles/animation/{name}.lua").write_text(f"-- profile: {name}\n")
        selection = self.root / "state/hypr/profiles/selected/animation"
        selection.parent.mkdir(parents=True)
        selection.write_text("original\n")
        self.scenario["vicinae"] = {"stdout": "candidate"}
        self.scenario["hyprctl"] = {
            "operations": {"reload": [{"code": 1, "stderr": "reload refused"}, {}]}
        }
        result = self.run_helper("profile-selector", "animation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous state restored", result.stderr)
        self.assertEqual(selection.read_text(), "original\n")
        self.assertEqual(sum(args == ["reload"] for args in self.calls("hyprctl")), 2)

    def test_failed_profile_recovery_reports_both_failures(self):
        (self.config / "profiles/animation/candidate.lua").write_text("-- profile: candidate\n")
        self.scenario["vicinae"] = {"stdout": "candidate"}
        self.scenario["hyprctl"] = {
            "operations": {"reload": {"code": 1, "stderr": "reload refused"}}
        }
        result = self.run_helper("profile-selector", "animation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recovery failed", result.stderr)
        self.assertIn("reload refused", result.stderr)

    def test_busy_writer_cannot_change_runtime_or_state(self):
        lock = self.root / "state/hypr/.operation.lock"
        lock.parent.mkdir(parents=True)
        with lock.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            result = self.run_helper("touchpad")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("in progress", result.stderr)
        self.assertEqual(self.calls("hyprctl"), [])

    def test_game_mode_toggles_even_when_animations_are_already_disabled(self):
        self.scenario["hyprctl"] = {
            "operations": {"getoption animations:enabled": {"stdout": '{"bool":false}'}}
        }
        first = self.run_helper("game-mode")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Enabled", self.calls("notify-send")[-1])
        saved = self.root / "runtime/hypr/game-mode-fixture.json"
        self.assertIs(json.loads(saved.read_text())["animations:enabled"], False)
        second = self.run_helper("game-mode")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("Disabled", self.calls("notify-send")[-1])
        self.assertFalse(saved.exists())
        self.assertTrue(
            any('["enabled"]=false' in " ".join(args) for args in self.calls("hyprctl"))
        )

    def test_invalid_declarations_and_profile_categories_fail_before_native_actions(self):
        (self.config / "lua/config/effects.toml").write_text('[sounds]\nmute="yes"\n')
        result = self.run_helper("sound", "screenshot")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected boolean", result.stderr)
        result = self.run_helper("profile-selector", "../../outside")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid profile category", result.stderr)
        self.assertEqual(self.calls("hyprctl"), [])

    def test_portal_failure_stops_before_the_broker_and_keeps_unrelated_processes(self):
        self.scenario["systemctl"] = {"code": 1, "stderr": "backend unavailable"}
        result = self.run_helper("portal-hyprland")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("backend unavailable", result.stderr)
        self.assertEqual(
            self.calls("systemctl"), [["--user", "restart", "xdg-desktop-portal-hyprland.service"]]
        )
        self.assertEqual(self.calls("pkill"), [])


if __name__ == "__main__":
    unittest.main()
