import json
import os
import subprocess
import sys
import tempfile
import urllib.request

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from . import __version__

GITHUB_REPO = "dutow20162007-create/focus-tracker"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str)  # version, download url
    finished = pyqtSignal()

    def run(self):
        try:
            req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "")
            if latest and _parse_version(latest) > _parse_version(__version__):
                url = ""
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if name.endswith(".exe") and "setup" in name:
                        url = asset.get("browser_download_url", "")
                        break
                if not url:
                    for asset in data.get("assets", []):
                        if asset.get("name", "").lower().endswith(".exe"):
                            url = asset.get("browser_download_url", "")
                            break
                if url:
                    self.update_available.emit(latest, url)
        except Exception:
            pass
        self.finished.emit()


class UpdateDownloader(QObject):
    progress = pyqtSignal(int)
    done = pyqtSignal(str)  # path to downloaded installer
    failed = pyqtSignal()

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            path = os.path.join(tempfile.gettempdir(), "FocusTrackerSetup.exe")
            with urllib.request.urlopen(self.url, timeout=30) as resp, open(path, "wb") as f:
                total = int(resp.headers.get("Content-Length") or 0)
                read = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    read += len(chunk)
                    if total:
                        self.progress.emit(int(read / total * 100))
            self.done.emit(path)
        except Exception:
            self.failed.emit()


def run_installer_and_exit(path: str):
    if sys.platform == "win32":
        subprocess.Popen([path, "/SILENT"], close_fds=True)
    else:
        subprocess.Popen(["xdg-open", path], close_fds=True)
    from PyQt6.QtWidgets import QApplication

    QApplication.quit()


class Updater(QObject):
    """Owns background threads for update check/download."""

    update_available = pyqtSignal(str, str)
    download_done = pyqtSignal(str)
    download_failed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._threads: list[QThread] = []

    def check(self):
        thread = QThread(self)
        worker = UpdateChecker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.update_available.connect(self.update_available)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()

    def download(self, url: str):
        thread = QThread(self)
        worker = UpdateDownloader(url)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self.download_done)
        worker.failed.connect(self.download_failed)
        worker.done.connect(lambda _: thread.quit())
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()
