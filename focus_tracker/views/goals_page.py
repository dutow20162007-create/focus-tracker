import time

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    PrimaryPushButton,
    ProgressBar,
    SpinBox,
    StrongBodyLabel,
    TransparentToolButton,
)

from ..database import Database, day_bounds
from ..i18n import category_label, fmt_duration, tr

CATEGORIES = ["Productive", "Neutral", "Distracting"]


class GoalCard(CardWidget):
    def __init__(self, goal_id: int, category: str, minutes: int, kind: str, on_delete, parent=None):
        super().__init__(parent)
        self.goal_id = goal_id
        self.category = category
        self.minutes = minutes
        self.kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 14, 14)
        text = f'{category_label(category)}: {tr("goal_min" if kind == "min" else "goal_max")} {minutes} {tr("minutes_day")}'
        col = QVBoxLayout()
        col.addWidget(StrongBodyLabel(text, self))
        self.progress = ProgressBar(self)
        self.progress.setRange(0, minutes)
        col.addWidget(self.progress)
        self.statusLabel = BodyLabel("", self)
        col.addWidget(self.statusLabel)
        layout.addLayout(col, 1)

        deleteBtn = TransparentToolButton(FluentIcon.DELETE, self)
        deleteBtn.clicked.connect(lambda: on_delete(self.goal_id))
        layout.addWidget(deleteBtn)

    def update_progress(self, spent_seconds: float):
        spent_min = int(spent_seconds // 60)
        self.progress.setValue(min(spent_min, self.minutes))
        if self.kind == "max" and spent_min > self.minutes:
            self.progress.error()
        self.statusLabel.setText(f"{fmt_duration(spent_seconds)} / {self.minutes} {tr('minutes_day')}")


class GoalsPage(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.setObjectName("goalsPage")
        self.db = db
        self._notified: set[int] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(12)

        addRow = QHBoxLayout()
        self.categoryBox = ComboBox(self)
        for cat in CATEGORIES:
            self.categoryBox.addItem(category_label(cat), userData=cat)
        self.kindBox = ComboBox(self)
        self.kindBox.addItem(tr("goal_min"), userData="min")
        self.kindBox.addItem(tr("goal_max"), userData="max")
        self.minutesSpin = SpinBox(self)
        self.minutesSpin.setRange(5, 720)
        self.minutesSpin.setValue(120)
        addBtn = PrimaryPushButton(FluentIcon.ADD, tr("add_goal"), self)
        addBtn.clicked.connect(self._add_goal)
        addRow.addWidget(self.categoryBox)
        addRow.addWidget(self.kindBox)
        addRow.addWidget(self.minutesSpin)
        addRow.addWidget(BodyLabel(tr("minutes_day"), self))
        addRow.addWidget(addBtn)
        addRow.addStretch(1)
        root.addLayout(addRow)

        self.goalsLayout = QVBoxLayout()
        self.goalsLayout.setSpacing(10)
        root.addLayout(self.goalsLayout)
        root.addStretch(1)

        self._cards: list[GoalCard] = []
        self._rebuild()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(15000)

    def _add_goal(self):
        self.db.add_goal(
            self.categoryBox.currentData(), self.minutesSpin.value(), self.kindBox.currentData()
        )
        self._rebuild()

    def _delete_goal(self, goal_id: int):
        self.db.remove_goal(goal_id)
        self._rebuild()

    def _rebuild(self):
        while self.goalsLayout.count():
            item = self.goalsLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards = []
        for goal_id, category, minutes, kind in self.db.get_goals():
            card = GoalCard(goal_id, category, minutes, kind, self._delete_goal, self)
            self._cards.append(card)
            self.goalsLayout.addWidget(card)
        self.refresh()

    def refresh(self):
        start, _ = day_bounds()
        cats = self.db.totals_by_category(start, time.time())
        for card in self._cards:
            card.update_progress(cats.get(card.category, 0.0))
