# SysMon RIG

Floating system monitor widgets for a secondary panel display (optimized for 1920×480).
Transparent, always-on-top, draggable. Runs silently from the system tray.

## Features

- CPU usage, frequency, temperature
- GPU usage, temperature, fan speed, power draw (NVIDIA)
- RAM usage
- Network upload / download
- Transparent floating widgets — wallpaper shows through
- Draggable — positions saved between sessions
- System tray icon — show/hide/quit
- Auto-starts on boot (optional)

## Requirements

- Windows 10/11
- Python 3.10+
- NVIDIA GPU (for GPU stats via `pynvml` / `nvidia-smi`)

## Install

```bash
pip install flask flask-cors psutil pynvml wmi pystray pillow
```

## Run

Double-click `Launch.bat` — accepts the UAC admin prompt (needed for CPU temps).

A tray icon appears in the system tray. Right-click to show/hide widgets or quit.

## Auto-start on Boot

1. Press `Win+R` → type `shell:startup` → Enter
2. Create a shortcut to `SysMon_Start.vbs` in that folder

## CPU Temperature Note

CPU temps require administrator privileges to access Windows thermal sensors.
`Launch.bat` handles this automatically via UAC elevation.

## File Overview

| File | Purpose |
|------|---------|
| `app.py` | Flask backend — reads CPU/GPU/RAM stats |
| `widgets.py` | Floating transparent widgets (Win32 + Pillow) |
| `tray.py` | System tray icon — manages backend + widgets |
| `Launch.bat` | One-click launcher with auto UAC elevation |
| `SysMon_Start.vbs` | Silent startup script for boot auto-launch |
| `requirements.txt` | Python dependencies |

## Customization

- **GPU boost clock**: in `widgets.py`, find `GPU_MAX_CLK = 2800` inside `GpuWidget` and change `2800` to your GPU's actual boost clock in MHz (check GPU-Z or run `nvidia-smi --query-gpu=clocks.max.graphics --format=csv,noheader`)
- **Widget positions**: drag widgets to reposition — saved automatically to `positions.json`
- **Colors**: edit the palette constants (`BLUE`, `PINK`, `GREEN`, etc.) near the top of `widgets.py`
