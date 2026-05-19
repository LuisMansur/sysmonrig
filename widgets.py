"""
widgets.py - SysMon floating widgets
Pure Win32 layered windows — no tkinter window chrome at all.
Per-pixel alpha via UpdateLayeredWindow. Truly transparent background.
Colors loaded live from settings.json. Corner drag to resize.
"""
import ctypes, ctypes.wintypes as wt
import json, os, sys, time, threading, urllib.request
from ctypes import windll, byref, c_int, WINFUNCTYPE
from ctypes.wintypes import HWND, UINT, RECT, MSG

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.run([sys.executable,'-m','pip','install','pillow','-q'])
    from PIL import Image, ImageDraw, ImageFont

import tkinter as tk

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
POS_FILE      = os.path.join(BASE_DIR, 'positions.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
API_URL       = 'http://127.0.0.1:5050/stats'

# ── Palette stored in a mutable dict so load_colors() always takes effect ─────
_C = {
    'blue':   (0,  200,255, 255),
    'pink':   (255, 45,120, 255),
    'green':  (0,  255,157, 255),
    'purple': (191, 95,255, 255),
    'orange': (255,124,  0, 255),
    'red':    (255, 60, 60, 255),
    'dim':    (80, 120,160, 220),
    'text':   (200,230,255, 255),
}

def _hex(h, a=255):
    h=h.lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4))+(a,)

def load_colors():
    """Reload palette from settings.json into _C — mutations visible everywhere."""
    try:
        with open(SETTINGS_FILE) as f: s=json.load(f)
        t=s.get('theme',{})
        _C['blue']   = _hex(t.get('blue',   '#00c8ff'))
        _C['pink']   = _hex(t.get('pink',   '#ff2d78'))
        _C['green']  = _hex(t.get('green',  '#00ff9d'))
        _C['purple'] = _hex(t.get('purple', '#bf5fff'))
        _C['orange'] = _hex(t.get('orange', '#ff7c00'))
        _C['red']    = _hex(t.get('red',    '#ff3c3c'))
        _C['dim']    = _hex(t.get('dim',    '#507090'), 220)
        _C['text']   = _hex(t.get('text',   '#c8e6ff'))
        return s.get('widgets',{})
    except: return {}

# Colour accessors — always read current value from _C
def BLUE():   return _C['blue']
def PINK():   return _C['pink']
def GREEN():  return _C['green']
def PURPLE(): return _C['purple']
def ORANGE(): return _C['orange']
def RED():    return _C['red']
def DIM():    return _C['dim']
def TEXT():   return _C['text']
def RAINBOW():return [_C['blue'],_C['purple'],_C['pink'],_C['orange'],_C['green']]

def widget_accent(ws, wid, default_fn):
    acc=ws.get(wid,{}).get('accent')
    return _hex(acc) if acc else default_fn()

def uc(p):
    if p<40: return GREEN()
    if p<70: return BLUE()
    if p<85: return ORANGE()
    return RED()

def tc(t):
    if not t or t==0: return GREEN()
    if t<50:  return GREEN()
    if t<70:  return BLUE()
    if t<85:  return ORANGE()
    return RED()

# ── Fonts ─────────────────────────────────────────────────────────────────────
def _f(name,size):
    for n in [name,'arial.ttf']:
        try: return ImageFont.truetype(n,size)
        except: pass
    return ImageFont.load_default()

F_GIANT=_f('arialbd.ttf',80); F_BIG=_f('arialbd.ttf',42)
F_MED  =_f('arialbd.ttf',28); F_BODY=_f('arial.ttf',  24)
F_SMALL=_f('arial.ttf',  20); F_LABEL=_f('arialbd.ttf',17)

# ── Positions ─────────────────────────────────────────────────────────────────
def load_pos():
    try:
        with open(POS_FILE) as f: return json.load(f)
    except: return {}

def save_pos(wid,x,y):
    p=load_pos(); p[wid]={'x':x,'y':y}
    with open(POS_FILE,'w') as f: json.dump(p,f,indent=2)

# ── Stats ─────────────────────────────────────────────────────────────────────
_stats={}; _lock=threading.Lock(); _ok=False

