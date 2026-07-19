import os
import sys
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import (
    ExpandLayout,
    FluentIcon,
    InfoBar,
    MessageBox,
    OptionsSettingCard,
    PushSettingCard,
    RangeSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    Theme,
    setTheme,
)

from .. import __version__
from ..config import cfg
from ..database import Database, day_bounds
from ..i18n import tr


class SettingsPage(ScrollArea):
    theme_changed = pyqtSignal()
    check_updates_clicked = pyqtSignal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self.db = db

        self.scrollWidget = QWidget(self)
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 20, 0, 20)
        self.enableTransparentBackground()

        # Appearance
        appearance = SettingCardGroup(tr("appearance"), self.scrollWidget)
        self.themeCard = OptionsSettingCard(
            cfg.theme,
            FluentIcon.BRUSH,
            tr("theme"),
            "",
            texts=[tr("theme_dark"), tr("theme_light")],
            parent=appearance,
        )
        self.languageCard = OptionsSettingCard(
            cfg.language,
            FluentIcon.LANGUAGE,
            tr("language"),
            tr("restart_hint"),
            texts=["Русский", "English"],
            parent=appearance,
        )
        appearance.addSettingCard(self.themeCard)
        appearance.addSettingCard(self.languageCard)

        # Tracking
        tracking = SettingCardGroup(tr("tracking"), self.scrollWidget)
        self.trackingCard = SwitchSettingCard(
            FluentIcon.STOP_WATCH, tr("tracking_enabled"), "", cfg.trackingEnabled, tracking
        )
        self.pollCard = RangeSettingCard(
            cfg.pollInterval, FluentIcon.SPEED_HIGH, tr("poll_interval"), "", tracking
        )
        self.idleCard = RangeSettingCard(
            cfg.idleThreshold, FluentIcon.POWER_BUTTON, tr("idle_threshold"), "", tracking
        )
        for card in (self.trackingCard, self.pollCard, self.idleCard):
            tracking.addSettingCard(card)

        # Pomodoro
        pomodoro = SettingCardGroup(tr("pomodoro_settings"), self.scrollWidget)
        for item, icon, label in (
            (cfg.pomodoroWork, FluentIcon.CAFE, tr("work_duration")),
            (cfg.pomodoroBreak, FluentIcon.PAUSE, tr("break_duration")),
            (cfg.pomodoroLongBreak, FluentIcon.CALENDAR, tr("long_break_duration")),
            (cfg.pomodoroRounds, FluentIcon.SYNC, tr("rounds")),
        ):
            pomodoro.addSettingCard(RangeSettingCard(item, icon, label, "", pomodoro))

        # Notifications
        notifications = SettingCardGroup(tr("notifications"), self.scrollWidget)
        notifications.addSettingCard(
            SwitchSettingCard(
                FluentIcon.RINGER, tr("notifications_enabled"), "", cfg.notifications, notifications
            )
        )
        notifications.addSettingCard(
            SwitchSettingCard(
                FluentIcon.MEGAPHONE,
                tr("distraction_alerts"),
                "",
                cfg.distractionAlerts,
                notifications,
            )
        )
        notifications.addSettingCard(
            RangeSettingCard(
                cfg.distractionLimitMin,
                FluentIcon.DATE_TIME,
                tr("distraction_limit"),
                "",
                notifications,
            )
        )

        # General
        general = SettingCardGroup(tr("general"), self.scrollWidget)
        self.autostartCard = SwitchSettingCard(
            FluentIcon.POWER_BUTTON, tr("autostart"), "", cfg.autostart, general
        )
        general.addSettingCard(self.autostartCard)
        general.addSettingCard(
            SwitchSettingCard(
                FluentIcon.MINIMIZE, tr("minimize_to_tray"), "", cfg.minimizeToTray, general
            )
        )

        # Data
        data = SettingCardGroup(tr("data"), self.scrollWidget)
        self.exportCard = PushSettingCard(
            tr("export_csv"), FluentIcon.SAVE, tr("export_csv"), "", data
        )
        self.exportCard.clicked.connect(self._export)
        self.clearCard = PushSettingCard(
            tr("clear_data"), FluentIcon.DELETE, tr("clear_data"), "", data
        )
        self.clearCard.clicked.connect(self._clear)
        data.addSettingCard(self.exportCard)
        data.addSettingCard(self.clearCard)

        # Updates
        updates = SettingCardGroup(tr("updates"), self.scrollWidget)
        self.updateCard = PushSettingCard(
            tr("check_updates"),
            FluentIcon.UPDATE,
            tr("check_updates"),
            f'{tr("version")}: {__version__}',
            updates,
        )
        self.updateCard.clicked.connect(self.check_updates_clicked)
        updates.addSettingCard(self.updateCard)

        for group in (appearance, tracking, pomodoro, notifications, general, data, updates):
            self.expandLayout.addWidget(group)
        self.expandLayout.setContentsMargins(30, 10, 30, 10)

        cfg.theme.valueChanged.connect(self._apply_theme)
        cfg.autostart.valueChanged.connect(self._apply_autostart)

    def _apply_theme(self, value: str):
        setTheme(Theme.DARK if value == "Dark" else Theme.LIGHT)
        self.theme_changed.emit()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_csv"), os.path.expanduser("~/focus_export.csv"), "CSV (*.csv)"
        )
        if path:
            start, _ = day_bounds(30)
            self.db.export_csv(path, start, time.time())
            InfoBar.success(tr("exported"), path, parent=self)

    def _clear(self):
        box = MessageBox(tr("clear_data"), tr("clear_confirm"), self.window())
        box.yesButton.setText(tr("yes"))
        box.cancelButton.setText(tr("cancel"))
        if box.exec():
            self.db.clear_all()

    def _apply_autostart(self, enabled: bool):
        try:
            if sys.platform == "win32":
                self._autostart_windows(enabled)
            elif sys.platform.startswith("linux"):
                self._autostart_linux(enabled)
        except Exception:
            pass

    @staticmethod
    def _autostart_windows(enabled: bool):
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enabled:
            cmd = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
            winreg.SetValueEx(key, "FocusTracker", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "FocusTracker")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)

    @staticmethod
    def _autostart_linux(enabled: bool):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "focus-tracker.desktop")
        if enabled:
            os.makedirs(autostart_dir, exist_ok=True)
            with open(desktop_file, "w") as f:
                f.write(
                    "[Desktop Entry]\nType=Application\nName=Focus Tracker\n"
                    f"Exec={sys.executable} {os.path.abspath(sys.argv[0])}\n"
                )
        elif os.path.exists(desktop_file):
            os.remove(desktop_file)
