"""Capture one deliberately prepared public workspace from the real desktop."""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def selected_output(workspace: int, expected_windows: int) -> dict[str, Any]:
    """Select the output without inspecting window titles or application data."""
    result = subprocess.run(
        ["hyprctl", "-j", "monitors"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    matches = [
        monitor
        for monitor in json.loads(result.stdout)
        if monitor.get("activeWorkspace", {}).get("id") == workspace
    ]
    if len(matches) != 1:
        raise SystemExit("Select the prepared public workspace before capturing")
    workspaces = json.loads(
        subprocess.check_output(
            ["hyprctl", "-j", "workspaces"],
            text=True,
            timeout=10,
        )
    )
    current = [item for item in workspaces if item.get("id") == workspace]
    if len(current) != 1 or current[0].get("windows") != expected_windows:
        raise SystemExit("The prepared window count changed; capture stopped")
    monitor = matches[0]
    if monitor.get("specialWorkspace", {}).get("id", 0):
        raise SystemExit("Close the special workspace before capturing")
    return {key: monitor[key] for key in ("name", "width", "height", "scale", "transform")}


def main() -> None:
    """Require readiness and discard a capture if its workspace changes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=int, required=True)
    parser.add_argument("--expected-windows", type=int, required=True)
    parser.add_argument("--public-view-ready", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--redact",
        action="append",
        default=[],
        metavar="X,Y,WIDTH,HEIGHT",
        help="cover an identifier region with an opaque privacy mask",
    )
    args = parser.parse_args()
    if args.expected_windows < 0 or args.workspace < 1 or args.output.suffix.lower() != ".png":
        parser.error("Use a positive workspace number and a PNG output path")
    before = selected_output(args.workspace, args.expected_windows)
    with tempfile.TemporaryDirectory(prefix="hypr-public-capture-") as directory:
        image = Path(directory) / "desktop.png"
        subprocess.run(["grim", "-o", before["name"], str(image)], check=True, timeout=15)
        image.chmod(0o600)
        if selected_output(args.workspace, args.expected_windows) != before:
            raise SystemExit("The prepared workspace changed; capture discarded")
        with image.open("rb") as stream:
            header = stream.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise SystemExit("The capture is not a PNG; capture discarded")
        width, height = struct.unpack(">II", header[16:24])
        for rectangle in args.redact:
            try:
                x, y, w, h = map(int, rectangle.split(","))
            except ValueError:
                parser.error("Each privacy region needs four integer coordinates")
            if min(x, y) < 0 or min(w, h) < 1 or x + w > width or y + h > height:
                parser.error("A privacy region lies outside the captured image")
            masked = image.with_name("masked.png")
            subprocess.run(
                [
                    "magick",
                    str(image),
                    "-fill",
                    "#111827",
                    "-draw",
                    f"rectangle {x},{y} {x + w - 1},{y + h - 1}",
                    "-depth",
                    "8",
                    str(masked),
                ],
                check=True,
                timeout=15,
            )
            masked.replace(image)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output.parent, prefix=".capture-") as published:
            temporary = Path(published) / "desktop.png"
            shutil.copyfile(image, temporary)
            temporary.replace(args.output)
        print(f"Captured the prepared public workspace at {width}x{height}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Capture failed; no raw diagnostics or private paths emitted", file=sys.stderr)
        raise SystemExit(1) from None