def _poll():
    global _ok
    import json as _j, subprocess
    while True:
        try:
            with urllib.request.urlopen(API_URL,timeout=2) as r:
                data=_j.loads(r.read())
            try:
                res=subprocess.run(
                    ['nvidia-smi','--query-gpu=fan.speed,power.draw,power.limit',
                     '--format=csv,noheader,nounits'],
                    capture_output=True,text=True,timeout=2)
                if res.returncode==0:
                    p=[x.strip() for x in res.stdout.strip().split(',')]
                    data['gpu']['fan_speed']  =int(float(p[0]))
                    data['gpu']['power_draw'] =float(p[1])
                    data['gpu']['power_limit']=float(p[2])
            except: pass
            with _lock: _stats.update(data); _ok=True
        except: _ok=False
        time.sleep(1.2)

threading.Thread(target=_poll,daemon=True).start()
def get_stats():
    with _lock: return dict(_stats),_ok

# ── Win32 ─────────────────────────────────────────────────────────────────────
user32=windll.user32; gdi32=windll.gdi32; kernel32=windll.kernel32
user32.DefWindowProcW.restype =ctypes.c_ssize_t
user32.DefWindowProcW.argtypes=[HWND,UINT,ctypes.c_size_t,ctypes.c_ssize_t]
user32.CreateWindowExW.restype=HWND

WS_EX_LAYERED=0x00080000; WS_EX_TOPMOST=0x00000008; WS_EX_TOOLWINDOW=0x00000080
WS_POPUP=0x80000000; WS_VISIBLE=0x10000000; ULW_ALPHA=0x00000002
AC_SRC_OVER=0x00; AC_SRC_ALPHA=0x01; GWL_EXSTYLE=-20
HTCAPTION=2; HTBOTTOMRIGHT=17
WM_NCHITTEST=0x0084; WM_RBUTTONDOWN=0x0204; WM_DESTROY=0x0002
WM_EXITSIZEMOVE=0x0232; WM_MOUSEMOVE=0x0200; WM_MOUSELEAVE=0x02A3
TME_LEAVE=0x00000002

class TRACKMOUSEEVENT(ctypes.Structure):
    _fields_=[('cbSize',ctypes.c_ulong),('dwFlags',ctypes.c_ulong),
              ('hwndTrack',HWND),('dwHoverTime',ctypes.c_ulong)]

class POINT(ctypes.Structure):  _fields_=[('x',c_int),('y',c_int)]
class SIZE(ctypes.Structure):   _fields_=[('cx',c_int),('cy',c_int)]
class BLEND(ctypes.Structure):
    _fields_=[('BlendOp',ctypes.c_byte),('BlendFlags',ctypes.c_byte),
              ('SourceConstantAlpha',ctypes.c_byte),('AlphaFormat',ctypes.c_byte)]
class BIH(ctypes.Structure):
    _fields_=[('biSize',ctypes.c_uint32),('biWidth',ctypes.c_int32),
              ('biHeight',ctypes.c_int32),('biPlanes',ctypes.c_uint16),
              ('biBitCount',ctypes.c_uint16),('biCompression',ctypes.c_uint32),
              ('biSizeImage',ctypes.c_uint32),('biXPelsPerMeter',ctypes.c_int32),
              ('biYPelsPerMeter',ctypes.c_int32),('biClrUsed',ctypes.c_uint32),
              ('biClrImportant',ctypes.c_uint32)]
class WNDCLASSEX(ctypes.Structure):
    _fields_=[('cbSize',UINT),('style',UINT),('lpfnWndProc',ctypes.c_void_p),
              ('cbClsExtra',c_int),('cbWndExtra',c_int),('hInstance',ctypes.c_void_p),
              ('hIcon',ctypes.c_void_p),('hCursor',ctypes.c_void_p),
              ('hbrBackground',ctypes.c_void_p),('lpszMenuName',ctypes.c_wchar_p),
              ('lpszClassName',ctypes.c_wchar_p),('hIconSm',ctypes.c_void_p)]

WNDPROC=WINFUNCTYPE(ctypes.c_ssize_t,HWND,UINT,ctypes.c_size_t,ctypes.c_ssize_t)

