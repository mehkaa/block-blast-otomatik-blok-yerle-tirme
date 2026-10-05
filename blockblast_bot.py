"""Block Blast Canlı - otomatik oynama yardımcısı.

block-blast-canli.html sayfasını http://localhost:8765 adresinde açar ve sayfanın
istediği sürüklemeleri farenin sol tuşuyla, paylaşılan pencerenin (ya da ekranın)
üstünde yapar. Sadece bu bilgisayardan erişilebilir. Esc tuşu her an durdurur.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "block-blast-canli.html")
TOKEN = secrets.token_hex(16)

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

# Work in real screen pixels, so coordinates match on scaled (125%, 150%) displays.
if not user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4 & 0xFFFFFFFFFFFFFFFF)):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()

STOP = threading.Event()


def watch_escape():
    while True:
        if user32.GetAsyncKeyState(0x1B) & 0x8000:
            if not STOP.is_set():
                print("Esc: otomatik oynama durduruldu.")
            STOP.set()
        time.sleep(0.03)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def window_rects(hwnd):
    """Candidate screen rectangles of a window: visible frame, client area, full window."""
    h = wt.HWND(hwnd)
    rects = []
    r = RECT()
    if dwmapi.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
    c = RECT()
    if user32.GetClientRect(h, ctypes.byref(c)):
        pt = wt.POINT(0, 0)
        user32.ClientToScreen(h, ctypes.byref(pt))
        rects.append((pt.x, pt.y, c.right, c.bottom))
    w = RECT()
    if user32.GetWindowRect(h, ctypes.byref(w)):
        rects.append((w.left, w.top, w.right - w.left, w.bottom - w.top))
    return [x for x in rects if x[2] > 0 and x[3] > 0]


def find_window(label):
    m = re.match(r"window:(\d+)", label or "")
    if m and user32.IsWindow(wt.HWND(int(m.group(1)))):
        return int(m.group(1))
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def each(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value == label:
                    found.append(hwnd)
        return True

    user32.EnumWindows(each, 0)
    return found[0] if found else None


def monitors():
    mons = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(RECT), wt.LPARAM)

    def each(_hm, _hdc, lprc, _lp):
        r = lprc.contents
        mons.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    user32.EnumDisplayMonitors(None, None, proc(each), 0)
    return mons


def closest_aspect(rects, vw, vh, prefer=None):
    a = vw / vh
    return min(rects, key=lambda r: (round(abs(r[2] / r[3] - a), 2), 0 if prefer and prefer(r) else 1))


def target_rect(surface, label, vw, vh):
    """Screen rectangle that the shared video covers."""
    if surface != "monitor":
        hwnd = find_window(label)
        if hwnd:
            rects = window_rects(hwnd)
            if rects:
                return closest_aspect(rects, vw, vh), None
        if surface == "window":
            return None, "Paylaşılan pencere bulunamadı. Pencere kapandıysa tekrar paylaş ya da tüm ekranı paylaş."
        if surface == "browser":
            return None, "Tarayıcı sekmesi değil, telefon penceresini ya da tüm ekranı paylaş."
    mons = monitors()
    if not mons:
        return None, "Ekran bilgisi alınamadı."
    return closest_aspect(mons, vw, vh, prefer=lambda r: r[0] == 0 and r[1] == 0), None


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


MOVE, LEFTDOWN, LEFTUP, VIRTUALDESK, ABSOLUTE = 0x0001, 0x0002, 0x0004, 0x4000, 0x8000


def mouse(x, y, flags=0):
    """Real injected mouse input (SetCursorPos alone is ignored by Phone Link while dragging)."""
    vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
    inp = INPUT(type=0)
    inp.mi = MOUSEINPUT(round((x - vx) * 65535 / max(1, vw - 1)), round((y - vy) * 65535 / max(1, vh - 1)),
                        0, flags | MOVE | ABSOLUTE | VIRTUALDESK, 0, 0)
    if not user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)):
        print("Uyarı: Windows fare girdisini engelledi.")


def glide(x1, y1, x2, y2, ms):
    steps = max(8, int(ms / 15))
    for i in range(1, steps + 1):
        if STOP.is_set():
            return
        t = i / steps
        t = t * t * (3 - 2 * t)
        mouse(round(x1 + (x2 - x1) * t), round(y1 + (y2 - y1) * t))
        time.sleep(ms / 1000 / steps)


class Hold:
    """A drag in progress: button is down, the page steers it with /move and finishes with /up."""
    lock = threading.Lock()
    active = False
    pos = (0, 0)
    restore = (0, 0)
    last = 0.0


def hold_down(x1, y1, x2, y2, ms):
    with Hold.lock:
        old = wt.POINT()
        user32.GetCursorPos(ctypes.byref(old))
        Hold.restore = (old.x, old.y)
        mouse(x1, y1)
        time.sleep(0.05)
        mouse(x1, y1, LEFTDOWN)
        Hold.active, Hold.pos, Hold.last = True, (x1, y1), time.time()
        time.sleep(0.12)
        glide(x1, y1, x2, y2, ms)
        Hold.pos, Hold.last = (x2, y2), time.time()


def hold_move(x, y):
    with Hold.lock:
        if not Hold.active:
            return False
        glide(*Hold.pos, x, y, 160)
        Hold.pos, Hold.last = (x, y), time.time()
        return True


def hold_up():
    with Hold.lock:
        if not Hold.active:
            return
        time.sleep(0.1)
        mouse(*Hold.pos, LEFTUP)
        Hold.active = False
        time.sleep(0.05)
        mouse(*Hold.restore)


def watch_hold():
    # Never leave the button pressed: release on Esc or if the page goes quiet mid-drag.
    while True:
        if Hold.active and (STOP.is_set() or time.time() - Hold.last > 4):
            hold_up()
            print("Basılı kalan fare tuşu bırakıldı.")
        time.sleep(0.1)


def drag(x1, y1, x2, y2, ms, dry=False):
    old = wt.POINT()
    user32.GetCursorPos(ctypes.byref(old))
    mouse(x1, y1)
    time.sleep(0.6 if dry else 0.05)
    if not dry:
        mouse(x1, y1, LEFTDOWN)
        time.sleep(0.12)
    steps = max(12, int(ms / 15))
    for i in range(1, steps + 1):
        if STOP.is_set():
            break
        t = i / steps
        t = t * t * (3 - 2 * t)
        mouse(round(x1 + (x2 - x1) * t), round(y1 + (y2 - y1) * t))
        time.sleep(ms / 1000 / steps)
    time.sleep(0.8 if dry else 0.15)
    if not dry:
        mouse(x2, y2, LEFTUP)
        time.sleep(0.05)
    mouse(old.x, old.y)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def local_host(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("localhost", "127.0.0.1")

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.local_host():
            return self.send(403, {"ok": False})
        if self.path in ("/", "/index.html"):
            with open(PAGE, "r", encoding="utf-8") as f:
                html = f.read().replace("__BOT_TOKEN__", TOKEN, 1)
            return self.send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if self.path == "/ping":
            return self.send(200, {"ok": True, "stopped": STOP.is_set()})
        self.send(404, {"ok": False})

    def do_POST(self):
        # Only the page served above knows the token, so other websites cannot move the mouse.
        if not self.local_host() or self.headers.get("X-Bot-Token") != TOKEN:
            return self.send(403, {"ok": False, "error": "İzin yok."})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send(400, {"ok": False, "error": "Bozuk istek."})
        if self.path == "/start":
            STOP.clear()
            print("Otomatik oynama başladı. Durdurmak için Esc.")
            return self.send(200, {"ok": True})
        if self.path == "/up":
            hold_up()
            return self.send(200, {"ok": True, "stopped": STOP.is_set()})
        if self.path not in ("/drag", "/down", "/move"):
            return self.send(404, {"ok": False})
        if STOP.is_set():
            hold_up()
            return self.send(200, {"ok": False, "stopped": True})
        try:
            vw, vh = float(data["vw"]), float(data["vh"])
            rect, err = target_rect(data.get("surface", ""), data.get("label", ""), vw, vh)
            if err:
                hold_up()
                return self.send(200, {"ok": False, "error": err})
            rx, ry, rw, rh = rect

            def to_screen(x, y):
                return round(rx + x * rw / vw), round(ry + y * rh / vh)

            x2, y2 = to_screen(float(data["tx"]), float(data["ty"]))
            if self.path == "/move":
                if not hold_move(x2, y2):
                    return self.send(200, {"ok": False, "error": "Parça elden düştü, tekrar denenecek."})
                return self.send(200, {"ok": True, "stopped": STOP.is_set()})
            x1, y1 = to_screen(float(data["sx"]), float(data["sy"]))
            ms = max(100, min(1500, int(data.get("ms", 350))))
            if self.path == "/down":
                print(f"Tut: alan {rect}, ({x1},{y1}) -> ({x2},{y2})")
                hold_down(x1, y1, x2, y2, ms)
            else:
                dry = bool(data.get("dry"))
                print(f"{'Test' if dry else 'Sürükleme'}: alan {rect}, ({x1},{y1}) -> ({x2},{y2})")
                drag(x1, y1, x2, y2, ms, dry)
        except (KeyError, ValueError, ZeroDivisionError):
            hold_up()
            return self.send(400, {"ok": False, "error": "Eksik koordinat."})
        return self.send(200, {"ok": True, "stopped": STOP.is_set()})


def main():
    if not os.path.exists(PAGE):
        print("block-blast-canli.html bu klasörde bulunamadı:", HERE)
        return
    threading.Thread(target=watch_escape, daemon=True).start()
    threading.Thread(target=watch_hold, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print("Block Blast Canlı açık:", url)
    print("Sayfayı Chrome ya da Edge'de kullan. Otomatik oynamayı durdurmak için Esc.")
    print("Kapatmak için bu pencereyi kapat ya da Ctrl+C.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
