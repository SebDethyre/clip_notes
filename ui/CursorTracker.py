from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QApplication
from dataclasses import dataclass
POSITION_FILE = "/tmp/.cursor_position"

# class CursorTracker(QWidget):
#     """Tracker de curseur pour Wayland"""
#     def __init__(self):
#         super().__init__()
#         self.last_x = 0
#         self.last_y = 0
#         self.on_click_callback = None
        
#         self.setWindowFlags(
#             Qt.WindowType.FramelessWindowHint |
#             Qt.WindowType.WindowStaysOnBottomHint |
#             Qt.WindowType.Tool
#         )
        
#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
#         self.setMouseTracking(True)
        
#         screen = QApplication.primaryScreen()
#         geometry = screen.geometry()
#         self.setGeometry(geometry)

#         self.screen_width = geometry.width()
#         self.screen_height = geometry.height()
      
#         self.x_correction_left = 200
#         self.x_correction_right = -200
        
#         self.y_correction_top = 200
#         self.y_correction_bottom = 80
        
#         # Marge Ubuntu interpolée
#         self.x_margin_left = -45
#         self.x_margin_right = 45
        
#         self.y_margin_top = 45
#         self.y_margin_bottom = -45  # Réduit de 45 à 0
        
#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update_pos)
#         self.timer.start(150)

#     def update_pos(self):
#         pos = QCursor.pos()
#         raw_x = pos.x()
#         raw_y = pos.y()
#             # 🚫 Filtre Wayland : valeur invalide
#         if raw_x == 0 and raw_y == 0:
#             return 
        
#         x_ratio = pos.x() / self.screen_width if self.screen_width > 0 else 0
#         y_ratio = pos.y() / self.screen_height if self.screen_height > 0 else 0
        
#         x_offset = self.x_correction_left + (self.x_correction_right - self.x_correction_left) * x_ratio
#         x_margin = self.x_margin_left + (self.x_margin_right - self.x_margin_left) * x_ratio
#         self.last_x = int(pos.x() + x_offset + x_margin)
        
#         y_offset = self.y_correction_top + (self.y_correction_bottom - self.y_correction_top) * y_ratio
#         y_margin = self.y_margin_top + (self.y_margin_bottom - self.y_margin_top) * y_ratio
#         self.last_y = int(pos.y() + y_offset + y_margin)
        
#         try:
#             with open(POSITION_FILE, 'w') as f:
#                 f.write(f"{self.last_x},{self.last_y}")
#         except:
#             pass





#     def mousePressEvent(self, event):
#         if self.on_click_callback:
#             self.on_click_callback()
#         else:
#             self.close()

# def read_cursor_position():
#     try:
#         with open(POSITION_FILE, 'r') as f:
#             x, y = f.read().strip().split(',')
#             return int(x), int(y)
#     except:
#         return 0, 0


# if __name__ == "__main__":
#     import sys
#     app = QApplication(sys.argv)
#     tracker = CursorTracker()
#     tracker.show()
#     sys.exit(app.exec())










# class CursorTracker(QWidget):
#     """Tracker de curseur pour Wayland"""

#     def __init__(self):
#         super().__init__()

#         self.last_x = 0
#         self.last_y = 0
#         self.on_click_callback = None

#         self.setWindowFlags(
#             Qt.WindowType.FramelessWindowHint |
#             Qt.WindowType.WindowStaysOnBottomHint |
#             Qt.WindowType.Tool
#         )

#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
#         self.setMouseTracking(True)

#         screen = QApplication.primaryScreen()
#         geometry = screen.geometry()
#         self.setGeometry(geometry)

#         self.screen_width = geometry.width()
#         self.screen_height = geometry.height()

#         # ─────────────────────────────────────
#         # 🔧 Grille de calibration 3×3
#         # Chaque cellule : (x_offset, y_offset, x_margin, y_margin)
#         # ─────────────────────────────────────
#         self.grid_cols = 3
#         self.grid_rows = 3