def push_image(hwnd,img):
    w,h=img.size; r,g,b,a=img.split()
    raw=Image.merge('RGBA',(b,g,r,a)).tobytes()
    sdc=user32.GetDC(None); mdc=gdi32.CreateCompatibleDC(sdc)
    bmi=BIH(ctypes.sizeof(BIH),w,-h,1,32,0,0,0,0,0,0)
    ppv=ctypes.c_void_p()
    hbm=gdi32.CreateDIBSection(mdc,byref(bmi),0,byref(ppv),None,0)
    ctypes.memmove(ppv,raw,len(raw)); old=gdi32.SelectObject(mdc,hbm)
    blend=BLEND(AC_SRC_OVER,0,255,AC_SRC_ALPHA)
    user32.UpdateLayeredWindow(hwnd,sdc,None,byref(SIZE(w,h)),mdc,
                               byref(POINT(0,0)),0,byref(blend),ULW_ALPHA)
    gdi32.SelectObject(mdc,old); gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(mdc); user32.ReleaseDC(None,sdc)

# ── Drawing helpers ───────────────────────────────────────────────────────────
def draw_ring(draw,cx,cy,r,pct,color,track_col=(20,20,55,180),width=16):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(8,8,22,200))
    box=[cx-r,cy-r,cx+r,cy+r]
    draw.arc(box,0,360,fill=track_col,width=width)
    if pct>0.3:
        sweep=360*min(pct/100,1.0)
        glow=tuple(min(255,c+40) for c in color[:3])+(60,)
        draw.arc(box,-90,-90+sweep,fill=glow, width=width+8)
        draw.arc(box,-90,-90+sweep,fill=color,width=width)

def tx(draw,x,y,text,color,font,anchor='mm'):
    for ox,oy in [(-2,-2),(-2,2),(2,-2),(2,2),(0,2),(0,-2),(-2,0),(2,0)]:
        draw.text((x+ox,y+oy),str(text),fill=(0,0,0,210),font=font,anchor=anchor)
    draw.text((x,y),str(text),fill=color,font=font,anchor=anchor)

# ── Win32 window ─────────────────────────────────────────────────────────────
_instances={}; _wndproc_cb=None

def _wnd_proc(hwnd,msg,wparam,lparam):
    inst=_instances.get(hwnd)
    if inst:
        if msg==WM_NCHITTEST:
            pt=wt.POINT(); user32.GetCursorPos(byref(pt))
            wr=wt.RECT(); user32.GetWindowRect(hwnd,byref(wr))
            rx=pt.x-wr.left; ry=pt.y-wr.top
            if rx>=inst.W-20 and ry>=inst.H-20: return HTBOTTOMRIGHT
            return HTCAPTION
        if msg==WM_MOUSEMOVE:
            if not inst._hovered:
                inst._hovered=True
                # Ask Windows to send WM_MOUSELEAVE when mouse exits
                tme=TRACKMOUSEEVENT(ctypes.sizeof(TRACKMOUSEEVENT),
                                    TME_LEAVE,hwnd,0)
                user32.TrackMouseEvent(byref(tme))
                inst._paint()   # redraw to show handle
        if msg==WM_MOUSELEAVE:
            inst._hovered=False
            inst._paint()       # redraw to hide handle
        if msg==WM_RBUTTONDOWN:
            user32.DestroyWindow(hwnd); _instances.pop(hwnd,None); return 0
        if msg==WM_DESTROY:
            _instances.pop(hwnd,None); return 0
        if msg==WM_EXITSIZEMOVE:
            r=wt.RECT(); user32.GetWindowRect(hwnd,byref(r))
            inst.W=r.right-r.left; inst.H=r.bottom-r.top
            inst._save_size(); inst._paint(); return 0
    return user32.DefWindowProcW(hwnd,msg,ctypes.c_size_t(wparam),ctypes.c_ssize_t(lparam))

def _register_class():
    global _wndproc_cb
    _wndproc_cb=WNDPROC(_wnd_proc); hinstance=kernel32.GetModuleHandleW(None)
    wc=WNDCLASSEX(); wc.cbSize=ctypes.sizeof(WNDCLASSEX); wc.style=0
    wc.lpfnWndProc=ctypes.cast(_wndproc_cb,ctypes.c_void_p)
    wc.hInstance=hinstance; wc.lpszClassName='SysMonWidget'; wc.hbrBackground=None
    user32.RegisterClassExW(byref(wc)); return hinstance

