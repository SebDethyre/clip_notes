from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QApplication

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
      
        self.x_correction_left = 200   # Correction à gauche
        self.x_correction_right = -200  # Correction à droite
        
        self.y_correction_top = 200     # Correction en haut
        self.y_correction_bottom = 80   # Correction en bas
        
        # print(f"Écran: {self.screen_width}x{self.screen_height}")
        # print(f"Milieu: X={self.screen_mid_x}, Y={self.screen_mid_y}")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pos)
        self.timer.start(150)
        

    def update_pos(self):
        pos = QCursor.pos()
        
        # Correction X PROPORTIONNELLE basée sur la position
        # Ratio : 0 à gauche, 1 à droite
        x_ratio = pos.x() / self.screen_width if self.screen_width > 0 else 0
        # Interpolation linéaire entre correction_left et correction_right
        x_offset = self.x_correction_left + (self.x_correction_right - self.x_correction_left) * x_ratio
        self.last_x = int(pos.x() + x_offset)
        
        # Correction Y PROPORTIONNELLE basée sur la position
        # Ratio : 0 en haut, 1 en bas
        y_ratio = pos.y() / self.screen_height if self.screen_height > 0 else 0
        # Interpolation linéaire entre correction_top et correction_bottom
        y_offset = self.y_correction_top + (self.y_correction_bottom - self.y_correction_top) * y_ratio
        self.last_y = int(pos.y() + y_offset)
    
    def mousePressEvent(self, event):
        if self.on_click_callback:
            self.on_click_callback()
        else:
            self.close()
