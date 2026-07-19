import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QTableWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ComboBox, SegmentedWidget, TableWidget

from ..database import Database, day_bounds, week_bounds
from ..i18n import category_label, fmt_duration, tr

CATEGORIES = ["Productive", "Neutral", "Distracting"]


class AppsPage(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.setObjectName("appsPage")
        self.db = db
        self._period = "today"

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(12)

        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("today", tr("today"), lambda: self._set_period("today"))
        self.pivot.addItem("week", tr("week"), lambda: self._set_period("week"))
        self.pivot.setCurrentItem("today")
        root.addWidget(self.pivot, 0, Qt.AlignmentFlag.AlignLeft)

        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("app"), tr("category"), tr("time")])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 320)
        self.table.setColumnWidth(1, 180)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(BodyLabel(tr("set_category") + ":", self))
        self.categoryBox = ComboBox(self)
        for cat in CATEGORIES:
            self.categoryBox.addItem(category_label(cat), userData=cat)
        self.categoryBox.currentIndexChanged.connect(self._assign_category)
        bottom.addWidget(self.categoryBox)
        bottom.addStretch(1)
        root.addLayout(bottom)

        self.table.itemSelectionChanged.connect(self._sync_combo)
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(15000)

    def _set_period(self, period: str):
        self._period = period
        self.refresh()

    def _bounds(self):
        if self._period == "week":
            return week_bounds()
        start, _ = day_bounds()
        return start, time.time()

    def refresh(self):
        selected = self._selected_app()
        start, end = self._bounds()
        rows = self.db.totals_by_app(start, end)
        self.table.setRowCount(len(rows))
        for i, (app, cat, total) in enumerate(rows):
            appItem = QTableWidgetItem(app)
            appItem.setData(Qt.ItemDataRole.UserRole, app)
            self.table.setItem(i, 0, appItem)
            self.table.setItem(i, 1, QTableWidgetItem(category_label(cat)))
            self.table.setItem(i, 2, QTableWidgetItem(fmt_duration(total)))
            if app == selected:
                self.table.selectRow(i)

    def _selected_app(self) -> str:
        items = self.table.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else ""

    def _sync_combo(self):
        app = self._selected_app()
        if not app:
            return
        cat = self.db.category_of(app)
        self.categoryBox.blockSignals(True)
        self.categoryBox.setCurrentIndex(CATEGORIES.index(cat))
        self.categoryBox.blockSignals(False)

    def _assign_category(self):
        app = self._selected_app()
        if not app:
            return
        cat = self.categoryBox.currentData()
        self.db.set_category(app, cat)
        self.refresh()
