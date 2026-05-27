import psutil
import time
import threading
import subprocess
import ctypes
import sys
from flask import Flask, jsonify
from flask_cors import CORS

# ── Re-elevate to admin if not already (needed for CPU temps via WMI) ─────────
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if not is_admin():
    # Restart this script with admin rights
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1)
    sys.exit(0)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# ── GPU via pynvml ────────────────────────────────────────────────────────────
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
    gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    print("[GPU] NVIDIA GPU detected via pynvml")
except Exception as e:
    GPU_AVAILABLE = False
    print(f"[GPU] pynvml not available, will use nvidia-smi: {e}")

# ── CPU stats — polled in background so interval=0 never returns 0 ────────────
_cpu_stats = {"usage": 0.0, "freq_ghz": 0.0, "freq_max_ghz": 0.0, "temp": None,
              "cores": psutil.cpu_count(logical=False), "threads": psutil.cpu_count(logical=True)}

def _cpu_poll_loop():
    while True:
        try:
            usage = psutil.cpu_percent(interval=1)
            freq  = psutil.cpu_freq()
            _cpu_stats["usage"]        = usage
            _cpu_stats["freq_ghz"]     = round(freq.current / 1000, 2) if freq else 0
            _cpu_stats["freq_max_ghz"] = round(freq.max    / 1000, 2) if freq else 0
            new_temp = _get_cpu_temp()
            if new_temp is not None:          # only update if we got a real reading
                _cpu_stats["temp"] = new_temp
        except Exception as e:
            print(f"[CPU] poll error: {e}")

threading.Thread(target=_cpu_poll_loop, daemon=True).start()

def _get_cpu_temp():
    # Primary: HWiNFO64 shared memory (no admin needed, most accurate)
    try:
        t = _hwinfo_cpu_temp()
        if t is not None:
            return t
    except Exception:
        pass

    # Fallback: psutil sensors (Linux / some Windows configs)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for key in ['coretemp', 'k10temp', 'cpu_thermal', 'acpitz']:
                if key in temps:
                    vals = [t.current for t in temps[key]]
                    return round(sum(vals) / len(vals), 1)
    except Exception:
        pass

    # Fallback: WMI thermal zones (needs admin)
    try:
        import wmi
        w = wmi.WMI(namespace="root\\wmi")
        zones = w.MSAcpi_ThermalZoneTemperature()
        if zones:
            temps = [(z.CurrentTemperature / 10.0) - 273.15 for z in zones]
            valid = [t for t in temps if 0 < t < 120]
            if valid:
                return round(max(valid), 1)
    except Exception:
        pass

    # Fallback: LibreHardwareMonitor / OpenHardwareMonitor
    try:
        import wmi
        for ns in ["root\\LibreHardwareMonitor", "root\\OpenHardwareMonitor"]:
            try:
                w = wmi.WMI(namespace=ns)
                cpu_temps = [s.Value for s in w.Sensor()
                             if s.SensorType == 'Temperature' and 'CPU' in s.Name
                             and 'Max' not in s.Name and 'Average' not in s.Name]
                if cpu_temps:
                    return round(sum(cpu_temps) / len(cpu_temps), 1)
            except Exception:
                continue
    except Exception:
        pass
    return None


# ── HWiNFO64 shared memory reader ────────────────────────────────────────────
import ctypes as _ct, struct as _st

_k32 = _ct.windll.kernel32
_k32.OpenFileMappingW.restype = _ct.c_void_p
_k32.MapViewOfFile.restype    = _ct.c_void_p

_HWINFO_MAP   = "Global\\HWiNFO_SENS_SM2"
_SENSOR_TEMP  = 1
# Reading element layout (sz=460 per HWiNFO SDK):
# 0:   tReading  (4)
# 12:  szLabelOrig (128)
# 284: Value (double 8)
_LABEL_OFF = 12
_VALUE_OFF = 284
# We target "CPU Package" label — most accurate single CPU temp
_CPU_LABELS = ['CPU Package', 'Core Max', 'CPU (Tdie)', 'CPU Temp']

