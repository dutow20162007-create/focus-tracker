import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QApplication, QMenu, QPushButton, QSystemTrayIcon
from qfluentwidgets import FluentIcon, FluentWindow, InfoBar, InfoBarPosition, NavigationItemPosition

from . import __version__
from .config import cfg
from .database import Database, day_bounds
from .i18n import category_label, tr
from .tracker import Tracker
from .updater import Updater, run_installer_and_exit
from .views.apps_page import AppsPage
from .views.dashboard import DashboardPage
from .views.goals_page import GoalsPage
from .views.pomodoro_page import PomodoroPage
from .views.settings_page import SettingsPage


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.resize(1100, 720)
        self.setWindowIcon(FluentIcon.STOP_WATCH.icon())

        self.db = Database()
        self._distraction_notified = False
        self._goal_notified: set[int] = set()

        self.dashboard = DashboardPage(self.db, self)
        self.appsPage = AppsPage(self.db, self)
        self.pomodoroPage = PomodoroPage(self)
        self.goalsPage = GoalsPage(self.db, self)
        self.settingsPage = SettingsPage(self.db, self)

        self.addSubInterface(self.dashboard, FluentIcon.HOME, tr("dashboard"))
        self.addSubInterface(self.appsPage, FluentIcon.APPLICATION, tr("apps"))
        self.addSubInterface(self.pomodoroPage, FluentIcon.STOP_WATCH, tr("pomodoro"))
        self.addSubInterface(self.goalsPage, FluentIcon.FLAG, tr("goals"))
        self.addSubInterface(
            self.settingsPage,
            FluentIcon.SETTING,
            tr("settings"),
            position=NavigationItemPosition.BOTTOM,
        )

        self.pomodoroPage.phase_finished.connect(self._on_phase_finished)

        self.tracker = Tracker(self)
        self.tracker.worker.poll_interval = cfg.pollInterval.value
        self.tracker.worker.idle_threshold = cfg.idleThreshold.value * 60
        self.tracker.worker.set_paused(not cfg.trackingEnabled.value)
        self.tracker.worker.segment_finished.connect(self._on_segment)
        self.tracker.worker.app_path_discovered.connect(self.db.set_app_path)
        self.tracker.worker.current_changed.connect(self.dashboard.set_current)
        cfg.trackingEnabled.valueChanged.connect(
            lambda v: self.tracker.worker.set_paused(not v)
        )
        cfg.pollInterval.valueChanged.connect(
            lambda v: setattr(self.tracker.worker, "poll_interval", v)
        )
        cfg.idleThreshold.valueChanged.connect(
            lambda v: setattr(self.tracker.worker, "idle_threshold", v * 60)
        )
        self.tracker.start()

        self._init_tray()
        self._init_updater()

    def _init_tray(self):
        self.tray = QSystemTrayIcon(FluentIcon.STOP_WATCH.icon(), self)
        menu = QMenu()
        showAction = QAction(tr("show"), menu)
        showAction.triggered.connect(self.showNormal)
        quitAction = QAction(tr("quit"), menu)
        quitAction.triggered.connect(self._quit)
        menu.addAction(showAction)
        menu.addAction(quitAction)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(tr("app_title"))
        self.tray.activated.connect(
            lambda reason: self.showNormal()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        self.tray.show()

    def _init_updater(self):
        self.updater = Updater(self)
        self.updater.update_available.connect(self._on_update_available)
        self.updater.download_done.connect(run_installer_and_exit)
        self.updater.download_failed.connect(
            lambda: InfoBar.error(
                tr("updates"), tr("update_failed"),
                position=InfoBarPosition.BOTTOM_RIGHT, parent=self,
            )
        )
        self._manual_check = False
        self.settingsPage.check_updates_clicked.connect(self._manual_update_check)
        self.updater.check()

    def _manual_update_check(self):
        self._manual_check = True
        self._update_found = False
        self.updater.check()
        QTimer.singleShot(
            12000,
            lambda: (
                InfoBar.success(
                    tr("updates"), tr("no_updates"),
                    position=InfoBarPosition.BOTTOM_RIGHT, parent=self,
                )
                if self._manual_check and not self._update_found
                else None
            ),
        )

    def _on_update_available(self, version: str, url: str):
        self._update_found = True
        bar = InfoBar.info(
            tr("updates"), tr("update_available", v=version),
            position=InfoBarPosition.BOTTOM_RIGHT, duration=-1, parent=self,
        )
        btn = QPushButton(tr("update_now"))

        def start_download():
            bar.close()
            InfoBar.info(
                tr("updates"), tr("downloading_update"),
                position=InfoBarPosition.BOTTOM_RIGHT, duration=5000, parent=self,
            )
            self.updater.download(url)

        btn.clicked.connect(start_download)
        bar.addWidget(btn)

    def _on_segment(self, app: str, title: str, start: float, duration: float):
        self.db.add_activity(app, title, start, duration)
        self._check_distraction()
        self._check_goals()

    def _notify(self, title: str, message: str):
        if not cfg.notifications.value:
            return
        if self.tray.isVisible():
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 5000)
        InfoBar.info(
            title, message, position=InfoBarPosition.BOTTOM_RIGHT, duration=5000, parent=self
        )

    def _check_distraction(self):
        if not cfg.distractionAlerts.value or self._distraction_notified:
            return
        start, _ = day_bounds()
        cats = self.db.totals_by_category(start, time.time())
        distracted_min = int(cats.get("Distracting", 0.0) // 60)
        if distracted_min >= cfg.distractionLimitMin.value:
            self._distraction_notified = True
            self._notify(tr("app_title"), tr("distraction_warning", m=distracted_min))

    def _check_goals(self):
        start, _ = day_bounds()
        cats = self.db.totals_by_category(start, time.time())
        for goal_id, category, minutes, kind in self.db.get_goals():
            if kind != "min" or goal_id in self._goal_notified:
                continue
            spent_min = int(cats.get(category, 0.0) // 60)
            if spent_min >= minutes:
                self._goal_notified.add(goal_id)
                self._notify(tr("app_title"), tr("goal_reached", cat=category_label(category), m=minutes))

    def _on_phase_finished(self, phase: str):
        self._notify(tr("pomodoro"), tr("work_done") if phase == "work" else tr("break_done"))

    def closeEvent(self, event):
        if cfg.minimizeToTray.value and self.tray.isVisible():
            self.hide()
            event.ignore()
            return
        self._quit()
        event.accept()

    def _quit(self):
        self.tracker.stop()
        self.tray.hide()
        QApplication.quit()
