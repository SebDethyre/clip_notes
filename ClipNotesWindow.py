import sys
import math
import subprocess
import signal
import os
import getpass
import json
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QPainter, QColor, QIcon, QRadialGradient, QFont, QPalette
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QRect, QEasingCurve, QVariantAnimation, QEvent, QPointF
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QHBoxLayout, QSlider
from PyQt6.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextEdit, QToolTip, QLabel, QFileDialog
from PIL import Image, ImageDraw
import hashlib

from utils import *                
from ui import EmojiSelector

# 🗑️ 📝
# Constantes de configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIP_NOTES_FILE = os.path.join(SCRIPT_DIR, "clip_notes.txt")
CLIP_NOTES_FILE_JSON = os.path.join(SCRIPT_DIR, "clip_notes.json")
EMOJIS_FILE = os.path.join(SCRIPT_DIR, "emojis.txt")
THUMBNAILS_DIR = os.path.join(SCRIPT_DIR, "thumbnails")
NEON_PRINCIPAL=False

# Créer le dossier des miniatures s'il n'existe pas
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

def create_thumbnail(image_path, size=48):
    """
    Crée une miniature ronde d'une image et la sauvegarde dans le dossier thumbnails.
    Retourne le chemin relatif de la miniature.
    """
    try:
        # Ouvrir l'image
        img = Image.open(image_path)
        
        # Convertir en RGBA pour gérer la transparence
        img = img.convert('RGBA')
        
        # Redimensionner en carré en remplissant tout l'espace (crop si nécessaire)
        # On prend la plus petite dimension et on crop le reste
        min_dimension = min(img.size)
        left = (img.width - min_dimension) / 2
        top = (img.height - min_dimension) / 2
        right = (img.width + min_dimension) / 2
        bottom = (img.height + min_dimension) / 2
        img = img.crop((left, top, right, bottom))
        
        # Redimensionner au size voulu
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Créer un masque circulaire
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        
        # Appliquer le masque circulaire
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0))
        output.putalpha(mask)
        
        # Créer un nom unique basé sur le hash du chemin original
        hash_name = hashlib.md5(image_path.encode()).hexdigest()
        thumbnail_filename = f"{hash_name}.png"
        thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_filename)
        
        # Sauvegarder en PNG pour conserver la transparence
        output.save(thumbnail_path, "PNG", optimize=True)
        
        # Retourner le chemin absolu
        return thumbnail_path
        
    except Exception as e:
        print(f"Erreur lors de la création de la miniature: {e}")
        return None

DIALOG_STYLE = """
    QWidget {
        background-color: rgba(30, 30, 30, 180);
        border-radius: 12px;
        color: white;
    }
    QLineEdit, QTextEdit {
        background-color: rgba(255, 255, 255, 30);
        border: 1px solid rgba(255, 255, 255, 50);
        border-radius: 6px;
        padding: 4px;
        color: white;
    }
    QPushButton {
        background-color: rgba(255, 255, 255, 30);
        border: 1px solid rgba(255, 255, 255, 60);
        border-radius: 6px;
        padding: 6px;
        color: white;
    }
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 60);
    }
"""

os.environ.pop("XDG_SESSION_TYPE", None)

LOCK_FILE = os.path.join(SCRIPT_DIR, ".clipnotes.lock")

def create_lock_file():
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_lock_file():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass

class CalibrationWindow(QWidget):
    def __init__(self, tracker, main_app):
        super().__init__()
        self.tracker = tracker
        self.main_app = main_app  # Référence à l'app principale
        
        self.setWindowTitle("Calibration Curseur Wayland")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # === SLIDER X GAUCHE ===
        x_left_layout = QHBoxLayout()
        x_left_label = QLabel("X Correction Gauche:")
        self.x_left_value = QLabel(str(tracker.x_correction_left))
        self.x_left_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_left_slider.setRange(-300, 300)
        self.x_left_slider.setValue(tracker.x_correction_left)
        self.x_left_slider.valueChanged.connect(self.update_x_left)
        
        x_left_layout.addWidget(x_left_label)
        x_left_layout.addWidget(self.x_left_slider)
        x_left_layout.addWidget(self.x_left_value)
        layout.addLayout(x_left_layout)
        
        # === SLIDER X DROITE ===
        x_right_layout = QHBoxLayout()
        x_right_label = QLabel("X Correction Droite:")
        self.x_right_value = QLabel(str(tracker.x_correction_right))
        self.x_right_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_right_slider.setRange(-300, 300)
        self.x_right_slider.setValue(tracker.x_correction_right)
        self.x_right_slider.valueChanged.connect(self.update_x_right)
        
        x_right_layout.addWidget(x_right_label)
        x_right_layout.addWidget(self.x_right_slider)
        x_right_layout.addWidget(self.x_right_value)
        layout.addLayout(x_right_layout)
        
        # === SLIDER Y HAUT ===
        y_top_layout = QHBoxLayout()
        y_top_label = QLabel("Y Correction Haut:")
        self.y_top_value = QLabel(str(tracker.y_correction_top))
        self.y_top_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_top_slider.setRange(-300, 300)
        self.y_top_slider.setValue(tracker.y_correction_top)
        self.y_top_slider.valueChanged.connect(self.update_y_top)
        
        y_top_layout.addWidget(y_top_label)
        y_top_layout.addWidget(self.y_top_slider)
        y_top_layout.addWidget(self.y_top_value)
        layout.addLayout(y_top_layout)
        
        # === SLIDER Y BAS ===
        y_bottom_layout = QHBoxLayout()
        y_bottom_label = QLabel("Y Correction Bas:")
        self.y_bottom_value = QLabel(str(tracker.y_correction_bottom))
        self.y_bottom_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_bottom_slider.setRange(-300, 300)
        self.y_bottom_slider.setValue(tracker.y_correction_bottom)
        self.y_bottom_slider.valueChanged.connect(self.update_y_bottom)
        
        y_bottom_layout.addWidget(y_bottom_label)
        y_bottom_layout.addWidget(self.y_bottom_slider)
        y_bottom_layout.addWidget(self.y_bottom_value)
        layout.addLayout(y_bottom_layout)
        
        # === BOUTON AFFICHER VALEURS ===
        print_button = QPushButton("Afficher valeurs actuelles")
        print_button.clicked.connect(self.print_values)
        layout.addWidget(print_button)
        
        # === INFO ===
        info_label = QLabel("Le menu se relance automatiquement à chaque changement")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def refresh_menu(self):
        """Relance le menu à la position actuelle du curseur"""
        self.tracker.update_pos()
        x, y = self.tracker.last_x, self.tracker.last_y
        self.main_app.show_window_at(x, y, "")
    
    def update_x_left(self, value):
        self.tracker.x_correction_left = value
        self.x_left_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_x_right(self, value):
        self.tracker.x_correction_right = value
        self.x_right_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_y_top(self, value):
        self.tracker.y_correction_top = value
        self.y_top_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_y_bottom(self, value):
        self.tracker.y_correction_bottom = value
        self.y_bottom_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def print_values(self):
        print("\n=== VALEURS DE CALIBRATION ===")
        print(f"self.x_correction_left = {self.tracker.x_correction_left}")
        print(f"self.x_correction_right = {self.tracker.x_correction_right}")
        print(f"self.y_correction_top = {self.tracker.y_correction_top}")
        print(f"self.y_correction_bottom = {self.tracker.y_correction_bottom}")
        print("==============================\n")