def _hwinfo_cpu_temp():
    hmap = _k32.OpenFileMappingW(0x0004, False, _HWINFO_MAP)
    if not hmap:
        return None
    try:
        pmap = _k32.MapViewOfFile(hmap, 0x0004, 0, 0, 0)
        if not pmap:
            return None
        try:
            hdr      = bytes((_ct.c_char * 44).from_address(pmap))
            off_read = _st.unpack_from('<I', hdr, 32)[0]
            sz_read  = _st.unpack_from('<I', hdr, 36)[0]
            num_read = _st.unpack_from('<I', hdr, 40)[0]
            best = None
            for i in range(num_read):
                chunk  = bytes((_ct.c_char * sz_read).from_address(pmap + off_read + i*sz_read))
                t_type = _st.unpack_from('<I', chunk, 0)[0]
                if t_type != _SENSOR_TEMP:
                    continue
                label  = chunk[_LABEL_OFF:_LABEL_OFF+128].rstrip(b'\x00').decode('utf-8','replace')
                if label in _CPU_LABELS:
                    val = _st.unpack_from('<d', chunk, _VALUE_OFF)[0]
                    if best is None or _CPU_LABELS.index(label) < _CPU_LABELS.index(best[0]):
                        best = (label, val)
            return round(best[1], 1) if best else None
        finally:
            _k32.UnmapViewOfFile(_ct.c_void_p(pmap))
    finally:
        _k32.CloseHandle(_ct.c_void_p(hmap))

# ── GPU helpers ───────────────────────────────────────────────────────────────
def _gpu_via_smi():
    try:
        r = subprocess.run(
            ['nvidia-smi',
             '--query-gpu=name,temperature.gpu,utilization.gpu,utilization.memory,'
             'clocks.current.graphics,clocks.current.memory,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            p = [x.strip() for x in r.stdout.strip().split(',')]
            return {"name": p[0], "temp": int(p[1]), "gpu_usage": int(p[2]),
                    "mem_usage_pct": int(p[3]), "core_clock": int(p[4]),
                    "mem_clock": int(p[5]),
                    "mem_used": round(int(p[6]) / 1024, 1),
                    "mem_total": round(int(p[7]) / 1024, 1)}
    except Exception as e:
        print(f"[GPU] smi error: {e}")
    return None

def get_gpu_stats():
    if GPU_AVAILABLE:
        try:
            temp     = pynvml.nvmlDeviceGetTemperature(gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            util     = pynvml.nvmlDeviceGetUtilizationRates(gpu_handle)
            mem      = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
            core_clk = pynvml.nvmlDeviceGetClockInfo(gpu_handle, pynvml.NVML_CLOCK_GRAPHICS)
            mem_clk  = pynvml.nvmlDeviceGetClockInfo(gpu_handle, pynvml.NVML_CLOCK_MEM)
            name     = pynvml.nvmlDeviceGetName(gpu_handle)
            if isinstance(name, bytes): name = name.decode()
            return {"name": name, "temp": temp, "gpu_usage": util.gpu,
                    "mem_usage_pct": util.memory, "core_clock": core_clk,
                    "mem_clock": mem_clk,
                    "mem_used":  round(mem.used  / (1024**3), 1),
                    "mem_total": round(mem.total / (1024**3), 1)}
        except Exception as e:
            print(f"[GPU] pynvml read error: {e}")
    return _gpu_via_smi() or {
        "name": "GPU N/A", "temp": 0, "gpu_usage": 0, "mem_usage_pct": 0,
        "core_clock": 0, "mem_clock": 0, "mem_used": 0, "mem_total": 0}

# ── Network speed ─────────────────────────────────────────────────────────────
_net = {"time": time.time(), "sent": 0, "recv": 0, "up": 0.0, "down": 0.0}

def _net_poll_loop():
    while True:
        time.sleep(1)
        try:
            io  = psutil.net_io_counters()
            now = time.time()
            dt  = now - _net["time"]
            if dt > 0:
                _net["up"]   = round((io.bytes_sent - _net["sent"]) / dt / 1024 / 1024, 2)
                _net["down"] = round((io.bytes_recv - _net["recv"]) / dt / 1024 / 1024, 2)
            _net.update({"time": now, "sent": io.bytes_sent, "recv": io.bytes_recv})
        except Exception as e:
            print(f"[NET] poll error: {e}")

io0 = psutil.net_io_counters()
_net["sent"] = io0.bytes_sent
_net["recv"] = io0.bytes_recv
threading.Thread(target=_net_poll_loop, daemon=True).start()

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/stats')
def stats():
    ram = psutil.virtual_memory()
    return jsonify({
        "cpu": _cpu_stats,
        "ram": {"used_gb":  round(ram.used  / (1024**3), 1),
                "total_gb": round(ram.total / (1024**3), 1),
                "percent":  ram.percent},
        "gpu": get_gpu_stats(),
        "network": {"upload_mbps": _net["up"], "download_mbps": _net["down"]}
    })

if __name__ == '__main__':
    print("[SysMon] http://localhost:5050  (waiting 2s for first CPU sample...)")
    time.sleep(2)
    app.run(host='127.0.0.1', port=5050, debug=False)
