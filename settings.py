"""
settings.py - SysMon RIG Settings Window
Launched from the tray menu. Lets users pick global theme colors
and per-widget accent color overrides. Changes save to settings.json
and widgets pick them up on the next paint cycle automatically.
"""
import tkinter as tk
from tkinter import colorchooser
import json, os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULTS = {
    "theme": {
        "blue":   "#00c8ff",
        "pink":   "#ff2d78",
        "green":  "#00ff9d",
        "purple": "#bf5fff",
        "orange": "#ff7c00",
        "red":    "#ff3c3c",
        "dim":    "#507090",
        "text":   "#c8e6ff",
    },
    "widgets": {
        "cpu": {"accent": None},   # None = use theme default
        "gpu": {"accent": None},
        "ram": {"accent": None},
        "net": {"accent": None},
    }
}

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        # Fill in any missing keys with defaults
        for key, val in DEFAULTS.items():
            if key not in data:
                data[key] = val
            elif isinstance(val, dict):
                for k2, v2 in val.items():
                    if k2 not in data[key]:
                        data[key][k2] = v2
        return data
    except Exception:
        return json.loads(json.dumps(DEFAULTS))

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ── Colour helpers ────────────────────────────────────────────────────────────
def hex_to_rgba(h, a=255):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0,2,4)) + (a,)

def rgba_to_hex(rgba):
    return '#{:02x}{:02x}{:02x}'.format(rgba[0], rgba[1], rgba[2])

