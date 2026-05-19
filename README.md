# SysMon RIG

Floating transparent system monitor widgets for a secondary panel display (optimized for 1920×480).
Ring gauges float directly over your Wallpaper Engine wallpaper with no background box.
Runs silently from the system tray with zero console windows.

## Features

- **CPU** — usage ring, temperature ring, frequency, cores/threads
- **GPU** — load ring, temperature ring, VRAM usage, fan speed, power draw (NVIDIA)
- **RAM** — usage ring, used/free GB
- **Network** — upload/download rings with session peak tracking
- Fully transparent — wallpaper shows through between and behind gauges
- Always-on-top, draggable — positions saved automatically between sessions
- System tray icon — show/hide widgets or quit without opening any window
- Auto-starts on boot (optional, via `SysMon_Start.vbs`)

## Requirements

- Windows 10/11
- Python 3.10+
- NVIDIA GPU (GPU stats via `pynvml` / `nvidia-smi`)

## Install

```bash
pip install flask flask-cors psutil pynvml wmi pystray pillow
```

## Run

Double-click `Launch.bat` — it will prompt for administrator access (UAC) which is needed for CPU temperature reading. A small rainbow tray icon appears in the system tray.

**Tray icon controls:**
- **Left-click / Show Widgets** — show the widgets on screen
- **Hide Widgets** — hide widgets without stopping the backend
- **Quit** — stop everything

## Auto-start on Boot

1. Press `Win+R` → type `shell:startup` → Enter
2. Create a shortcut to `SysMon_Start.vbs` in that folder

The VBS script launches everything silently with admin rights on every boot.

## CPU Temperature Note

Windows blocks CPU temperature access without a kernel driver.
`Launch.bat` auto-elevates to administrator which enables the built-in
`MSAcpi_ThermalZoneTemperature` WMI sensor — no third-party tools needed.

If temps still show N/A, install and run
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
as administrator — `app.py` will pick it up automatically.

## File Overview

| File | Purpose |
|------|---------|
| `app.py` | Flask backend — reads CPU/GPU/RAM/network stats |
| `widgets.py` | Transparent floating widgets (pure Win32 + Pillow) |
| `tray.py` | System tray icon — launches and controls backend + widgets |
| `Launch.bat` | One-click launcher with automatic UAC elevation |
| `SysMon_Start.vbs` | Silent boot auto-start script |
| `requirements.txt` | Python dependencies |

## Customization

- **Colors** — edit `BLUE`, `PINK`, `GREEN`, `ORANGE`, `PURPLE` at the top of `widgets.py`
- **Widget positions** — drag any widget to reposition, saved automatically to `positions.json`
- **Refresh rate** — change `time.sleep(1.2)` in `app.py` and `_root.after(1200, ...)` in `widgets.py`
- **Monitor detection** — the panel monitor is auto-detected as any display where width ≥ 2.5× height. If detection fails, check the printed output in the console when running `widgets.py` directly.