#         self.grid = [
#             [(-200,  200, -45,  45), (0, 200, 0, 45), (200, 200, 45, 45)],
#             [(-200,   80, -45,   0), (0,  80, 0,  0), (200,  80, 45,  0)],
#             [(-200,  -80, -45, -45), (0, -80, 0, -45), (200, -80, 45, -45)],
#         ]

#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update_pos)
#         self.timer.start(150)

#     # ─────────────────────────────────────
#     # 🔧 Utilitaire interpolation
#     # ─────────────────────────────────────
#     def lerp(self, a, b, t):
#         return a + (b - a) * t

#     def bilerp(self, tl, tr, bl, br, tx, ty):
#         top = self.lerp(tl, tr, tx)
#         bottom = self.lerp(bl, br, tx)
#         return self.lerp(top, bottom, ty)

#     # ─────────────────────────────────────
#     # 🎯 Mise à jour position
#     # ─────────────────────────────────────
#     def update_pos(self):
#         pos = QCursor.pos()
#         raw_x = pos.x()
#         raw_y = pos.y()

#         # 🚫 Filtre Wayland
#         if raw_x == 0 and raw_y == 0:
#             return

#         # Position normalisée écran
#         x_ratio = raw_x / self.screen_width
#         y_ratio = raw_y / self.screen_height

#         # Taille des cellules
#         cell_w = self.screen_width / (self.grid_cols - 1)
#         cell_h = self.screen_height / (self.grid_rows - 1)

#         # Indices de cellule
#         cx = min(int(raw_x / cell_w), self.grid_cols - 2)
#         cy = min(int(raw_y / cell_h), self.grid_rows - 2)

#         # Position locale dans la cellule
#         tx = (raw_x - cx * cell_w) / cell_w
#         ty = (raw_y - cy * cell_h) / cell_h

#         # Coins de la grille
#         tl = self.grid[cy][cx]
#         tr = self.grid[cy][cx + 1]
#         bl = self.grid[cy + 1][cx]
#         br = self.grid[cy + 1][cx + 1]

#         # Interpolation bilinéaire
#         x_offset = self.bilerp(tl[0], tr[0], bl[0], br[0], tx, ty)
#         y_offset = self.bilerp(tl[1], tr[1], bl[1], br[1], tx, ty)
#         x_margin = self.bilerp(tl[2], tr[2], bl[2], br[2], tx, ty)
#         y_margin = self.bilerp(tl[3], tr[3], bl[3], br[3], tx, ty)

#         self.last_x = int(raw_x + x_offset + x_margin)
#         self.last_y = int(raw_y + y_offset + y_margin)

#         try:
#             with open(POSITION_FILE, 'w') as f:
#                 f.write(f"{self.last_x},{self.last_y}")
#         except:
#             pass


#     def mousePressEvent(self, event):
#         if self.on_click_callback:
#             self.on_click_callback()
#         else:
#             self.close()









################ 3 x ################################
#
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################
#######################################################




