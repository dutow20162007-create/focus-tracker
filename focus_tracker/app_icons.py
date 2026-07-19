import os
import sys

from PyQt6.QtCore import QFileInfo, QRect, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QFileIconProvider

_cache: dict[str, QIcon] = {}
_provider: QFileIconProvider | None = None

_LETTER_COLORS = [
    "#e0526f", "#0ea47a", "#3b78d8", "#b06fd8", "#d8963b",
    "#3bb3d8", "#7a8a3b", "#d85454", "#5a6acf", "#3f9e8f",
]


def _letter_icon(app: str) -> QIcon:
    letter = (app[:1] or "?").upper()
    color = QColor(_LETTER_COLORS[hash(app) % len(_LETTER_COLORS)])
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, 32, 32)
    painter.setPen(QColor("white"))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(18)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return QIcon(pixmap)


def get_app_icon(app: str, exe_path: str = "") -> QIcon:
    key = f"{app}|{exe_path}"
    if key in _cache:
        return _cache[key]

    icon = QIcon()
    if exe_path and os.path.exists(exe_path):
        global _provider
        if _provider is None:
            _provider = QFileIconProvider()
        icon = _provider.icon(QFileInfo(exe_path))
    if icon.isNull() and sys.platform.startswith("linux"):
        for name in (app, app.lower(), app.lower().replace(" ", "-")):
            themed = QIcon.fromTheme(name)
            if not themed.isNull():
                icon = themed
                break
    if icon.isNull():
        icon = _letter_icon(app)
    _cache[key] = icon
    return icon
