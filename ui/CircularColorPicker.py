import math
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtWidgets import QWidget

class CircularColorPicker(QWidget):
    colorChanged = pyqtSignal(tuple)  # (r, g, b)

    def __init__(self, initial_rgb, parent=None, radius=38):
        super().__init__(parent)
        self.radius = radius

        # HSV interne
        c = QColor(*initial_rgb)
        self.h, self.s, self.v, _ = c.getHsvF()

        self.setFixedSize(radius * 2, radius * 2 + 40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPoint(self.radius, self.radius)

        # ===== ROUE HSV (H + S) =====
        for x in range(-self.radius, self.radius):
            for y in range(-self.radius, self.radius):
                r = (x * x + y * y) ** 0.5
                if r <= self.radius:
                    hue = (math.degrees(math.atan2(y, x)) + 360) % 360
                    sat = r / self.radius
                    color = QColor.fromHsvF(hue / 360, sat, self.v)
                    painter.setPen(color)
                    painter.drawPoint(center + QPoint(x, y))

        # ===== CURSEUR H/S =====
        hs_pos = self._hs_to_pos()
        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QColor(0, 0, 0))
        painter.drawEllipse(hs_pos, 4, 4)

        painter.setPen(QColor(255, 255, 255))
        painter.drawEllipse(hs_pos, 5, 5)

        # ===== BARRE LUMINOSITÉ (V) =====
        bar_y = self.radius * 2 + 4
        bar_rect = QRect(5, bar_y, self.radius * 2 - 10, 10)

        grad = QLinearGradient(bar_rect.left(), 0, bar_rect.right(), 0)
        grad.setColorAt(0.0, QColor.fromHsvF(self.h, self.s, 0.0))
        grad.setColorAt(1.0, QColor.fromHsvF(self.h, self.s, 1.0))
        painter.fillRect(bar_rect, grad)

        # curseur V
        vx = int(bar_rect.left() + self.v * bar_rect.width())
        painter.setPen(Qt.GlobalColor.white)
        painter.drawLine(vx, bar_rect.top(), vx, bar_rect.bottom())

        # ===== LABEL =====
        painter.setPen(QColor(255, 255, 255, 180))
        font = painter.font()
        font.setPointSize(9)
        font.setItalic(True)
        painter.setFont(font)

        text_rect = QRect(0, bar_y + 12, self.radius * 2, 16)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "saturation")

    def mousePressEvent(self, event):
        self._pick(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event)

    def _pick(self, event):
        pos = event.position().toPoint()

        # ----- ROUE -----
        dx = pos.x() - self.radius
        dy = pos.y() - self.radius
        r = (dx * dx + dy * dy) ** 0.5

        if r <= self.radius:
            self.h = ((math.degrees(math.atan2(dy, dx)) + 360) % 360) / 360
            self.s = min(1.0, r / self.radius)
            self._emit()
            return

        # ----- BARRE V -----
        bar_y = self.radius * 2 + 4
        if bar_y <= pos.y() <= bar_y + 10:
            self.v = min(1.0, max(0.0, (pos.x() - 5) / (self.radius * 2 - 10)))
            self._emit()

    def _hs_to_pos(self):
        angle = self.h * 2 * math.pi
        r = self.s * self.radius
        x = self.radius + math.cos(angle) * r
        y = self.radius + math.sin(angle) * r
        return QPoint(int(x), int(y))

    def _emit(self):
        color = QColor.fromHsvF(self.h, self.s, self.v)
        self.colorChanged.emit((color.red(), color.green(), color.blue()))
        self.update()
