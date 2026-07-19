import subprocess
import sys
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal


def get_active_window() -> tuple[str, str]:
    """Returns (app_name, window_title) of the currently focused window."""
    if sys.platform == "win32":
        return _active_window_windows()
    if sys.platform == "darwin":
        return _active_window_mac()
    return _active_window_linux()


def _active_window_windows() -> tuple[str, str]:
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app = ""
    try:
        import psutil

        app = psutil.Process(pid.value).name()
    except Exception:
        pass
    return app, buf.value


def _active_window_mac() -> tuple[str, str]:
    script = 'tell application "System Events" to get name of first process whose frontmost is true'
    try:
        app = subprocess.check_output(["osascript", "-e", script], text=True, timeout=2).strip()
        return app, app
    except Exception:
        return "", ""


def _active_window_linux() -> tuple[str, str]:
    try:
        out = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"], text=True, timeout=2
        )
        win_id = out.strip().split()[-1]
        if win_id in ("0x0", "0x0."):
            return "", ""
        out = subprocess.check_output(
            ["xprop", "-id", win_id, "WM_CLASS", "_NET_WM_NAME"], text=True, timeout=2
        )
        app, title = "", ""
        for line in out.splitlines():
            if line.startswith("WM_CLASS"):
                parts = line.split('"')
                if len(parts) >= 4:
                    app = parts[3]
            elif line.startswith("_NET_WM_NAME"):
                parts = line.split('"', 1)
                if len(parts) == 2:
                    title = parts[1].rstrip('"')
        return app, title
    except Exception:
        return "", ""


def get_idle_seconds() -> float:
    if sys.platform == "win32":
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
            return millis / 1000.0
        return 0.0
    try:
        out = subprocess.check_output(["xprintidle"], text=True, timeout=2)
        return int(out.strip()) / 1000.0
    except Exception:
        return 0.0


class TrackerWorker(QObject):
    """Polls the active window and emits finished activity segments."""

    segment_finished = pyqtSignal(str, str, float, float)  # app, title, start, duration
    current_changed = pyqtSignal(str, str, float)  # app, title, seconds on it

    def __init__(self, poll_interval: float = 2.0, idle_threshold: float = 180.0):
        super().__init__()
        self.poll_interval = poll_interval
        self.idle_threshold = idle_threshold
        self._running = True
        self._paused = False

    def stop(self):
        self._running = False

    def set_paused(self, paused: bool):
        self._paused = paused

    def run(self):
        cur_app, cur_title, cur_start = "", "", time.time()
        while self._running:
            time.sleep(self.poll_interval)
            if self._paused:
                self._flush(cur_app, cur_title, cur_start)
                cur_app, cur_title, cur_start = "", "", time.time()
                continue
            if get_idle_seconds() >= self.idle_threshold:
                self._flush(cur_app, cur_title, cur_start)
                cur_app, cur_title, cur_start = "", "", time.time()
                continue
            app, title = get_active_window()
            now = time.time()
            if app != cur_app or title != cur_title:
                self._flush(cur_app, cur_title, cur_start)
                cur_app, cur_title, cur_start = app, title, now
            if cur_app:
                self.current_changed.emit(cur_app, cur_title, now - cur_start)
        self._flush(cur_app, cur_title, cur_start)

    def _flush(self, app: str, title: str, start: float):
        if app:
            duration = time.time() - start
            if duration >= 1.0:
                self.segment_finished.emit(app, title, start, duration)


class Tracker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.worker = TrackerWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

    def start(self):
        self.thread.start()

    def stop(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait(5000)