@dataclass
class GridCell:
    x_offset: int
    y_offset: int
    x_margin: int
    y_margin: int


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

        self.grid_cols = 3
        self.grid_rows = 3

        self.grid_def= {
            "top_left":     dict(x_off=150, y_off=150,  x_mar=-45, y_mar=-50),
            "top_center":   dict(x_off=0,    y_off=150,  x_mar=0,   y_mar=-50),
            "top_right":    dict(x_off=-200,  y_off=150,  x_mar=45,  y_mar=-50),

            "mid_left":     dict(x_off=150, y_off=150,   x_mar=-45, y_mar=-50),
            "mid_center":   dict(x_off=0,    y_off=150,   x_mar=0,   y_mar=-50),
            "mid_right":    dict(x_off=-200,  y_off=150,   x_mar=45,  y_mar=-50),

            "bot_left":     dict(x_off=150, y_off=40,  x_mar=-45, y_mar=-50),
            "bot_center":   dict(x_off=0,    y_off=40,  x_mar=0,   y_mar=-50),
            "bot_right":    dict(x_off=-200,  y_off=40,  x_mar=45,  y_mar=-50),
        }

        # self.grid_def= {
        #     "top_left":     dict(x_off=300,   y_off=400,  x_mar=-45, y_mar=-50),
        #     "top_center":   dict(x_off=0,     y_off=200,  x_mar=0,   y_mar=-50),
        #     "top_right":    dict(x_off=-150,  y_off=200,  x_mar=45,  y_mar=-50),

        #     "mid_left":     dict(x_off=350,  y_off=250,   x_mar=-45, y_mar=-50),
        #     "mid_center":   dict(x_off=0,    y_off=250,   x_mar=0,   y_mar=-50),
        #     "mid_right":    dict(x_off=-450, y_off=350,   x_mar=45,  y_mar=-50),

        #     "bot_left":     dict(x_off=350, y_off=40,  x_mar=-45, y_mar=-50),
        #     "bot_center":   dict(x_off=0,    y_off=40,  x_mar=0,   y_mar=-50),
        #     "bot_right":    dict(x_off=-350,  y_off=40,  x_mar=45,  y_mar=-50),
        # }

        # self.grid_def = {
        #     # Top row
        #     "top_left":     dict(x_off=-self.screen_width/2,  y_off=-self.screen_height/2,  x_mar=-45, y_mar=45),
        #     "top_center":   dict(x_off=0,                     y_off=-self.screen_height/2,  x_mar=0,   y_mar=45),
        #     "top_right":    dict(x_off=self.screen_width/2,   y_off=-self.screen_height/2,  x_mar=45,  y_mar=45),

        #     # Middle row
        #     "mid_left":     dict(x_off=-self.screen_width/2,  y_off=0,                     x_mar=-45, y_mar=0),
        #     "mid_center":   dict(x_off=0,                     y_off=0,                     x_mar=0,   y_mar=0),  # bien centré !
        #     "mid_right":    dict(x_off=self.screen_width/2,   y_off=0,                     x_mar=45,  y_mar=0),

        #     # Bottom row
        #     "bot_left":     dict(x_off=-self.screen_width/2,  y_off=self.screen_height/2,  x_mar=-45, y_mar=-45),
        #     "bot_center":   dict(x_off=0,                     y_off=self.screen_height/2,  x_mar=0,   y_mar=-45),
        #     "bot_right":    dict(x_off=self.screen_width/2,   y_off=self.screen_height/2,  x_mar=45,  y_mar=-45),
        # }

        self.grid = [
            [
                GridCell(**self._cell("top_left")),
                GridCell(**self._cell("top_center")),
                GridCell(**self._cell("top_right")),
            ],
            [
                GridCell(**self._cell("mid_left")),
                GridCell(**self._cell("mid_center")),
                GridCell(**self._cell("mid_right")),
            ],
            [
                GridCell(**self._cell("bot_left")),
                GridCell(**self._cell("bot_center")),
                GridCell(**self._cell("bot_right")),
            ],
        ]
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pos)
        self.timer.start(150)

    def _cell(self, key):
        d = self.grid_def[key]
        return dict(
            x_offset=d["x_off"],
            y_offset=d["y_off"],
            x_margin=d["x_mar"],
            y_margin=d["y_mar"],
        )

    def lerp(self, a, b, t):
        return a + (b - a) * t

    def bilerp(self, tl, tr, bl, br, tx, ty):
        top = self.lerp(tl, tr, tx)
        bottom = self.lerp(bl, br, tx)
        return self.lerp(top, bottom, ty)

    def update_pos(self):
        pos = QCursor.pos()
        raw_x = pos.x()
        raw_y = pos.y()

        if raw_x == 0 and raw_y == 0:
            return

        cell_w = self.screen_width / (self.grid_cols - 1)
        cell_h = self.screen_height / (self.grid_rows - 1)

        cx = min(int(raw_x / cell_w), self.grid_cols - 2)
        cy = min(int(raw_y / cell_h), self.grid_rows - 2)

        tx = (raw_x - cx * cell_w) / cell_w
        ty = (raw_y - cy * cell_h) / cell_h

        tl = self.grid[cy][cx]
        tr = self.grid[cy][cx + 1]
        bl = self.grid[cy + 1][cx]
        br = self.grid[cy + 1][cx + 1]

        x_offset = self.bilerp(
            tl.x_offset, tr.x_offset,
            bl.x_offset, br.x_offset,
            tx, ty
        )
        y_offset = self.bilerp(
            tl.y_offset, tr.y_offset,
            bl.y_offset, br.y_offset,
            tx, ty
        )
        x_margin = self.bilerp(
            tl.x_margin, tr.x_margin,
            bl.x_margin, br.x_margin,
            tx, ty
        )
        y_margin = self.bilerp(
            tl.y_margin, tr.y_margin,
            bl.y_margin, br.y_margin,
            tx, ty
        )

        self.last_x = int(raw_x + x_offset + x_margin)
        self.last_y = int(raw_y + y_offset + y_margin)

        try:
            with open(POSITION_FILE, "w") as f:
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