_hinstance=None

class Widget:
    def __init__(self,wid,W,H,xy):
        global _hinstance
        self.id=wid; self.W=W; self.H=H
        pos=load_pos().get(wid,{}); sx=pos.get('x',xy[0]); sy=pos.get('y',xy[1])
        self.hwnd=user32.CreateWindowExW(
            WS_EX_LAYERED|WS_EX_TOPMOST|WS_EX_TOOLWINDOW,
            'SysMonWidget','',WS_POPUP|WS_VISIBLE,sx,sy,W,H,None,None,_hinstance,None)
        _instances[self.hwnd]=self
        self._hovered=False
        self._paint(); self._schedule()

    def _get_pos(self):
        r=wt.RECT(); user32.GetWindowRect(self.hwnd,byref(r)); return r.left,r.top

    def _save_size(self):
        try:
            with open(SETTINGS_FILE) as f: s=json.load(f)
        except: s={}
        if 'sizes' not in s: s['sizes']={}
        s['sizes'][self.id]={'w':self.W,'h':self.H}
        with open(SETTINGS_FILE,'w') as f: json.dump(s,f,indent=2)

    def _paint(self):
        ws=load_colors()   # mutates _C in place — all color functions see changes
        stats,ok=get_stats()
        img=Image.new('RGBA',(self.W,self.H),(0,0,0,0))
        draw=ImageDraw.Draw(img)
        if ok: self._draw(draw,stats,ws)
        else:  tx(draw,self.W//2,self.H//2,'NO SIGNAL',PINK(),F_MED)
        # Resize handle — only visible on hover
        if self._hovered:
            s=18
            draw.polygon([(self.W-s,self.H),(self.W,self.H-s),(self.W,self.H)],
                         fill=(255,255,255,120))
        push_image(self.hwnd,img)

    def _schedule(self):
        self._paint(); _root.after(1200,self._schedule)

    def _draw(self,draw,stats,ws): pass


# ── Widget drawings ───────────────────────────────────────────────────────────

class CpuWidget(Widget):
    def _draw(self,draw,s,ws):
        W,H=self.W,self.H; cpu=s.get('cpu',{})
        acc=widget_accent(ws,'cpu',BLUE)
        u=cpu.get('usage',0); col=uc(u)
        ct=cpu.get('temp'); freq=cpu.get('freq_ghz','--')
        cores=cpu.get('cores','--'); threads=cpu.get('threads','--')

        ph=58; pad=10
        r=int((H-ph-pad*3)*0.46); rw=max(14,int(r*0.14))
        cx=W//2; cy=r+pad+rw

        draw_ring(draw,cx,cy,r,u,col,width=rw)
        tx(draw,cx,cy-30,f'{int(u)}%', col,    F_GIANT)
        tx(draw,cx,cy+28,'CPU LOAD',   DIM(),  F_LABEL)
        tx(draw,cx,cy+52,f'{freq} GHz',TEXT(), F_SMALL)

        if ct:
            tr=int(r*0.28); trx=cx-r+tr+2; try_=cy+r-tr-2
            draw_ring(draw,trx,try_,tr,ct/105*100,tc(ct),width=int(tr*0.12))
            tx(draw,trx,try_-10,f'{ct}°',tc(ct), F_SMALL)
            tx(draw,trx,try_+12,'TEMP',  DIM(),  F_LABEL)

        py=cy+r+rw+pad; hw=W//2-6
        draw.rounded_rectangle([4,   py,hw,  py+ph],radius=8,fill=(8,8,22,210))
        draw.rounded_rectangle([hw+4,py,W-4, py+ph],radius=8,fill=(8,8,22,210))
        tx(draw,hw//2+2,        py+10,'CORES / THREADS',      DIM(),F_LABEL)
        tx(draw,hw//2+2,        py+34,f'{cores} / {threads}', acc,  F_BODY)
        tx(draw,hw+(W-hw)//2+2, py+10,'FREQUENCY',            DIM(),F_LABEL)
        tx(draw,hw+(W-hw)//2+2, py+34,f'{freq} GHz',          acc,  F_BODY)


class GpuWidget(Widget):
    GPU_MAX_CLK=2800

    def _draw(self,draw,s,ws):
        W,H=self.W,self.H; gpu=s.get('gpu',{})
        acc=widget_accent(ws,'gpu',PINK)
        u=gpu.get('gpu_usage',0); col=uc(u)
        gt=gpu.get('temp',0)
        vp=(gpu.get('mem_used',0)/max(gpu.get('mem_total',1),1))*100
        fan=gpu.get('fan_speed',0); pwr=gpu.get('power_draw',0)
        plim=gpu.get('power_limit',0)
        name=(gpu.get('name','') or '').replace('NVIDIA GeForce ','').replace('GeForce ','')

        ph=58; pad=10
        r=int((H-ph-pad*3)*0.46); rw=max(14,int(r*0.14))
        cx=W//2; cy=r+pad+rw

        draw_ring(draw,cx,cy,r,u,col,width=rw)
        tx(draw,cx,cy-30,f'{int(u)}%',col,    F_GIANT)
        tx(draw,cx,cy+22,'GPU LOAD',  DIM(),  F_LABEL)
        if name: tx(draw,cx,cy+46,name[:18],DIM(),F_LABEL)

        tr=int(r*0.28); trx=cx-r+tr+2; try_=cy+r-tr-2
        draw_ring(draw,trx,try_,tr,gt/105*100,tc(gt),width=int(tr*0.12))
        tx(draw,trx,try_-10,f'{gt}°',tc(gt), F_SMALL)
        tx(draw,trx,try_+12,'TEMP',  DIM(),  F_LABEL)

        py=cy+r+rw+pad; pw=(W-8)//3
        pwr_pct=(pwr/plim*100) if plim else 0
        for i,(lbl,val,vcol) in enumerate([
            ('VRAM', f'{int(vp)}%  {gpu.get("mem_used","--")}GB', uc(vp)),
            ('FAN',  f'{fan}%',                                     uc(fan)),
            ('POWER',f'{int(pwr)}W / {int(plim)}W',                uc(pwr_pct)),
        ]):
            x0=4+i*(pw+2)
            draw.rounded_rectangle([x0,py,x0+pw,py+ph],radius=8,fill=(8,8,22,210))
            tx(draw,x0+pw//2,py+10,lbl,DIM(), F_LABEL)
            tx(draw,x0+pw//2,py+34,val,vcol,  F_BODY)


class RamWidget(Widget):
    def _draw(self,draw,s,ws):
        W,H=self.W,self.H; ram=s.get('ram',{})
        acc=widget_accent(ws,'ram',PURPLE)
        p=ram.get('percent',0); col=uc(p)
        used=ram.get('used_gb',0); total=ram.get('total_gb',0)
        free=round(total-used,1) if total else '--'

        ph=58; pad=10
        r=int((H-ph-pad*3)*0.46); rw=max(14,int(r*0.14))
        cx=W//2; cy=r+pad+rw

        draw_ring(draw,cx,cy,r,p,col,width=rw)
        tx(draw,cx,cy-30,f'{int(p)}%',         col,   F_GIANT)
        tx(draw,cx,cy+28,'RAM USED',            DIM(), F_LABEL)
        tx(draw,cx,cy+52,f'{used} / {total} GB',TEXT(),F_SMALL)

        py=cy+r+rw+pad; hw=W//2-6
        draw.rounded_rectangle([4,   py,hw,  py+ph],radius=8,fill=(8,8,22,210))
        draw.rounded_rectangle([hw+4,py,W-4, py+ph],radius=8,fill=(8,8,22,210))
        tx(draw,hw//2+2,        py+10,'USED',      DIM(),  F_LABEL)
        tx(draw,hw//2+2,        py+34,f'{used} GB', acc,   F_BODY)
        tx(draw,hw+(W-hw)//2+2, py+10,'FREE',      DIM(),  F_LABEL)
        tx(draw,hw+(W-hw)//2+2, py+34,f'{free} GB',GREEN(),F_BODY)


class NetWidget(Widget):
    _peak_up=0.0; _peak_dn=0.0

    def _draw(self,draw,s,ws):
        W,H=self.W,self.H; net=s.get('network',{})
        up=net.get('upload_mbps',0); dn=net.get('download_mbps',0)
        acc_up=widget_accent(ws,'net',GREEN)

        NetWidget._peak_up=max(NetWidget._peak_up,up)
        NetWidget._peak_dn=max(NetWidget._peak_dn,dn)
        scale=max(100.0,NetWidget._peak_up,NetWidget._peak_dn)

        half=H//2; r=int(half*0.38); rw=max(10,int(r*0.18))
        cx=r+rw+10; px=cx+r+rw+18

        cyu=half//2
        draw_ring(draw,cx,cyu,r,min(up/scale*100,100),acc_up,width=rw)
        tx(draw,cx,cyu-18,f'{up}',   acc_up, F_BIG)
        tx(draw,cx,cyu+14,'Mbps',    DIM(),  F_SMALL)
        tx(draw,cx,cyu+34,'UPLOAD',  DIM(),  F_LABEL)
        tx(draw,px,cyu-16,'PEAK',                       DIM(),  F_LABEL,'la')
        tx(draw,px,cyu+8, f'{NetWidget._peak_up} Mbps',acc_up, F_BODY, 'la')

        draw.line([8,half,W-8,half],fill=(50,50,100,160),width=1)

        cyd=half+half//2
        draw_ring(draw,cx,cyd,r,min(dn/scale*100,100),BLUE(),width=rw)
        tx(draw,cx,cyd-18,f'{dn}',     BLUE(), F_BIG)
        tx(draw,cx,cyd+14,'Mbps',      DIM(),  F_SMALL)
        tx(draw,cx,cyd+34,'DOWNLOAD',  DIM(),  F_LABEL)
        tx(draw,px,cyd-16,'PEAK',                       DIM(),  F_LABEL,'la')
        tx(draw,px,cyd+8, f'{NetWidget._peak_dn} Mbps',BLUE(), F_BODY, 'la')


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__=='__main__':
    monitors=[]
    def _cb(hmon,hdc,lprect,lparam):
        r=lprect.contents; monitors.append((r.left,r.top,r.right,r.bottom)); return 1
    MONITORENUMPROC=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_ulong,ctypes.c_ulong,
                                        ctypes.POINTER(wt.RECT),ctypes.c_double)
    user32.EnumDisplayMonitors(None,None,MONITORENUMPROC(_cb),0)
    print(f'[Widgets] Monitors: {monitors}')

    panel=None
    for m in monitors:
        l,t,r,b=m
        if (r-l)>=(b-t)*2.5: panel=m; break
    if not panel:
        for m in monitors:
            if m[0]!=0 or m[1]!=0: panel=m; break
    if not panel and monitors: panel=monitors[0]

    ml,mt,mr,mb=panel or (0,0,1920,480)
    mw=mr-ml; mh=mb-mt
    print(f'[Widgets] Panel: {mw}x{mh} at ({ml},{mt})')

    GAP=16; H=mh-GAP*2; wy=mt+GAP
    avail=mw-GAP*5; W4=avail//4

    try:
        with open(SETTINGS_FILE) as f: _s=json.load(f)
        sizes=_s.get('sizes',{})
    except: sizes={}
    def wsize(wid,dw,dh):
        sz=sizes.get(wid,{}); return sz.get('w',dw),sz.get('h',dh)

    xs={'cpu':ml+GAP,'gpu':ml+GAP*2+W4,'ram':ml+GAP*3+W4*2,'net':ml+GAP*4+W4*3}

    print('[Widgets] Waiting for stats server...')
    for _ in range(20):
        try: urllib.request.urlopen(API_URL,timeout=1); print('[Widgets] Ready!'); break
        except: time.sleep(0.5)

    _hinstance=_register_class()
    _root=tk.Tk(); _root.withdraw(); _root.overrideredirect(True)

    CpuWidget('cpu',*wsize('cpu',W4,H),(xs['cpu'],wy))
    GpuWidget('gpu',*wsize('gpu',W4,H),(xs['gpu'],wy))
    RamWidget('ram',*wsize('ram',W4,H),(xs['ram'],wy))
    NetWidget('net',*wsize('net',W4,H),(xs['net'],wy))

    msg=MSG()
    while True:
        while user32.PeekMessageW(byref(msg),None,0,0,1):
            if msg.message==0x0012: sys.exit(0)
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        try: _root.update()
        except tk.TclError: break
        time.sleep(0.01)