# ── Settings Window ───────────────────────────────────────────────────────────
class SettingsWindow:
    BG       = '#0d0d1f'
    CARD     = '#14142e'
    BORDER   = '#2a2a5a'
    FG       = '#c8e6ff'
    DIM      = '#607090'
    ACCENT   = '#00c8ff'
    FONT     = ('Segoe UI', 10)
    FONT_B   = ('Segoe UI', 10, 'bold')
    FONT_T   = ('Segoe UI', 13, 'bold')
    FONT_S   = ('Segoe UI', 9)

    def __init__(self):
        self.settings = load_settings()
        self._vars = {}   # key -> StringVar (hex colour)

        self.root = tk.Tk()
        self.root.title('SysMon RIG — Settings')
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        # Centre on screen
        w, h = 520, 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        self._build()
        self.root.mainloop()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg='#0a0a1a', pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text='SysMon RIG  //  Settings', font=self.FONT_T,
                 bg='#0a0a1a', fg=self.ACCENT).pack()
        tk.Label(hdr, text='Changes apply instantly — no restart needed',
                 font=self.FONT_S, bg='#0a0a1a', fg=self.DIM).pack()

        canvas = tk.Canvas(self.root, bg=self.BG, highlightthickness=0)
        scroll = tk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(fill='both', expand=True)

        frame = tk.Frame(canvas, bg=self.BG, padx=16, pady=10)
        frame_id = canvas.create_window((0,0), window=frame, anchor='nw')

        def _on_resize(e):
            canvas.itemconfig(frame_id, width=e.width)
        canvas.bind('<Configure>', _on_resize)
        frame.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.bind_all('<MouseWheel>',
            lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        # Global theme section
        self._section(frame, 'GLOBAL THEME COLORS')
        theme_keys = [
            ('blue',   'Blue  (CPU ring, default)'),
            ('green',  'Green (low usage / good temp)'),
            ('pink',   'Pink  (GPU ring, default)'),
            ('purple', 'Purple (RAM ring, default)'),
            ('orange', 'Orange (medium usage warning)'),
            ('red',    'Red   (high usage / hot temp)'),
            ('dim',    'Dim   (labels & subtitles)'),
            ('text',   'Text  (values & body text)'),
        ]
        for key, label in theme_keys:
            self._color_row(frame, label, f'theme.{key}',
                            self.settings['theme'][key])

        # Per-widget overrides
        self._section(frame, 'PER-WIDGET ACCENT OVERRIDES')
        tk.Label(frame, text='Leave blank to use the global theme color.',
                 font=self.FONT_S, bg=self.BG, fg=self.DIM).pack(anchor='w', pady=(0,8))

        widget_rows = [
            ('cpu', 'CPU widget accent'),
            ('gpu', 'GPU widget accent'),
            ('ram', 'RAM widget accent'),
            ('net', 'NET widget accent (upload)'),
        ]
        for wid, label in widget_rows:
            current = self.settings['widgets'][wid].get('accent') or ''
            self._color_row(frame, label, f'widget.{wid}', current, nullable=True)

        # Buttons
        btn_frame = tk.Frame(self.root, bg=self.BG, pady=12)
        btn_frame.pack(fill='x', padx=16)
        tk.Button(btn_frame, text='Reset to Defaults', font=self.FONT,
                  bg=self.CARD, fg=self.DIM, relief='flat', padx=12, pady=6,
                  cursor='hand2', command=self._reset).pack(side='left')
        tk.Button(btn_frame, text='Save & Close', font=self.FONT_B,
                  bg=self.ACCENT, fg='#000000', relief='flat', padx=16, pady=6,
                  cursor='hand2', command=self._save_close).pack(side='right')
        tk.Button(btn_frame, text='Save', font=self.FONT,
                  bg=self.CARD, fg=self.FG, relief='flat', padx=12, pady=6,
                  cursor='hand2', command=self._save).pack(side='right', padx=(0,8))

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=self.BG)
        f.pack(fill='x', pady=(14,6))
        tk.Label(f, text=title, font=('Segoe UI', 9, 'bold'),
                 bg=self.BG, fg=self.ACCENT).pack(side='left')
        tk.Frame(f, bg=self.BORDER, height=1).pack(
            side='left', fill='x', expand=True, padx=(10,0), pady=6)

    def _color_row(self, parent, label, key, value, nullable=False):
        var = tk.StringVar(value=value)
        self._vars[key] = var

        row = tk.Frame(parent, bg=self.CARD, pady=8, padx=10)
        row.pack(fill='x', pady=2)
        row.columnconfigure(1, weight=1)

        # Colour swatch
        swatch = tk.Label(row, width=3, bg=value if value else self.BG,
                          relief='flat', cursor='hand2')
        swatch.grid(row=0, column=0, padx=(0,10))

        tk.Label(row, text=label, font=self.FONT, bg=self.CARD,
                 fg=self.FG, anchor='w').grid(row=0, column=1, sticky='w')

        # Hex entry
        entry = tk.Entry(row, textvariable=var, font=('Courier New', 10),
                         bg='#1a1a3a', fg=self.FG, insertbackground=self.FG,
                         relief='flat', width=10, bd=4)
        entry.grid(row=0, column=2, padx=(8,6))

        def pick():
            current = var.get() or '#00c8ff'
            result = colorchooser.askcolor(color=current,
                                           title=f'Pick color — {label}',
                                           parent=self.root)
            if result and result[1]:
                var.set(result[1])
                swatch.configure(bg=result[1])
                self._auto_save(key, result[1])

        def on_entry_change(*_):
            val = var.get()
            if len(val) == 7 and val.startswith('#'):
                try:
                    int(val[1:], 16)
                    swatch.configure(bg=val)
                    self._auto_save(key, val)
                except ValueError:
                    pass
            elif nullable and val == '':
                swatch.configure(bg=self.BG)
                self._auto_save(key, None)

        var.trace_add('write', on_entry_change)

        tk.Button(row, text='Pick', font=self.FONT_S, bg='#1a1a3a',
                  fg=self.ACCENT, relief='flat', padx=8, pady=2,
                  cursor='hand2', command=pick).grid(row=0, column=3)

        if nullable:
            def clear():
                var.set('')
                swatch.configure(bg=self.BG)
                self._auto_save(key, None)
            tk.Button(row, text='Clear', font=self.FONT_S, bg='#1a1a3a',
                      fg=self.DIM, relief='flat', padx=8, pady=2,
                      cursor='hand2', command=clear).grid(row=0, column=4, padx=(4,0))

    def _auto_save(self, key, value):
        """Save to settings.json immediately so widgets pick it up live."""
        if key.startswith('theme.'):
            self.settings['theme'][key[6:]] = value or self.settings['theme'].get(key[6:])
        elif key.startswith('widget.'):
            wid = key[7:]
            self.settings['widgets'][wid]['accent'] = value if value else None
        save_settings(self.settings)

    def _save(self):
        save_settings(self.settings)

    def _save_close(self):
        save_settings(self.settings)
        self.root.destroy()

    def _reset(self):
        import copy
        self.settings = copy.deepcopy(DEFAULTS)
        save_settings(self.settings)
        # Refresh the UI
        self.root.destroy()
        SettingsWindow()


def open_settings():
    """Entry point called from tray.py"""
    import threading
    threading.Thread(target=SettingsWindow, daemon=True).start()


if __name__ == '__main__':
    SettingsWindow()