######################################################################
######################################################################
######################################################################
######################################################################
######################################################################


# from dataclasses import dataclass
# from PyQt6.QtWidgets import QWidget, QApplication
# from PyQt6.QtCore import Qt, QTimer
# from PyQt6.QtGui import QCursor

# POSITION_FILE = "/tmp/cursor_position.txt"





















# @dataclass
# class GridCell:
#     x_offset: int
#     y_offset: int
#     x_margin: int
#     y_margin: int


# class CursorTracker(QWidget):
#     """Tracker de curseur pour Wayland"""

#     def __init__(self):
#         super().__init__()

#         self.last_x = 0
#         self.last_y = 0
#         self.on_click_callback = None

#         self.setWindowFlags(
#             Qt.WindowType.FramelessWindowHint |
#             Qt.WindowType.WindowStaysOnBottomHint |
#             Qt.WindowType.Tool
#         )

#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
#         self.setMouseTracking(True)

#         screen = QApplication.primaryScreen()
#         geometry = screen.geometry()
#         self.setGeometry(geometry)

#         self.screen_width = geometry.width()
#         self.screen_height = geometry.height()

#         self.grid_cols = 5
#         self.grid_rows = 5

#         self.grid_def = {
#             "top_left":        dict(x_off=-200, y_off=200,  x_mar=-45, y_mar=45),
#             "top_mid_left":    dict(x_off=-100, y_off=200,  x_mar=-25, y_mar=45),
#             "top_center":      dict(x_off=0,    y_off=200,  x_mar=0,   y_mar=45),
#             "top_mid_right":   dict(x_off=100,  y_off=200,  x_mar=25,  y_mar=45),
#             "top_right":       dict(x_off=200,  y_off=200,  x_mar=45,  y_mar=45),

#             "upper_left":      dict(x_off=-200, y_off=120,  x_mar=-45, y_mar=25),
#             "upper_mid_left":  dict(x_off=-100, y_off=120,  x_mar=-25, y_mar=25),
#             "upper_center":    dict(x_off=0,    y_off=120,  x_mar=0,   y_mar=25),
#             "upper_mid_right": dict(x_off=100,  y_off=120,  x_mar=25,  y_mar=25),
#             "upper_right":     dict(x_off=200,  y_off=120,  x_mar=45,  y_mar=25),

#             "mid_left":        dict(x_off=-200, y_off=80,   x_mar=-45, y_mar=0),
#             "mid_mid_left":    dict(x_off=-100, y_off=80,   x_mar=-25, y_mar=0),
#             "mid_center":      dict(x_off=200,  y_off=50,   x_mar=0,   y_mar=-10),
#             "mid_mid_right":   dict(x_off=100,  y_off=80,   x_mar=25,  y_mar=0),
#             "mid_right":       dict(x_off=200,  y_off=80,   x_mar=45,  y_mar=0),

