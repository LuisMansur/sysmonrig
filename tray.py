"""
tray.py - SysMon system tray icon
Right-click the tray icon to show/hide widgets or quit.
Runs hidden — no window, no taskbar entry.
"""
import sys, os, threading, subprocess, time
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    import subprocess as _sp
    _sp.run([sys.executable, '-m', 'pip', 'install', 'pystray', 'pillow', '-q'])
    import pystray
    from PIL import Image, ImageDraw

# ── Build tray icon image (RGB rainbow ring) ──────────────────────────────────
def make_icon():
    img  = Image.new('RGB', (64, 64), (15, 15, 35))
    draw = ImageDraw.Draw(img)
    colors = [(0,200,255),(191,95,255),(255,45,120),(255,124,0),(0,255,157)]
    seg = 360 / len(colors)
    for i, col in enumerate(colors):
        draw.arc([8,8,56,56], start=i*seg-90, end=(i+1)*seg-90, fill=col, width=10)
    draw.text((32,32), 'SM', fill=(200,230,255), anchor='mm')
    return img

# ── Launch backend + widgets as subprocesses ──────────────────────────────────
_backend = None
_widgets = None

def start_backend():
    global _backend
    _backend = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, 'app.py')],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def start_widgets():
    global _widgets
    _widgets = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, 'widgets.py')],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def stop_widgets():
    global _widgets
    if _widgets and _widgets.poll() is None:
        _widgets.terminate()
        _widgets = None

def widgets_running():
    return _widgets is not None and _widgets.poll() is None

# ── Tray menu actions ─────────────────────────────────────────────────────────
def on_settings(icon, item):
    from settings import open_settings
    open_settings()

def on_toggle(icon, item):
    if widgets_running():
        stop_widgets()
        icon.menu = make_menu(icon)
    else:
        start_widgets()
        icon.menu = make_menu(icon)

def on_quit(icon, item):
    stop_widgets()
    if _backend and _backend.poll() is None:
        _backend.terminate()
    icon.stop()

def make_menu(icon=None):
    label = 'Hide Widgets' if widgets_running() else 'Show Widgets'
    return pystray.Menu(
        pystray.MenuItem(label,        on_toggle, default=True),
        pystray.MenuItem('Settings',   on_settings),
        pystray.MenuItem('Quit',       on_quit),
    )

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Start backend first, wait for it to be ready
    start_backend()
    import urllib.request
    for _ in range(20):
        try:
            urllib.request.urlopen('http://127.0.0.1:5050/stats', timeout=1)
            break
        except: time.sleep(0.5)

    # Start widgets
    start_widgets()

    # Tray icon — this blocks until quit
    icon = pystray.Icon(
        name    = 'SysMon',
        icon    = make_icon(),
        title   = 'SysMon RIG',
        menu    = make_menu()
    )
    icon.run()
