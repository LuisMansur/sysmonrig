# SysMon RIG

Floating transparent system monitor widgets for a secondary panel display.
Optimized for 1920×480 landscape or 480×1920 portrait panel displays.
Ring gauges float directly over your Wallpaper Engine wallpaper with no background box.
Runs silently from the system tray with zero console windows.

## Features

- **CPU** — usage ring, temperature ring, frequency, cores / threads
- **GPU** — load ring, temperature ring, VRAM usage, fan speed, power draw (NVIDIA)
- **RAM** — usage ring, used / free GB
- **Network** — upload / download rings with session peak tracking
- Fully transparent — wallpaper shows through between and behind gauges
- Always-on-top, draggable — positions saved automatically between sessions
- Corner resize handle appears on hover — drag to resize any widget
- System tray icon — show / hide widgets or quit
- Auto-detects landscape and portrait panel monitors
- Auto-starts on boot (optional)

## Requirements

- Windows 10 / 11
- Python 3.10+
- NVIDIA GPU (GPU stats via `pynvml` / `nvidia-smi`)

## Install

```bash
pip install flask flask-cors psutil pynvml wmi pystray pillow
```

## Run

Double-click `Launch.bat` — accepts a UAC admin prompt (needed for CPU temperature).
A small rainbow **SM** tray icon appears in the system tray (bottom-right hidden icons).

**Tray icon controls:**
- **Left-click / Show Widgets** — show the widgets on screen
- **Hide Widgets** — hide widgets without stopping the backend
- **Quit** — stop everything

## Auto-start on Boot

1. Press `Win+R` → type `shell:startup` → Enter
2. Create a shortcut to `SysMon_Start.vbs` in that folder

The VBS script launches everything silently with admin rights on every boot.

## Widget Controls

| Action | Result |
|--------|--------|
| Drag anywhere on widget | Move widget — position saved automatically |
| Hover bottom-right corner | Resize handle appears |
| Drag bottom-right corner | Resize widget — size saved automatically |
| Right-click widget | Close that widget |

## CPU Temperature Note

Windows blocks CPU temperature access without a kernel driver.
`Launch.bat` auto-elevates to administrator which gives access to the built-in
`MSAcpi_ThermalZoneTemperature` WMI sensor — no third-party tools needed.

If temps still show N/A, install and run
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
as administrator — `app.py` will detect it automatically.

## Monitor Detection

The panel monitor is auto-detected as any display where width ≥ 2.5× height (landscape)
or height ≥ 2.5× width (portrait). If detection fails, run `widgets.py` directly from a
terminal — it prints the list of detected monitors and which one it chose.

Widgets are saved per-position so if you drag them to the right screen they will
remember that location on the next launch.

## Color Customization

Colors are stored in `settings.json` and can be edited manually:

```json
{
  "theme": {
    "blue":   "#00c8ff",
    "pink":   "#ff2d78",
    "green":  "#00ff9d",
    "purple": "#bf5fff",
    "orange": "#ff7c00",
    "red":    "#ff3c3c",
    "dim":    "#507090",
    "text":   "#c8e6ff"
  },
  "widgets": {
    "cpu": { "accent": null },
    "gpu": { "accent": null },
    "ram": { "accent": null },
    "net": { "accent": null }
  }
}
```

Set a widget `"accent"` to a hex color (e.g. `"#ff00ff"`) to override its ring color
independently of the global theme. Set to `null` to use the theme default.
Changes apply within 1–2 seconds without restarting.

## File Overview

| File | Purpose |
|------|---------|
| `app.py` | Flask backend — reads CPU / GPU / RAM / network stats |
| `widgets.py` | Transparent floating widgets (pure Win32 + Pillow) |
| `tray.py` | System tray icon — launches and controls backend + widgets |
| `Launch.bat` | One-click launcher with automatic UAC elevation |
| `SysMon_Start.vbs` | Silent boot auto-start script |
| `requirements.txt` | Python dependencies |
| `positions.json` | Auto-generated — stores widget positions (gitignored) |
| `settings.json` | Auto-generated — stores colors and widget sizes (gitignored) |