#             "lower_left":      dict(x_off=-200, y_off=-40,  x_mar=-45, y_mar=-25),
#             "lower_mid_left":  dict(x_off=-100, y_off=-40,  x_mar=-25, y_mar=-25),
#             "lower_center":    dict(x_off=0,    y_off=-40,  x_mar=0,   y_mar=-25),
#             "lower_mid_right": dict(x_off=100,  y_off=-40,  x_mar=25,  y_mar=-25),
#             "lower_right":     dict(x_off=200,  y_off=-40,  x_mar=45,  y_mar=-25),

#             "bot_left":        dict(x_off=-200, y_off=-80,  x_mar=-45, y_mar=-45),
#             "bot_mid_left":    dict(x_off=-100, y_off=-80,  x_mar=-25, y_mar=-45),
#             "bot_center":      dict(x_off=0,    y_off=-80,  x_mar=0,   y_mar=-45),
#             "bot_mid_right":   dict(x_off=100,  y_off=-80,  x_mar=25,  y_mar=-45),
#             "bot_right":       dict(x_off=200,  y_off=-80,  x_mar=45,  y_mar=-45),
#         }

#         self.grid = [
#             [GridCell(**self._cell(k)) for k in row]
#             for row in [
#                 ["top_left", "top_mid_left", "top_center", "top_mid_right", "top_right"],
#                 ["upper_left", "upper_mid_left", "upper_center", "upper_mid_right", "upper_right"],
#                 ["mid_left", "mid_mid_left", "mid_center", "mid_mid_right", "mid_right"],
#                 ["lower_left", "lower_mid_left", "lower_center", "lower_mid_right", "lower_right"],
#                 ["bot_left", "bot_mid_left", "bot_center", "bot_mid_right", "bot_right"],
#             ]
#         ]

#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update_pos)
#         self.timer.start(150)

#     def _cell(self, key):
#         d = self.grid_def[key]
#         return dict(
#             x_offset=d["x_off"],
#             y_offset=d["y_off"],
#             x_margin=d["x_mar"],
#             y_margin=d["y_mar"],
#         )

#     def lerp(self, a, b, t):
#         return a + (b - a) * t

#     def bilerp(self, tl, tr, bl, br, tx, ty):
#         top = self.lerp(tl, tr, tx)
#         bottom = self.lerp(bl, br, tx)
#         return self.lerp(top, bottom, ty)

#     def update_pos(self):
#         pos = QCursor.pos()
#         raw_x = pos.x()
#         raw_y = pos.y()

#         if raw_x == 0 and raw_y == 0:
#             return

#         cell_w = self.screen_width / (self.grid_cols - 1)
#         cell_h = self.screen_height / (self.grid_rows - 1)

#         cx = min(int(raw_x / cell_w), self.grid_cols - 2)
#         cy = min(int(raw_y / cell_h), self.grid_rows - 2)

#         tx = (raw_x - cx * cell_w) / cell_w
#         ty = (raw_y - cy * cell_h) / cell_h

#         tl = self.grid[cy][cx]
#         tr = self.grid[cy][cx + 1]
#         bl = self.grid[cy + 1][cx]
#         br = self.grid[cy + 1][cx + 1]

#         x_offset = self.bilerp(tl.x_offset, tr.x_offset, bl.x_offset, br.x_offset, tx, ty)
#         y_offset = self.bilerp(tl.y_offset, tr.y_offset, bl.y_offset, br.y_offset, tx, ty)
#         x_margin = self.bilerp(tl.x_margin, tr.x_margin, bl.x_margin, br.x_margin, tx, ty)
#         y_margin = self.bilerp(tl.y_margin, tr.y_margin, bl.y_margin, br.y_margin, tx, ty)

#         self.last_x = int(raw_x + x_offset + x_margin)
#         self.last_y = int(raw_y + y_offset + y_margin)

#         try:
#             with open(POSITION_FILE, "w") as f:
#                 f.write(f"{self.last_x},{self.last_y}")
#         except:
#             pass

#     def mousePressEvent(self, event):
#         if self.on_click_callback:
#             self.on_click_callback()
#         else:
#             self.close()
