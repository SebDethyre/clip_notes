from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QApplication

POSITION_FILE = "/tmp/.cursor_position"

class CursorTracker(QWidget):
    """Tracker de curseur pour Wayland"""
    def __init__(self):
        super().__init__()
        self.last_x = 0
        self.last_y = 0
        self.on_click_callback = None
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        self.setGeometry(geometry)

        self.screen_width = geometry.width()
        self.screen_height = geometry.height()
      
        self.x_correction_left = 200
        self.x_correction_right = -200
        
        self.y_correction_top = 200
        self.y_correction_bottom = 80
        
        # Marge Ubuntu interpolée
        self.x_margin_left = -45
        self.x_margin_right = 45
        
        self.y_margin_top = 45
        self.y_margin_bottom = -45  # Réduit de 45 à 0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pos)
        self.timer.start(150)

    def update_pos(self):
        pos = QCursor.pos()
        
        x_ratio = pos.x() / self.screen_width if self.screen_width > 0 else 0
        y_ratio = pos.y() / self.screen_height if self.screen_height > 0 else 0
        
        x_offset = self.x_correction_left + (self.x_correction_right - self.x_correction_left) * x_ratio
        x_margin = self.x_margin_left + (self.x_margin_right - self.x_margin_left) * x_ratio
        self.last_x = int(pos.x() + x_offset + x_margin)
        
        y_offset = self.y_correction_top + (self.y_correction_bottom - self.y_correction_top) * y_ratio
        y_margin = self.y_margin_top + (self.y_margin_bottom - self.y_margin_top) * y_ratio
        self.last_y = int(pos.y() + y_offset + y_margin)
        
        try:
            with open(POSITION_FILE, 'w') as f:
                f.write(f"{self.last_x},{self.last_y}")
        except:
            pass

    def mousePressEvent(self, event):
        if self.on_click_callback:
            self.on_click_callback()
        else:
            self.close()


def read_cursor_position():
    try:
        with open(POSITION_FILE, 'r') as f:
            x, y = f.read().strip().split(',')
            return int(x), int(y)
    except:
        return 0, 0


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    tracker = CursorTracker()
    tracker.show()
    sys.exit(app.exec())