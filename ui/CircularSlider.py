import math
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPalette
from PyQt6.QtWidgets import QWidget, QApplication


class CircularSlider(QWidget):
    valueChanged = pyqtSignal(int)  # degrés 0..360

    def __init__(self, parent=None, radius=45):
        super().__init__(parent)
        self.radius = radius
        self._value = 0.0  # interne normalisé 0..1
        self.setFixedSize(radius * 2, radius * 2)

    # -------- API compatible QSlider --------

    def setMinimum(self, v):
        pass  # toujours 0

    def setMaximum(self, v):
        pass  # toujours 360

    def setValue(self, v):
        v = max(0, min(360, int(v)))
        self._value = v / 360.0
        self.valueChanged.emit(v)
        self.update()

    def value(self):
        return int(self._value * 360)

    # -------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPoint(self.radius, self.radius)

        # === CERCLE PRINCIPAL ===
        # painter.setPen(QColor(160, 160, 160))
        slider_gray = QApplication.palette().color(QPalette.ColorRole.Mid)
        darker_gray = QColor(
            int(slider_gray.red() * 0.4),
            int(slider_gray.green() * 0.4),
            int(slider_gray.blue() * 0.4),
            180
        )
        pen = QPen(darker_gray)
        pen.setWidth(6)  # <- largeur du bord
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self.radius - 4, self.radius - 4)

        # === CURSEUR ===
        pos = self._value_to_pos()
        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(pos, 8, 8)

    # -------------------------------------------------

    def mousePressEvent(self, event):
        self._update_value(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_value(event)

    # -------------------------------------------------

    def _update_value(self, event):
        pos = event.position().toPoint()
        dx = pos.x() - self.radius
        dy = pos.y() - self.radius

        # 0° en haut, sens horaire
        angle = (math.degrees(math.atan2(dy, dx)) + 450) % 360
        self._value = angle / 360.0

        self.valueChanged.emit(int(angle))
        self.update()

    def _value_to_pos(self):
        angle = self._value * 2 * math.pi - math.pi / 2
        r = self.radius - 6

        x = self.radius + math.cos(angle) * r
        y = self.radius + math.sin(angle) * r
        return QPoint(int(x), int(y))
