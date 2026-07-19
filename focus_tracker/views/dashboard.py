import time

from PyQt6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QPieSeries,
    QValueAxis,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CardWidget, StrongBodyLabel, SubtitleLabel, isDarkTheme

from ..app_icons import get_app_icon
from ..database import Database, day_bounds
from ..i18n import category_label, fmt_duration, tr

PRODUCTIVE_COLOR = QColor("#0ea47a")
DISTRACTING_COLOR = QColor("#e0526f")
NEUTRAL_COLOR = QColor("#8a8a8a")

CAT_COLORS = {
    "Productive": PRODUCTIVE_COLOR,
    "Distracting": DISTRACTING_COLOR,
    "Neutral": NEUTRAL_COLOR,
}


class StatCard(CardWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        self.titleLabel = BodyLabel(title, self)
        self.valueLabel = SubtitleLabel("—", self)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.valueLabel)

    def setValue(self, text: str):
        self.valueLabel.setText(text)


def _style_chart(chart: QChart):
    chart.setBackgroundBrush(QColor(0, 0, 0, 0))
    chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
    color = QColor("#ffffff") if isDarkTheme() else QColor("#202020")
    chart.setTitleBrush(color)
    if chart.legend():
        chart.legend().setLabelColor(color)


class DashboardPage(QWidget):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardPage")
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        root.setSpacing(16)

        currentRow = QHBoxLayout()
        currentRow.setSpacing(8)
        self.currentIcon = BodyLabel(self)
        self.currentIcon.setFixedSize(20, 20)
        self.currentLabel = BodyLabel("", self)
        currentRow.addWidget(self.currentIcon)
        currentRow.addWidget(self.currentLabel, 1)
        root.addLayout(currentRow)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.totalCard = StatCard(tr("total_time"), self)
        self.productiveCard = StatCard(tr("productive_time"), self)
        self.distractCard = StatCard(tr("distracting_time"), self)
        self.scoreCard = StatCard(tr("focus_score"), self)
        for i, card in enumerate(
            (self.totalCard, self.productiveCard, self.distractCard, self.scoreCard)
        ):
            grid.addWidget(card, 0, i)
        root.addLayout(grid)

        charts = QHBoxLayout()
        charts.setSpacing(12)

        barCard = CardWidget(self)
        barLayout = QVBoxLayout(barCard)
        barLayout.addWidget(StrongBodyLabel(tr("last_7_days"), barCard))
        self.barChart = QChart()
        self.barView = QChartView(self.barChart, barCard)
        self.barView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.barView.setStyleSheet("background: transparent")
        barLayout.addWidget(self.barView)
        charts.addWidget(barCard, 3)

        pieCard = CardWidget(self)
        pieLayout = QVBoxLayout(pieCard)
        pieLayout.addWidget(StrongBodyLabel(tr("by_category"), pieCard))
        self.pieChart = QChart()
        self.pieView = QChartView(self.pieChart, pieCard)
        self.pieView.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pieView.setStyleSheet("background: transparent")
        pieLayout.addWidget(self.pieView)
        charts.addWidget(pieCard, 2)

        topCard = CardWidget(self)
        topLayout = QVBoxLayout(topCard)
        topLayout.addWidget(StrongBodyLabel(tr("top_apps"), topCard))
        self.topAppsLayout = QVBoxLayout()
        self.topAppsLayout.setSpacing(8)
        topLayout.addLayout(self.topAppsLayout)
        topLayout.addStretch(1)
        charts.addWidget(topCard, 2)

        root.addLayout(charts, 1)

        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(15000)

    def set_current(self, app: str, title: str, seconds: float):
        if app:
            icon = get_app_icon(app, self.db.get_app_paths().get(app, ""))
            self.currentIcon.setPixmap(icon.pixmap(20, 20))
            self.currentLabel.setText(
                f'{tr("current_app")}: {app} — {title[:60]} ({fmt_duration(seconds)})'
            )

    def refresh(self):
        start, _ = day_bounds()
        cats = self.db.totals_by_category(start, time.time())
        total = sum(cats.values())
        productive = cats.get("Productive", 0.0)
        distracting = cats.get("Distracting", 0.0)
        self.totalCard.setValue(fmt_duration(total))
        self.productiveCard.setValue(fmt_duration(productive))
        self.distractCard.setValue(fmt_duration(distracting))
        rated = productive + distracting
        score = f"{round(productive / rated * 100)}%" if rated else "—"
        self.scoreCard.setValue(score)
        self._update_bar_chart()
        self._update_pie_chart(cats)
        self._update_top_apps(start)

    def _update_bar_chart(self):
        self.barChart.removeAllSeries()
        for axis in self.barChart.axes():
            self.barChart.removeAxis(axis)

        data = self.db.daily_totals(7)
        prodSet = QBarSet(tr("productive"))
        prodSet.setColor(PRODUCTIVE_COLOR)
        distSet = QBarSet(tr("distracting"))
        distSet.setColor(DISTRACTING_COLOR)
        labels = []
        max_val = 1.0
        for label, prod, dist in data:
            labels.append(label)
            prodSet.append(prod / 3600)
            distSet.append(dist / 3600)
            max_val = max(max_val, prod / 3600, dist / 3600)

        series = QBarSeries()
        series.append(prodSet)
        series.append(distSet)
        self.barChart.addSeries(series)

        axisX = QBarCategoryAxis()
        axisX.append(labels)
        axisY = QValueAxis()
        axisY.setRange(0, max_val * 1.1)
        axisY.setLabelFormat("%.1f h")
        textColor = QColor("#ffffff") if isDarkTheme() else QColor("#202020")
        for axis in (axisX, axisY):
            axis.setLabelsColor(textColor)
        self.barChart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        self.barChart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axisX)
        series.attachAxis(axisY)
        _style_chart(self.barChart)

    def _update_pie_chart(self, cats: dict):
        self.pieChart.removeAllSeries()
        series = QPieSeries()
        total = sum(cats.values())
        if total:
            for cat, seconds in sorted(cats.items(), key=lambda x: -x[1]):
                sl = series.append(f"{category_label(cat)} ({fmt_duration(seconds)})", seconds)
                sl.setColor(CAT_COLORS.get(cat, NEUTRAL_COLOR))
        else:
            sl = series.append(tr("no_data"), 1)
            sl.setColor(NEUTRAL_COLOR)
        series.setHoleSize(0.4)
        self.pieChart.addSeries(series)
        _style_chart(self.pieChart)

    def _update_top_apps(self, start_ts: float):
        while self.topAppsLayout.count():
            item = self.topAppsLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    w = sub.takeAt(0)
                    if w.widget():
                        w.widget().deleteLater()
                sub.deleteLater()
        rows = self.db.totals_by_app(start_ts, time.time())[:5]
        paths = self.db.get_app_paths()
        for app, cat, total in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            iconLabel = BodyLabel(self)
            iconLabel.setFixedSize(20, 20)
            iconLabel.setPixmap(get_app_icon(app, paths.get(app, "")).pixmap(20, 20))
            nameLabel = BodyLabel(app, self)
            timeLabel = BodyLabel(fmt_duration(total), self)
            timeLabel.setStyleSheet("color: gray")
            row.addWidget(iconLabel)
            row.addWidget(nameLabel, 1)
            row.addWidget(timeLabel)
            self.topAppsLayout.addLayout(row)
        if not rows:
            self.topAppsLayout.addWidget(BodyLabel("—", self))