# === TRACKER POUR WAYLAND ===
class CursorTracker(QWidget):
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
        self.timer.start(100)
        

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

    # def update_pos(self):
    #     pos = QCursor.pos()
        # if pos.x() < self.screen_mid_x / 2:  # Quart gauche (0-25%)
        #     self.last_x = pos.x() + 180
        # elif pos.x() < self.screen_mid_x:  # Entre quart et milieu (25-50%)
        #     self.last_x = pos.x() + 80
        # elif pos.x() < self.screen_mid_x + (self.screen_mid_x / 2):  # Entre milieu et 3/4 (50-75%)
        #     self.last_x = pos.x() - 80
        # else:  # Quart droit (75-100%)
        #     self.last_x = pos.x() - 150
        
        # # Correction Y
        # if pos.y() < self.screen_mid_y / 2:  # Quart supérieur
        #     self.last_y = pos.y() + 180
        # elif pos.y() < self.screen_mid_y:  # Entre quart et milieu
        #     self.last_y = pos.y() + 220
        # elif pos.y() > self.screen_mid_y:  # En dessous du milieu
        #     self.last_y = pos.y() + 80
        # else:
        #     self.last_y = pos.y()
    
    def mousePressEvent(self, event):
        if self.on_click_callback:
            self.on_click_callback()
        else:
            self.close()



