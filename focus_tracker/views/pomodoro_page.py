from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    LargeTitleLabel,
    PrimaryPushButton,
    ProgressRing,
    PushButton,
    SubtitleLabel,
)

from ..config import cfg
from ..i18n import tr

WORK, BREAK, LONG_BREAK = "work", "break", "long_break"


class PomodoroPage(QWidget):
    phase_finished = pyqtSignal(str)  # emits the phase that just ended

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pomodoroPage")
        self.phase = WORK
        self.round = 1
        self.remaining = self._phase_seconds()
        self.running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(20)
        root.addStretch(1)

        self.phaseLabel = SubtitleLabel(tr("work"), self)
        self.phaseLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.phaseLabel)

        self.ring = ProgressRing(self)
        self.ring.setFixedSize(220, 220)
        self.ring.setStrokeWidth(10)
        self.ring.setRange(0, self._phase_seconds())
        self.ring.setValue(self._phase_seconds())
        ringRow = QHBoxLayout()
        ringRow.addStretch(1)
        ringRow.addWidget(self.ring)
        ringRow.addStretch(1)
        root.addLayout(ringRow)

        self.timeLabel = LargeTitleLabel(self._fmt(self.remaining), self)
        self.timeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.timeLabel)

        self.roundLabel = BodyLabel(f'{tr("round")} {self.round}/{cfg.pomodoroRounds.value}', self)
        self.roundLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.roundLabel)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.startBtn = PrimaryPushButton(FluentIcon.PLAY, tr("start"), self)
        self.startBtn.clicked.connect(self.toggle)
        self.resetBtn = PushButton(FluentIcon.SYNC, tr("reset"), self)
        self.resetBtn.clicked.connect(self.reset)
        buttons.addWidget(self.startBtn)
        buttons.addWidget(self.resetBtn)
        buttons.addStretch(1)
        root.addLayout(buttons)
        root.addStretch(2)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def _phase_seconds(self) -> int:
        if self.phase == WORK:
            return cfg.pomodoroWork.value * 60
        if self.phase == BREAK:
            return cfg.pomodoroBreak.value * 60
        return cfg.pomodoroLongBreak.value * 60

    @staticmethod
    def _fmt(seconds: int) -> str:
        m, s = divmod(max(0, seconds), 60)
        return f"{m:02d}:{s:02d}"

    def toggle(self):
        self.running = not self.running
        if self.running:
            self.timer.start()
            self.startBtn.setText(tr("pause"))
            self.startBtn.setIcon(FluentIcon.PAUSE)
        else:
            self.timer.stop()
            self.startBtn.setText(tr("start"))
            self.startBtn.setIcon(FluentIcon.PLAY)

    def reset(self):
        self.timer.stop()
        self.running = False
        self.phase = WORK
        self.round = 1
        self.remaining = self._phase_seconds()
        self._sync_ui()
        self.startBtn.setText(tr("start"))
        self.startBtn.setIcon(FluentIcon.PLAY)

    def _tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            finished = self.phase
            self.phase_finished.emit(finished)
            if finished == WORK:
                if self.round >= cfg.pomodoroRounds.value:
                    self.phase = LONG_BREAK
                else:
                    self.phase = BREAK
            else:
                if finished == LONG_BREAK:
                    self.round = 1
                else:
                    self.round += 1
                self.phase = WORK
            self.remaining = self._phase_seconds()
        self._sync_ui()

    def _sync_ui(self):
        self.phaseLabel.setText(tr(self.phase))
        self.timeLabel.setText(self._fmt(self.remaining))
        self.roundLabel.setText(f'{tr("round")} {self.round}/{cfg.pomodoroRounds.value}')
        self.ring.setRange(0, self._phase_seconds())
        self.ring.setValue(self.remaining)
