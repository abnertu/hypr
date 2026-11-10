# Capture the desktop demo

Use Grim and Python 3 in the actual Hyprland session.
Use ImageMagick when privacy masks are required.

1. Prepare a workspace that you want to publish.
2. Close private windows and hide identifying notifications.
3. Select that workspace.
4. Keep the prepared view stable throughout capture.
5. Run the capture from the repository root.

```bash
python3 docs/assets/demo/capture.py --workspace 5 --expected-windows 0 \
  --public-view-ready --redact 258,0,480,38 --output /tmp/public-desktop.png
```

Set the expected window count to match the prepared view.
Each optional privacy mask uses `X,Y,WIDTH,HEIGHT` in captured pixels.
Masks cover only the specified rectangles with an opaque color.
The included image masks the top-bar window titles.
All other pixels preserve the actual desktop.

The command captures only the output showing the selected workspace.
It keeps the current wallpaper, Noctalia panels and window layout.
It reads no preference files, clipboard data or window titles.
Special workspaces, changed window counts and detected display changes reject the capture.
Checks before and after capture cannot detect a transient switch that switches back.

Inspect the complete PNG at native resolution.
Check visible text, notifications and personal information.
Copy only the reviewed image to `docs/assets/demo.png`.
Keep private captures outside the repository.
Never run capture automatically.