# === NOUVELLE CLASSE: FENÊTRE TOOLTIP INVISIBLE ===
class TooltipWindow(QWidget):
    """Fenêtre semi-transparente pour afficher des messages en dessous du menu radial"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de la fenêtre
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # CRITIQUE: La tooltip ne doit pas intercepter les événements souris
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # Label pour le texte
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(80, 80, 80, 200);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        
        # Timer pour l'auto-masquage
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide)
        self.hide_timer.setSingleShot(True)
        
        # État initial
        self.hide()
    
    def show_message(self, text, duration_ms=0):
        """
        Affiche un message.
        
        Args:
            text: Le texte à afficher
            duration_ms: Durée d'affichage en millisecondes (0 = infini)
        """
        if not text:
            self.hide()
            return
        
        self.label.setText(text)
        self.adjustSize()
        self.show()
        
        # Si une durée est spécifiée, masquer automatiquement
        if duration_ms > 0:
            self.hide_timer.start(duration_ms)
        else:
            self.hide_timer.stop()
    
    def position_below_menu(self, menu_center_x, menu_center_y, menu_radius):
        """
        Positionne la fenêtre tooltip en dessous du menu radial.
        
        Args:
            menu_center_x: Position X du centre du menu
            menu_center_y: Position Y du centre du menu
            menu_radius: Rayon du menu (pour calculer la distance)
        """
        # Distance en pixels (environ 1cm = 38 pixels sur un écran standard)
        distance_below = menu_radius + 20  # Rayon du menu + 50 pixels de marge
        
        # Calculer la position
        tooltip_x = menu_center_x - self.width() // 2
        tooltip_y = menu_center_y + distance_below
        
        self.move(tooltip_x, tooltip_y)


class RadialMenu(QWidget):
    def __init__(self, x, y, buttons, parent=None, sub=False, tracker=None, app_instance=None):
        super().__init__(parent)  # Ne jamais utiliser tracker comme parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.sub = sub
        self.tracker = tracker
        self.app_instance = app_instance  # Référence à l'instance de App
        
        # Ajustement dynamique du rayon en fonction du nombre de boutons
        num_buttons = len(buttons)
        self.btn_size = 55
        
        if num_buttons <= 7:
            self.radius = 80  # Rayon par défaut pour 7 boutons ou moins
        else:
            # Augmentation proportionnelle du rayon pour plus de 7 boutons
            # Formule: on augmente le rayon pour maintenir un espacement confortable
            self.radius = int(80 * (num_buttons / 7))
        
        self.buttons = []

        self.diameter = 2 * (self.radius + self.btn_size)
        # Ajouter de l'espace pour les badges (50 pixels de chaque côté)
        self.widget_size = self.diameter + 100
        
        self._target_x = x - self.widget_size // 2
        self._target_y = y - self.widget_size // 2
        
        self.resize(self.widget_size, self.widget_size)
        self.move(self._target_x, self._target_y)

        self._x = x
        self._y = y
        self._central_text = ""
        self._tooltips = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)

        step = 2
        max_val = 50
        min_val = 0

        up = list(range(min_val, max_val + 1, step))
        down = list(range(max_val - step, min_val - 1, -step))
        sequence = up + down
        self.keyframes = sequence
        self._neon_radius = self.keyframes[0]  
        self.neon_enabled = False
        self._neon_opacity = 120
        self._neon_color = "cyan"
        self._widget_opacity = 1.0
        self._scale_factor = 0.1  # Démarrer petit pour l'animation

        self.current_index = 0
        
        # Stocker les couleurs par action pour chaque bouton
        self._button_colors = []  # Liste des couleurs pour chaque bouton
        self._button_actions = []  # Liste des actions pour chaque bouton
        self._button_labels = []  # Liste des labels pour chaque bouton
        self._hovered_action = None  # Action survolée (None, "copy", "term", ou "exec")
        self._action_badges = {}  # Dictionnaire des badges globaux par action
        
        # Activer le tracking de la souris pour détecter le hover
        self.setMouseTracking(True)
        
        
        # === NOUVELLE FENÊTRE TOOLTIP ===
        self.tooltip_window = TooltipWindow(parent=self)
        
        # Créer les boutons initiaux
        self._create_buttons(buttons)

    def _create_buttons(self, buttons):
        """Crée les boutons pour le menu radial"""
        # Couleurs par type d'action (plus légères et transparentes)
        action_colors = {
            "copy": QColor(255, 150, 100, 25),   # Orange transparent
            "term": QColor(100, 255, 150, 25),   # Vert transparent
            "exec": QColor(100, 150, 255, 25),   # Bleu transparent
        }
        
        # Tooltips pour les boutons spéciaux
        special_tooltips = {
            "➕": "Ajouter",
            "✏️": "Modifier",
            "➖": "Supprimer"
        }
        
        angle_step = 360 / len(buttons)
        for i, button in enumerate(buttons):
            if len(button) == 2:
                label, callback = button
                tooltip = ""
                action = None
            elif len(button) == 3:
                label, callback, tooltip = button
                action = None
            elif len(button) == 4:
                label, callback, tooltip, action = button
            else:
                label, callback = button
                tooltip = ""
                action = None
            
            # Si c'est un bouton spécial sans tooltip, utiliser le tooltip par défaut
            if label in special_tooltips and not tooltip:
                tooltip = special_tooltips[label]
            
            # Stocker la couleur, l'action et le label pour ce bouton
            color = action_colors.get(action, None)
            self._button_colors.append(color)
            self._button_actions.append(action)
            self._button_labels.append(label)
                
            angle = math.radians(i * angle_step)
            # Le centre du menu radial est maintenant au centre du widget agrandi
            center_offset = self.widget_size // 2
            bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
            by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2

            btn = QPushButton("", self)
            # Déterminer le type de label et utiliser la fonction appropriée
            if "/" in label:
                # C'est un chemin d'image - légèrement plus petit pour voir le hover
                btn.setIcon(QIcon(image_pixmap(label, 48)))
                btn.setIconSize(QSize(48, 48))
            elif is_emoji(label):
                # C'est un emoji
                btn.setIcon(QIcon(emoji_pixmap(label, 32)))
                btn.setIconSize(QSize(32, 32))
            else:
                # C'est du texte simple
                btn.setIcon(QIcon(text_pixmap(label, 32)))
                btn.setIconSize(QSize(32, 32))
            
            # Les boutons spéciaux (➕ ✏️ ➖) ont un fond transparent MAIS coloré au hover
            if label in ["➖", "✏️", "➕"]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 100);
                    }}
                """)
            elif "/" in label:
                # Boutons avec images - pas de padding, fond transparent
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 30);
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 10);
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 100);
                    }}
                """)
            btn.setFixedSize(self.btn_size, self.btn_size)
            btn.move(int(bx), int(by))
            btn.setVisible(False)
            btn.clicked.connect(self.make_click_handler(callback, label, tooltip, action))
            
            # Installer l'eventFilter pour tous les boutons (pour tooltips et badges)
            btn.installEventFilter(self)
            if tooltip:
                self._tooltips[btn] = tooltip
            self.buttons.append(btn)
        
        # Créer les 3 badges globaux (un par action) - seront positionnés dynamiquement
        self._action_badges = {}
        badge_info = {
            "copy": "✂️",
            "term": "💻", 
            "exec": "🚀"
        }
        
        for action, emoji in badge_info.items():
            badge = QLabel(emoji, self)
            badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 80);
                    border-radius: 17px;
                    padding: 4px;
                    font-size: 22px;
                }
            """)
            badge.setFixedSize(35, 35)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setVisible(False)
            # CRITIQUE: Les badges ne doivent pas intercepter les événements souris
            badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._action_badges[action] = badge

    def update_buttons(self, buttons):
        """Met à jour les boutons existants sans recréer le widget entier"""
        # Sauvegarder l'état actuel
        was_visible = self.isVisible()
        current_opacity = self._widget_opacity
        
        # Détruire les anciens boutons
        for btn in self.buttons:
            btn.removeEventFilter(self)
            btn.deleteLater()
        
        # Détruire les anciens badges
        if hasattr(self, '_action_badges'):
            for badge in self._action_badges.values():
                badge.deleteLater()
        
        self.buttons.clear()
        self._tooltips.clear()
        self._button_colors.clear()
        self._button_actions.clear()
        self._button_labels.clear()
        self._action_badges = {}
        
        # Recalculer le rayon si nécessaire
        num_buttons = len(buttons)
        old_radius = self.radius
        
        if num_buttons <= 7:
            self.radius = 80
        else:
            self.radius = int(80 * (num_buttons / 7))
        
        # Si le rayon a changé, redimensionner le widget
        if old_radius != self.radius:
            self.diameter = 2 * (self.radius + self.btn_size)
            self.widget_size = self.diameter + 100
            self.resize(self.widget_size, self.widget_size)
            # Recentrer
            self.move(self._x - self.widget_size // 2, self._y - self.widget_size // 2)
        
        # Réinitialiser le hover
        self._hovered_action = None
        
        # Créer les nouveaux boutons
        self._create_buttons(buttons)
        
        # Restaurer l'état
        if was_visible:
            self.set_widget_opacity(current_opacity)
            for btn in self.buttons:
                btn.setVisible(True)
        
        # CRITIQUE: Réactiver le mouse tracking après la reconstruction
        self.setMouseTracking(True)
        
        # Repositionner la fenêtre tooltip
        self._update_tooltip_position()
        
        self.update()

    def eventFilter(self, watched, event):
        """Gère les événements de hover sur les boutons"""
        if event.type() == QEvent.Type.Enter:
            # Afficher le message de hover dans la fenêtre tooltip
            if watched in self._tooltips:
                tooltip_text = self._tooltips[watched]
                # Afficher dans la fenêtre tooltip en dessous (durée infinie)
                self.tooltip_window.show_message(tooltip_text, 0)
                self._update_tooltip_position()
        elif event.type() == QEvent.Type.Leave:
            # Masquer le message quand on quitte le bouton
            self.tooltip_window.hide()
        
        return super().eventFilter(watched, event)

    def _update_tooltip_position(self):
        """Met à jour la position de la fenêtre tooltip en dessous du menu"""
        self.tooltip_window.position_below_menu(self._x, self._y, self.radius + self.btn_size)

    def set_central_text(self, value):
        self._central_text = value
        self.update()

    def get_neon_radius(self):
        return self._neon_radius

    def set_neon_radius(self, value):
        self._neon_radius = value
        self.update()

    def get_neon_opacity(self):
        return self._neon_opacity

    def set_neon_opacity(self, value):
        self._neon_opacity = value
        self.update()

    def get_neon_color(self):
        return self._neon_color

    def set_neon_color(self, value):
        self._neon_color = value
        self.update()

    def get_widget_opacity(self):
        return self._widget_opacity

    def set_widget_opacity(self, value):
        self._widget_opacity = value
        for i, btn in enumerate(self.buttons):
            # Vérifier si c'est un bouton spécial (➕ ✏️ ➖)
            label = self._button_labels[i] if i < len(self._button_labels) else ""
            if label in ["➖", "✏️", "➕"]:
                # Les boutons spéciaux restent transparents MAIS colorés au hover
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, {int(100 * value)});
                    }}
                """)
            elif "/" in label:
                # Boutons avec images - pas de padding
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, {int(30 * value)});
                    }}
                """)
            else:
                # Les autres boutons ont un fond avec opacité
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, {int(10 * value)});
                        border-radius: {self.btn_size // 2}px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, {int(100 * value)});
                    }}
                """)
        self.update()

    def toggle_neon(self, enabled: bool):
        self.neon_enabled = enabled
        self.update()

    def advance_animation(self):
        self.set_neon_radius(self.keyframes[self.current_index])
        self.update()
        self.current_index = (self.current_index + 1) % len(self.keyframes)

    def make_click_handler(self, cb, label, value, action):
        """Crée un handler de clic qui affiche un message de confirmation personnalisé selon l'action"""
        def handler():
            # Pour les boutons spéciaux uniquement, afficher un message
            if action is None:
                message = f"✓ {label}"
                self.tooltip_window.show_message(message, 1000)
                self._update_tooltip_position()
            
            # Exécuter le callback
            cb()
        return handler

    def mousePressEvent(self, event):
        if not any(btn.geometry().contains(event.pos()) for btn in self.buttons):
            # Masquer tous les badges
            for badge in self._action_badges.values():
                badge.setVisible(False)
            # Masquer la fenêtre tooltip
            self.tooltip_window.hide()
            self.handle_click_outside()
    
    def mouseMoveEvent(self, event):
        """Détecte quelle action est survolée par la souris (zone angulaire complète)"""
        if not self.buttons:
            return
        
        # Calculer la position relative au centre
        center = self.rect().center()
        dx = event.pos().x() - center.x()
        dy = event.pos().y() - center.y()
        
        # Calculer la distance au centre
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Si on est trop près du centre ou au-delà de la zone externe, pas de hover
        if distance < 30 or distance > self.radius + self.btn_size + 10:
            if self._hovered_action is not None:
                self._hovered_action = None
                # Masquer tous les badges
                for badge in self._action_badges.values():
                    badge.setVisible(False)
                self.update()
            return
        
        # Calculer l'angle de la souris (0° = droite, sens horaire)
        angle_rad = math.atan2(dy, dx)
        
        # Normaliser pour être positif (0 à 2π)
        if angle_rad < 0:
            angle_rad += 2 * math.pi
        
        # Convertir en degrés
        angle_deg = math.degrees(angle_rad)
        
        # Trouver l'index du bouton correspondant à cet angle
        angle_step = 360 / len(self.buttons)
        button_index = int(round(angle_deg / angle_step)) % len(self.buttons)
        
        # Récupérer l'action de ce bouton
        hovered_action = None
        if button_index < len(self._button_actions):
            hovered_action = self._button_actions[button_index]
        
        # Mettre à jour si l'action survolée a changé
        if hovered_action != self._hovered_action:
            self._hovered_action = hovered_action
            
            # Masquer tous les badges d'abord
            for badge in self._action_badges.values():
                badge.setVisible(False)
            
            # Si une action est survolée, calculer la position et afficher son badge
            if self._hovered_action and self._hovered_action in self._action_badges:
                # Trouver tous les indices des boutons ayant cette action
                indices = [i for i, action in enumerate(self._button_actions) if action == self._hovered_action]
                
                if indices:
                    angle_step = 360 / len(self.buttons)
                    
                    # Calculer l'angle moyen de tous ces boutons avec moyenne vectorielle
                    angles_rad = [math.radians(i * angle_step) for i in indices]
                    avg_x = sum(math.cos(a) for a in angles_rad) / len(angles_rad)
                    avg_y = sum(math.sin(a) for a in angles_rad) / len(angles_rad)
                    avg_angle_rad = math.atan2(avg_y, avg_x)
                    
                    # Distance du badge depuis le centre (juste après les boutons)
                    badge_distance = self.radius + self.btn_size + 20
                    
                    # Position du badge
                    center = self.rect().center()
                    badge_x = center.x() + badge_distance * math.cos(avg_angle_rad)
                    badge_y = center.y() + badge_distance * math.sin(avg_angle_rad)
                    
                    # Centrer le badge sur cette position
                    badge = self._action_badges[self._hovered_action]
                    badge.move(int(badge_x - badge.width() / 2), int(badge_y - badge.height() / 2))
                    badge.setVisible(True)
            
            self.update()
    
    def reveal_buttons(self):
        for btn in self.buttons:
            btn.setVisible(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setOpacity(self._widget_opacity)
        
        center = self.rect().center()
        
        # Appliquer le scale au diamètre
        scaled_diameter = int(self.diameter * self._scale_factor)
        
        # Le cercle du menu radial (plus petit que le widget)
        circle_rect = QRect(
            (self.widget_size - scaled_diameter) // 2,
            (self.widget_size - scaled_diameter) // 2,
            scaled_diameter,
            scaled_diameter
        )

        # Dessiner le fond global
        painter.setBrush(QColor(50, 50, 50, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)
        
        # Dessiner les zones colorées de tous les boutons qui ont l'action survolée
        if self._hovered_action is not None:
            # Trouver la couleur correspondante (plus légère et transparente)
            action_colors = {
                "copy": QColor(255, 150, 100, 25),
                "term": QColor(100, 255, 150, 25),
                "exec": QColor(100, 150, 255, 25),
            }
            color = action_colors.get(self._hovered_action)
            
            if color is not None:
                angle_step = 360 / len(self.buttons)
                
                # Dessiner une tranche pour chaque bouton ayant cette action
                for i, action in enumerate(self._button_actions):
                    if action == self._hovered_action:
                        # Calculer l'angle de ce bouton
                        button_angle = i * angle_step
                        
                        # Convertir en angle Qt (0° à droite, sens anti-horaire)
                        start_angle = -button_angle - (angle_step / 2)
                        
                        painter.setBrush(color)
                        painter.setPen(Qt.PenStyle.NoPen)
                        # drawPie utilise des "16èmes de degrés"
                        painter.drawPie(circle_rect, int(start_angle * 16), int(angle_step * 16))

        if self.neon_enabled:
            scaled_neon_radius = self._neon_radius * self._scale_factor
            gradient = QRadialGradient(QPointF(center), scaled_neon_radius)
            gradient.setColorAt(0.0, couleur_avec_opacite(self._neon_color, self._neon_opacity))
            gradient.setColorAt(1.0, couleur_avec_opacite(self._neon_color, 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(center), scaled_neon_radius, scaled_neon_radius)

        if self._central_text:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", int(24 * self._scale_factor))
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._central_text)


    def handle_click_outside(self):
        """Gère le clic en dehors du menu (sur le tracker ou au centre)"""
        # Si on est en mode modification ou suppression, revenir au menu de base
        if self.app_instance and (self.app_instance.update_mode or self.app_instance.delete_mode):
            self.app_instance.update_mode = False
            self.app_instance.delete_mode = False
            self.app_instance.refresh_menu()
        else:
            # Sinon, fermer normalement
            self.close_with_animation()

    def animate_open(self):
        # Masquer les badges pendant l'animation
        for badge in self._action_badges.values():
            badge.setVisible(False)
        
        # Masquer la fenêtre tooltip pendant l'animation
        self.tooltip_window.hide()
        
        # Configurer le tracker pour qu'il ferme ce menu quand on clique dessus
        if self.tracker:
            self.tracker.on_click_callback = self.handle_click_outside
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)  # Réduit de 350ms à 250ms
        self.anim.setStartValue(0.1)  # Partir de 10% de la taille, pas 0
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def update_scale(value):
            self._scale_factor = value
            self._apply_scale()
        
        self.anim.valueChanged.connect(update_scale)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()
    
    def _apply_scale(self):
        """Trigger un repaint avec le nouveau scale factor"""
        # Le scale sera appliqué dans paintEvent via une transformation
        # On met aussi à jour la position/taille des boutons
        if self._scale_factor > 0:
            for i, btn in enumerate(self.buttons):
                # Repositionner et redimensionner chaque bouton selon le scale
                angle_step = 360 / len(self.buttons)
                angle = math.radians(i * angle_step)
                center_offset = self.widget_size // 2
                
                # Position originale
                orig_bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
                orig_by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
                
                # Appliquer le scale depuis le centre
                scaled_bx = center_offset + (orig_bx - center_offset) * self._scale_factor
                scaled_by = center_offset + (orig_by - center_offset) * self._scale_factor
                scaled_size = int(self.btn_size * self._scale_factor)
                
                btn.move(int(scaled_bx), int(scaled_by))
                btn.setFixedSize(scaled_size, scaled_size)
                
                # Adapter la taille de l'icône selon le type
                label = self._button_labels[i] if i < len(self._button_labels) else ""
                if "/" in label:
                    # Image - légèrement plus petit pour voir le hover
                    btn.setIconSize(QSize(int(48 * self._scale_factor), int(48 * self._scale_factor)))
                else:
                    # Emoji ou texte - taille d'icône standard
                    btn.setIconSize(QSize(int(32 * self._scale_factor), int(32 * self._scale_factor)))
                
                # Mettre à jour le style avec le border-radius scalé
                if label in ["➖", "✏️", "➕"]:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border-radius: {int((self.btn_size // 2) * self._scale_factor)}px;
                            border: none;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 100);
                        }}
                    """)
                elif "/" in label:
                    # Boutons avec images - pas de padding
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border-radius: {int((self.btn_size // 2) * self._scale_factor)}px;
                            border: none;
                            padding: 0px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 30);
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 10);
                            border-radius: {int((self.btn_size // 2) * self._scale_factor)}px;
                            border: none;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 100);
                        }}
                    """)
        
        self.update()

    def on_animation_finished(self):
        self.reveal_buttons()
        # CRITIQUE: Réactiver le mouse tracking après l'animation
        self.setMouseTracking(True)
        # Positionner la fenêtre tooltip après l'animation
        self._update_tooltip_position()
    
    def close_with_animation(self):
        self.neon_enabled = False
        
        # Masquer les badges pendant l'animation
        for badge in self._action_badges.values():
            badge.setVisible(False)
        
        # Masquer la fenêtre tooltip
        self.tooltip_window.hide()
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.1)  # Finir à 10% de la taille, pas 0
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        
        def update_scale(value):
            self._scale_factor = value
            self._apply_scale()
        
        self.anim.valueChanged.connect(update_scale)
        self.anim.finished.connect(self._on_close_finished)
        self.anim.start()
    
    def _on_close_finished(self):
        """Appelé quand l'animation de fermeture est terminée"""
        # Fermer la fenêtre tooltip
        self.tooltip_window.close()
        if self.tracker:
            self.tracker.close()
        self.close()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = None
        self.current_popup = None
        self.actions_map_sub = {}
        self.buttons_sub = []
        self.update_mode = False
        self.delete_mode = False
        
        # Créer une fenêtre tooltip pour l'application (utilisée dans les dialogues)
        self.tooltip_window = TooltipWindow()
        self._dialog_emoji_labels = []
        self._dialog_help_label = None
        self._dialog_slider = None

    def eventFilter(self, watched, event):
        """Gère les événements de hover et de clic sur les widgets du dialogue"""
        if event.type() == QEvent.Type.Enter:
            # Vérifier les icônes d'action (avec tooltip_text)
            if watched in self._dialog_emoji_labels:
                tooltip_text = watched.property("tooltip_text")
                if tooltip_text and self._dialog_help_label:
                    self._dialog_help_label.setText(tooltip_text)
            # Vérifier les autres widgets (avec help_text)
            else:
                help_text = watched.property("help_text")
                if help_text and self._dialog_help_label:
                    self._dialog_help_label.setText(help_text)
        elif event.type() == QEvent.Type.Leave:
            # Vider le label d'aide
            if self._dialog_help_label:
                self._dialog_help_label.setText("")
        elif event.type() == QEvent.Type.MouseButtonPress:
            # Gérer les clics sur les emojis pour changer le slider
            if watched in self._dialog_emoji_labels and self._dialog_slider:
                slider_value = watched.property("slider_value")
                if slider_value is not None:
                    self._dialog_slider.setValue(slider_value)
        
        return super().eventFilter(watched, event)

    def get_action_from_json(self, alias):
        """Lit l'action d'un clip depuis le fichier JSON"""
        try:
            if os.path.exists(CLIP_NOTES_FILE_JSON):
                with open(CLIP_NOTES_FILE_JSON, 'r', encoding='utf-8') as f:
                    clips = json.load(f)
                    for clip in clips:
                        if clip.get('alias') == alias:
                            action = clip.get('action', 'copy')
                            action_to_slider = {
                                'copy': 0,
                                'term': 1,
                                'exec': 2
                            }
                            return action_to_slider.get(action, 0)
        except Exception as e:
            print(f"Erreur lecture JSON: {e}")
        return 0

    def refresh_menu(self):
        """Rafraîchit le menu en mettant à jour les boutons existants"""
        if not self.current_popup:
            return
        
        # Réinitialiser le state
        self.current_popup.set_central_text("")
        self.current_popup.set_neon_color("cyan")
        # ===== NÉON BLEU MENU PRINCIPAL =====
        # Pour activer le néon bleu clignotant sur le menu principal :
        self.current_popup.toggle_neon(NEON_PRINCIPAL)
        self.current_popup.timer.start(80)  # 100ms = clignotement lent (50ms = rapide)
        # Pour désactiver, changez True en False et commentez la ligne timer.start()
        # ====================================
        
        # Reconstruire buttons_sub depuis actions_map_sub avec tri
        self.buttons_sub = []
        
        # Séparer les boutons spéciaux des autres
        special_buttons = ["➖", "✏️", "➕"]
        clips_to_sort = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Trier seulement les clips (pas les boutons spéciaux)
        sorted_clips = sort_actions_map(clips_to_sort)
        
        # Ajouter d'abord les boutons spéciaux dans l'ordre fixe
        for name in special_buttons:
            if name in self.actions_map_sub:
                action_data, value, action = self.actions_map_sub[name]
                tooltip = value.replace(r'\n', '\n')
                self.buttons_sub.append((name, self.make_handler_sub(name, value, self._x, self._y), tooltip, action))
        
        # Puis ajouter les clips triés
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append((name, self.make_handler_sub(name, value, self._x, self._y), tooltip, action))
        
        # Mettre à jour les boutons du menu existant
        self.current_popup.update_buttons(self.buttons_sub)
        
        # CRITIQUE: Forcer le mouse tracking après le refresh
        self.current_popup.setMouseTracking(True)

    def update_clip(self, x, y, slider_value=0):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode modification
        self.update_mode = True
        
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in ["➖", "✏️", "➕"]}
        
        # Trier les clips
        sorted_clips = sort_actions_map(clips_only)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            # Lire l'action depuis le JSON pour ce clip
            clip_slider_value = self.get_action_from_json(name)
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_edit(name, value, x, y, clip_slider_value),
                    tooltip,
                    action
                )
            )
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("✏️")
            self.current_popup.set_neon_color("jaune")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)

    def make_handler_edit(self, name, value, x, y, slider_value):
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            self.edit_clip(name, value, x, y, slider_value)
        return handler

    def delete_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode suppression
        self.delete_mode = True
        
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in ["➖", "✏️", "➕"]}
        
        # Trier les clips
        sorted_clips = sort_actions_map(clips_only)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_delete(name, value, x, y),
                    tooltip,
                    action
                )
            )
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("➖")
            self.current_popup.set_neon_color("rouge")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)

    def make_handler_delete(self, name, value, x, y):
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            
            self.show_delete_confirmation(name, value, x, y)
        return handler

    def show_delete_confirmation(self, name, value, x, y):
        """Affiche une fenêtre de confirmation pour la suppression"""
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("➖ Supprimer")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Appliquer une palette sombre au dialogue
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
        dialog.setPalette(palette)
        
        dialog.setFixedSize(350, 180)
        
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x - dialog.width() // 2, y - dialog.height() // 2)

        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        message_label = QLabel(f"Voulez-vous vraiment supprimer :\n\n{name}")
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: white; font-size: 14px;")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(32)
        cancel_button.clicked.connect(dialog.reject)
        
        delete_button = QPushButton("Supprimer")
        delete_button.setFixedHeight(32)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 70, 70, 150);
                border: 1px solid rgba(255, 100, 100, 200);
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 200);
            }
        """)
        
        def confirm_delete():
            self.actions_map_sub.pop(name, None)
            delete_from_json(CLIP_NOTES_FILE_JSON, name)
            # Supprimer l'ancien thumbnail s'il existe
            if os.path.exists(name):
                os.remove(name)
            dialog.accept()
            # Rester en mode suppression au lieu de revenir au menu principal
            self.delete_clip(x, y)
        
        delete_button.clicked.connect(confirm_delete)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(delete_button)
        layout.addLayout(buttons_layout)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        dialog.exec()
        
        # CRITIQUE: Réactiver le mouse tracking du menu radial après fermeture du dialogue
        if self.current_popup:
            self.current_popup.setMouseTracking(True)

    def make_handler_sub(self, name, value, x, y):
        def handler_sub():
            if name in self.actions_map_sub:
                func_data = self.actions_map_sub[name][0]
                if isinstance(func_data, tuple) and len(func_data) == 3:
                    func, args, kwargs = func_data
                    func(*args, **kwargs)
                    if name not in ["➖", "✏️", "➕"]:
                        # Récupérer l'action et générer le message
                        action = self.actions_map_sub[name][2]
                        if action == "copy":
                            message = f'"{value}" copié'
                        elif action == "term":
                            message = f'"{value}" exécuté dans un terminal'
                        elif action == "exec":
                            message = f'"{value}" lancé'
                        else:
                            message = None
                        
                        # Afficher le message et fermer après 1 seconde
                        if message and self.current_popup:
                            self.current_popup.tooltip_window.show_message(message, 1000)
                            self.current_popup._update_tooltip_position()
                            # Fermer après 1 seconde
                            QTimer.singleShot(1000, self._close_popup)
                        else:
                            # Fermer immédiatement si pas de message
                            self._close_popup()
                else:
                    print(f"Aucune fonction associée à '{name}'")
        return handler_sub
    
    def _close_popup(self):
        """Méthode helper pour fermer le popup"""
        if self.tracker:
            self.tracker.close()
        if self.current_popup:
            self.current_popup.close()

    def _create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
                           initial_slider_value=0, placeholder="", on_submit_callback=None):
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(350)
        dialog.setWindowFlags(Qt.WindowType.Dialog)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Appliquer une palette sombre au dialogue
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
        dialog.setPalette(palette)
        
        dialog.resize(300, 400)
        
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x, y)

        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        layout.addLayout(top_bar)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Émoji - Image - Texte")
        name_input.setMinimumHeight(30)
        name_input.setText(initial_name)
        name_input.setProperty("help_text", "Alias")
        name_input.installEventFilter(self)

        # Layout horizontal pour les boutons emoji et image
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        
        emoji_button = QPushButton("😀 Emoji")
        emoji_button.setFixedHeight(30)
        emoji_button.setProperty("help_text", "Attribuer un emoji")
        emoji_button.installEventFilter(self)
        
        image_button = QPushButton("🖼️ Image")
        image_button.setFixedHeight(30)
        image_button.setProperty("help_text", "Attribuer une image")
        image_button.installEventFilter(self)
        
        buttons_row.addWidget(emoji_button)
        buttons_row.addWidget(image_button)

        slider_container = QWidget()
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(2)

        emoji_labels_layout = QHBoxLayout()
        emoji_labels_layout.setContentsMargins(8, 0, 8, 0)
        emoji_labels_layout.setSpacing(0)
        emoji_labels = ["✂️", "💻", "🚀"]
        emoji_tooltips = ["Copier", "Exécuter dans un terminal", "Exécuter"]
        
        # Stocker les labels pour l'event filter
        self._dialog_emoji_labels = []
        self._dialog_slider = None  # Référence au slider pour les clics sur emojis
        
        for i, emoji in enumerate(emoji_labels):
            if i > 0:
                emoji_labels_layout.addStretch()
            label = QLabel(emoji)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 20px;")
            label.setCursor(Qt.CursorShape.PointingHandCursor)  # Curseur pointeur
            
            # Stocker le tooltip et la valeur du slider pour ce label
            label.setProperty("tooltip_text", emoji_tooltips[i])
            label.setProperty("slider_value", i)  # 0 pour ✂️, 1 pour 💻, 2 pour 🚀
            
            # Installer l'event filter pour détecter le hover et les clics
            label.installEventFilter(self)
            label.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            self._dialog_emoji_labels.append(label)
            
            emoji_labels_layout.addWidget(label)
            if i < len(emoji_labels) - 1:
                emoji_labels_layout.addStretch()
        
        slider_layout.addLayout(emoji_labels_layout)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(2)
        slider.setValue(initial_slider_value)  # INITIALISER avec la bonne valeur
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setPageStep(1)
        slider.setProperty("help_text", "Associer une action")
        slider.installEventFilter(self)
        self._dialog_slider = slider  # Stocker pour les clics sur emojis
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #555;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #888;
                width: 16px;
                margin: -6px 0;
                border-radius: 9px;
            }
        """)
        
        # Layout pour réduire la largeur du slider
        slider_h_layout = QHBoxLayout()
        slider_h_layout.setContentsMargins(8, 0, 8, 0)
        slider_h_layout.addWidget(slider)
        slider_layout.addLayout(slider_h_layout)

        value_input = QTextEdit()
        value_input.setMinimumHeight(80)
        value_input.setProperty("help_text", "Valeur")
        value_input.installEventFilter(self)
        if placeholder:
            value_input.setPlaceholderText(placeholder)
        if initial_value:
            value_input.setText(initial_value.replace(r'\n', '\n'))

        submit_button = QPushButton(button_text)
        submit_button.setFixedHeight(32)
        
        # Label d'aide pour afficher les descriptions des icônes
        help_label = QLabel("")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setStyleSheet("color: white; font-size: 12px; padding: 4px; font-weight: bold;")
        help_label.setMinimumHeight(20)
        self._dialog_help_label = help_label  # Stocker pour l'event filter

        layout.addWidget(name_input)
        layout.addLayout(buttons_row)
        layout.addWidget(slider_container)
        layout.addWidget(value_input)
        layout.addWidget(submit_button)
        layout.addWidget(help_label)

        def open_image_selector():
            """Ouvre un sélecteur de fichier pour choisir une image"""
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Choisir une image",
                "",
                "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Tous les fichiers (*)"
            )
            
            if file_path:
                # Créer une miniature
                thumbnail_path = create_thumbnail(file_path)
                if thumbnail_path:
                    # Mettre le chemin de la miniature dans le champ nom
                    name_input.setText(thumbnail_path)
                    print(f"Miniature créée: {thumbnail_path}")
                else:
                    print("Erreur lors de la création de la miniature")

        def open_emoji_selector():
            path = EMOJIS_FILE
            if not os.path.exists(path):
                print(f"Fichier introuvable : {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                emojis = [line.strip() for line in f if line.strip()]
            selector = EmojiSelector(emojis, parent=dialog)

            def on_emoji_selected(emoji):
                cursor_pos = name_input.cursorPosition()
                current_text = name_input.text()
                new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
                name_input.setFocus()
                name_input.setText(new_text)
                name_input.setCursorPosition(cursor_pos + len(emoji))
                selector.accept()

            selector.emoji_selected = on_emoji_selected
            selector.exec()

        emoji_button.clicked.connect(open_emoji_selector)
        image_button.clicked.connect(open_image_selector)
        
        if on_submit_callback:
            submit_button.clicked.connect(
                lambda: on_submit_callback(dialog, name_input, value_input, slider)
            )

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        name_input.setFocus()
        dialog.exec()
        
        # CRITIQUE: Réactiver le mouse tracking du menu radial après fermeture du dialogue
        if self.current_popup:
            self.current_popup.setMouseTracking(True)
        
        return dialog

    def new_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input, slider):
            name = name_input.text().strip()
            value = value_input.toPlainText().strip().replace('\n', '\\n')
            
            if name and value:
                slider_value = slider.value()
                action_map = {
                    0: "copy",
                    1: "term",
                    2: "exec"
                }
                action = action_map.get(slider_value, "copy")
                
                # Format: [(fonction, [args], {}), value, action]
                if action == "copy":
                    self.actions_map_sub[name] = [(paperclip_copy, [value], {}), value, action]
                elif action == "term":
                    self.actions_map_sub[name] = [(execute_terminal, [value], {}), value, action]
                elif action == "exec":
                    self.actions_map_sub[name] = [(execute_command, [value], {}), value, action]
                
                append_to_actions_file(CLIP_NOTES_FILE, name, value)
                append_to_actions_file_json(CLIP_NOTES_FILE_JSON, name, value, action)
                
                dialog.accept()
                self.delete_mode = False
                
                # Au lieu de relaunch_window, on rafraîchit le menu
                self.refresh_menu()
            else:
                print("Les deux champs doivent être remplis")
        
        self._create_clip_dialog(
            title="➕ Ajouter",
            button_text="Ajouter",
            x=x, y=y,
            placeholder="Contenu (ex: lien ou texte)",
            on_submit_callback=handle_submit
        )

    def edit_clip(self, name, value, x, y, slider_value):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input, slider):
            new_name = name_input.text().strip()
            new_value = value_input.toPlainText().strip().replace('\n', '\\n')

            if new_name and new_value:
                slider_value = slider.value()
                action_map = {
                    0: "copy",
                    1: "term",
                    2: "exec"
                }
                action = action_map.get(slider_value, "copy")
                old_name = name
                if new_name != old_name:
                    self.actions_map_sub.pop(old_name, None)
                    # Supprimer l'ancien alias du JSON
                    delete_from_json(CLIP_NOTES_FILE_JSON, old_name)
                    # Supprimer l'ancien thumbnail s'il existe
                    if os.path.exists(old_name):
                        os.remove(old_name)
                
                # Format: [(fonction, [args], {}), value, action]
                if action == "copy":
                    self.actions_map_sub[new_name] = [(paperclip_copy, [new_value], {}), new_value, action]
                elif action == "term":
                    self.actions_map_sub[new_name] = [(execute_terminal, [new_value], {}), new_value, action]
                elif action == "exec":
                    self.actions_map_sub[new_name] = [(execute_command, [new_value], {}), new_value, action]
                
                replace_or_append_json(CLIP_NOTES_FILE_JSON, new_name, new_value, action)
                dialog.accept()
                
                # Rester en mode modification au lieu de revenir au menu principal
                self.update_clip(x, y)
            else:
                print("Les deux champs doivent être remplis")

        self._create_clip_dialog(
            title="✏️ Modifier",
            button_text="Modifier",
            x=x, y=y,
            initial_name=name,
            initial_value=value,
            initial_slider_value=slider_value,  # PASSER la valeur du slider
            on_submit_callback=handle_submit
        )

    def show_window_at(self, x, y, wm_name):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Stocker les coordonnées pour refresh_menu
        self._x = x
        self._y = y
        
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except RuntimeError:
            pass
        self.current_popup = None

        self.buttons_sub = []
        
        # Définir les tooltips pour les boutons spéciaux
        special_button_tooltips = {
            "➕": "Ajouter",
            "✏️": "Modifier",
            "➖": "Supprimer"
        }
        
        self.actions_map_sub = {
            "➕": [(self.new_clip,    [x,y], {}), special_button_tooltips["➕"], None],
            "✏️": [(self.update_clip, [x,y], {}), special_button_tooltips["✏️"], None],
            "➖": [(self.delete_clip, [x,y], {}), special_button_tooltips["➖"], None],
        }
        populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub, execute_command)

        # Séparer les boutons spéciaux des autres
        special_buttons = ["➖", "✏️", "➕"]
        clips_to_sort = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Trier seulement les clips (pas les boutons spéciaux)
        sorted_clips = sort_actions_map(clips_to_sort)
        
        # Ajouter d'abord les boutons spéciaux dans l'ordre fixe
        for name in special_buttons:
            if name in self.actions_map_sub:
                action_data, value, action = self.actions_map_sub[name]
                tooltip = value.replace(r'\n', '\n')
                self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y), tooltip, action))
        
        # Puis ajouter les clips triés
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y), tooltip, action))
        
        self.current_popup = RadialMenu(x, y, self.buttons_sub, sub=True, tracker=self.tracker, app_instance=self)
        self.current_popup.show()
        self.current_popup.animate_open()
        
        # ===== NÉON BLEU MENU PRINCIPAL =====
        # Activer le néon bleu clignotant dès l'ouverture
        self.current_popup.toggle_neon(NEON_PRINCIPAL)
        self.current_popup.timer.start(80)  # 100ms = clignotement lent
        # ====================================

if __name__ == "__main__":
    create_lock_file()
    
    def cleanup_handler(sig, frame):
        remove_lock_file()
        QApplication.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    app = QApplication(sys.argv)
    
    global tracker
    tracker = CursorTracker()
    tracker.show()
    #     # AJOUTER LA FENÊTRE DE CALIBRATION
    # calibration_window = CalibrationWindow(tracker)
    # calibration_window.show()
    
    import time
    max_wait = 0.3
    elapsed = 0.0
    while (tracker.last_x == 0 and tracker.last_y == 0) and elapsed < max_wait:
        QApplication.processEvents()
        time.sleep(0.1)
        elapsed += 0.1
    
    tracker.update_pos()
    x, y = tracker.last_x, tracker.last_y
    
    QApplication.processEvents()
    
    main_app = App()
    main_app.tracker = tracker
    # Fenêtre de calibration du menu Radial
    # calibration_window = CalibrationWindow(tracker, main_app)
    # calibration_window.show()
    main_app.show_window_at(x, y, "")

    try:
        sys.exit(app.exec())
    finally:
        remove_lock_file()