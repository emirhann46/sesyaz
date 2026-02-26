import collections

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

BAR_COUNT = 22
BAR_W = 3
BAR_GAP = 2
MAX_H = 30
IDLE_H = 2


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._levels: collections.deque[float] = collections.deque(
            [0.0] * BAR_COUNT, maxlen=BAR_COUNT
        )
        self.setFixedSize(BAR_COUNT * (BAR_W + BAR_GAP), MAX_H + 8)

        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(40)  # ~25 fps

    @Slot(float)
    def push_level(self, rms: float):
        self._levels.append(min(rms, 1.0))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_y = self.height() / 2

        for i, level in enumerate(self._levels):
            bar_h = max(IDLE_H, int(level * MAX_H))
            x = i * (BAR_W + BAR_GAP)
            y = int(center_y - bar_h / 2)

            # Dark teal → bright cyan (matches logo palette)
            r = int(38 + 42 * level)
            g = int(170 + 54 * level)
            b = int(185 + 55 * level)
            painter.setBrush(QColor(r, g, b, 210))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, BAR_W, bar_h, 1, 1)
