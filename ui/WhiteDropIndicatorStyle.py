from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStyle, QProxyStyle
from PyQt6.QtGui import QColor

class WhiteDropIndicatorStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_IndicatorItemViewItemDrop:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255))  # BLANC
            rect = option.rect
            rect.setHeight(6)  # 👈 ÉPAISSEUR RÉELLE
            painter.drawRect(rect)
            painter.restore()
        else:
            super().drawPrimitive(element, option, painter, widget)