from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QApplication
import json

POSITION_FILE = "/tmp/.cursor_position"

class CursorTracker(QWidget):
    """Tracker de curseur pour Wayland avec maillage calibré"""

    def __init__(self, mesh_file="cursor_mesh.json"):
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
        available = screen.availableGeometry()
        self.offset_x = available.x()
        self.offset_y = available.y()
        self.screen_width = available.width()
        self.screen_height = available.height()
        
        self.setGeometry(available)

        self.x_mesh = None
        self.y_mesh = None
        if mesh_file:
            try:
                with open(mesh_file, "r") as f:
                    data = json.load(f)
                    self.x_mesh = data["x_mesh"]
                    self.y_mesh = data["y_mesh"]
            except:
                pass

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pos)
        self.timer.start(200)

    def mousePressEvent(self, event):
        if self.on_click_callback:
            self.on_click_callback()
        else:
            self.close()

    # def update_pos(self):
    #     if self.x_mesh is None or self.y_mesh is None:
    #         return

    #     pos = QCursor.pos()
        
    #     rel_x = pos.x() - self.offset_x
    #     rel_y = pos.y() - self.offset_y
        
    #     x_ratio = max(0, min(1, rel_x / self.screen_width)) if self.screen_width > 0 else 0
    #     y_ratio = max(0, min(1, rel_y / self.screen_height)) if self.screen_height > 0 else 0

    #     def bilinear_interpolate(mesh, xr, yr):
    #         rows = len(mesh)
    #         cols = len(mesh[0])
    #         fx = xr * (rows - 1)
    #         fy = yr * (cols - 1)
    #         x0 = int(fx)
    #         y0 = int(fy)
    #         x1 = min(x0 + 1, rows - 1)
    #         y1 = min(y0 + 1, cols - 1)
    #         dx = fx - x0
    #         dy = fy - y0
    #         val = (1-dx)*(1-dy)*mesh[x0][y0] + (1-dx)*dy*mesh[x0][y1] + dx*(1-dy)*mesh[x1][y0] + dx*dy*mesh[x1][y1]
    #         return val

    #     x_error = bilinear_interpolate(self.x_mesh, x_ratio, y_ratio)
    #     y_error = bilinear_interpolate(self.y_mesh, x_ratio, y_ratio)

    #     # Soustraire l'erreur pour obtenir la vraie position
    #     self.last_x = int(rel_x - x_error)
    #     self.last_y = int(rel_y - y_error)
        
    #     try:
    #         with open(POSITION_FILE, 'w') as f:
    #             f.write(f"{self.last_x},{self.last_y}")
    #     except:
    #         pass
    def update_pos(self):
        if self.x_mesh is None or self.y_mesh is None:
            return

        pos = QCursor.pos()

        rel_x = pos.x() - self.offset_x
        rel_y = pos.y() - self.offset_y

        x_ratio = max(0, min(1, rel_x / self.screen_width)) if self.screen_width > 0 else 0
        y_ratio = max(0, min(1, rel_y / self.screen_height)) if self.screen_height > 0 else 0

        def bilinear_interpolate(mesh, xr, yr):
            rows = len(mesh)
            cols = len(mesh[0])
            fx = xr * (rows - 1)
            fy = yr * (cols - 1)
            x0 = int(fx)
            y0 = int(fy)
            x1 = min(x0 + 1, rows - 1)
            y1 = min(y0 + 1, cols - 1)
            dx = fx - x0
            dy = fy - y0
            return (
                (1 - dx) * (1 - dy) * mesh[x0][y0]
                + (1 - dx) * dy * mesh[x0][y1]
                + dx * (1 - dy) * mesh[x1][y0]
                + dx * dy * mesh[x1][y1]
            )

        x_error = bilinear_interpolate(self.x_mesh, x_ratio, y_ratio)
        y_error = bilinear_interpolate(self.y_mesh, x_ratio, y_ratio)

        corrected_x = rel_x - x_error
        corrected_y = rel_y - y_error

        # ===== CORRECTION HAUT D'ÉCRAN =====
        TOP_ZONE_RATIO = 0.25     # 25% supérieur
        TOP_MIDDLE_ZONE_RATIO = 0.5     # 25% supérieur
        MAX_Y_OFFSET_TOP = 100        # offset max en pixels
        MAX_Y_OFFSET_TOP_MIDDLE = 180        # offset max en pixels

        if y_ratio < TOP_ZONE_RATIO:
            factor = 1 - (y_ratio / TOP_ZONE_RATIO)  # 1 → 0
            corrected_y += MAX_Y_OFFSET_TOP * factor

        elif y_ratio < TOP_MIDDLE_ZONE_RATIO:
            factor = 1 - (y_ratio / TOP_MIDDLE_ZONE_RATIO)  # 1 → 0
            corrected_y += MAX_Y_OFFSET_TOP_MIDDLE * factor
        # ===== CORRECTION GAUCHE → DROITE =====
        LEFT_ZONE_1 = 0.25
        LEFT_ZONE_2 = 0.5
        LEFT_ZONE_3 = 0.75

        MAX_X_OFFSET_1 = 40    # bord gauche → 1/4
        MAX_X_OFFSET_2 = 25    # 1/4 → milieu
        MAX_X_OFFSET_3 = 65    # milieu → 3/4
        MAX_X_OFFSET_4 = -15   # 3/4 → bord droit

        if x_ratio < LEFT_ZONE_1:
            # Bord gauche
            factor = 1 - (x_ratio / LEFT_ZONE_1)
            corrected_x += MAX_X_OFFSET_1 * factor

        elif x_ratio < LEFT_ZONE_2:
            # 1/4 → milieu
            factor = 1 - (
                (x_ratio - LEFT_ZONE_1)
                / (LEFT_ZONE_2 - LEFT_ZONE_1)
            )
            corrected_x += MAX_X_OFFSET_2 * factor

        elif x_ratio < LEFT_ZONE_3:
            # milieu → 3/4
            factor = 1 - (
                (x_ratio - LEFT_ZONE_2)
                / (LEFT_ZONE_3 - LEFT_ZONE_2)
            )
            corrected_x += MAX_X_OFFSET_3 * factor

        else:
            # 3/4 → bord droit
            factor = (x_ratio - LEFT_ZONE_3) / (1 - LEFT_ZONE_3)
            corrected_x += MAX_X_OFFSET_4 * factor
        # ==================================

        self.last_x = int(corrected_x)
        self.last_y = int(corrected_y)

        try:
            with open(POSITION_FILE, "w") as f:
                f.write(f"{self.last_x},{self.last_y}")
        except:
            pass



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