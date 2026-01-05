import sys
import math
import subprocess
import signal
import os
import getpass
import json
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QPainter, QColor, QIcon, QRadialGradient, QFont, QPalette, QPixmap, QPainterPath
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QRect, QEasingCurve, QVariantAnimation, QEvent, QPointF
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QHBoxLayout, QSlider
from PyQt6.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextEdit, QToolTip, QLabel, QFileDialog, QComboBox, QCheckBox, QColorDialog, QScrollArea
from PIL import Image, ImageDraw
import hashlib

from utils import *                
from ui import EmojiSelector

# 🗑️ 📝
# Constantes de configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# CLIP_NOTES_FILE = os.path.join(SCRIPT_DIR, "clip_notes.txt")
CLIP_NOTES_FILE_JSON = os.path.join(SCRIPT_DIR, "clip_notes.json")
EMOJIS_FILE = os.path.join(SCRIPT_DIR, "emojis.txt")
THUMBNAILS_DIR = os.path.join(SCRIPT_DIR, "thumbnails")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
STORED_CLIPS_FILE = os.path.join(SCRIPT_DIR, "stored_clips.json")

NEON_PRINCIPAL=False
CENTRAL_NEON = False  # Afficher le néon cosmétique au centre
ZONE_BASIC_OPACITY = 15
ZONE_HOVER_OPACITY = 45
SHOW_CENTRAL_ICON = True  # Afficher l'icône du clip survolé au centre
MENU_OPACITY = 100  # Opacité globale du menu radial (0-100)

SPECIAL_BUTTONS = ["📦", "⚙️", "➖", "✏️", "➕"]

# Palette de couleurs disponibles (RGB)
COLOR_PALETTE = {
    # Rouges
    "Rouge": (255, 0, 0),
    "Rouge clair": (255, 100, 100),
    "Rose": (255, 192, 203),
    "Rose pâle": (255, 200, 200),
    "Rouge foncé": (200, 0, 0),
    
    # Oranges
    "Orange": (255, 150, 100),
    "Orange vif": (255, 100, 0),
    "Orange clair": (255, 200, 150),
    "Pêche": (255, 218, 185),
    
    # Jaunes
    "Jaune": (255, 255, 0),
    "Jaune clair": (255, 255, 150),
    "Jaune pâle": (255, 255, 200),
    "Or": (255, 215, 0),
    
    # Verts
    "Vert": (100, 255, 150),
    "Vert vif": (0, 255, 0),
    "Vert clair": (150, 255, 150),
    "Vert pâle": (200, 255, 200),
    "Vert foncé": (0, 150, 0),
    "Vert menthe": (152, 255, 152),
    
    # Bleus
    "Bleu": (100, 150, 255),
    "Bleu vif": (0, 0, 255),
    "Bleu clair": (150, 200, 255),
    "Bleu pâle": (200, 200, 255),
    "Cyan": (0, 255, 255),
    "Cyan pâle": (200, 255, 255),
    "Bleu foncé": (0, 0, 200),
    
    # Violets
    "Violet": (150, 100, 255),
    "Violet clair": (200, 150, 255),
    "Mauve": (224, 176, 255),
    "Magenta": (255, 0, 255),
    
    # Gris
    "Gris menu": (50, 50, 50),      # Gris par défaut du menu
    "Gris": (150, 150, 150),
    "Gris clair": (200, 200, 200),
    "Gris foncé": (100, 100, 100),
}

# Couleurs des zones par action (RGB)
ACTION_ZONE_COLORS = {
    "copy": (255, 150, 100),  # Orange par défaut
    "term": (100, 255, 150),  # Vert par défaut
    "exec": (100, 150, 255),  # Bleu par défaut
}

# Couleur du fond du menu radial (RGB)
MENU_BACKGROUND_COLOR = (50, 50, 50)

# Couleur du néon cosmétique (RGB)
NEON_COLOR = (0, 255, 255)  # Cyan par défaut

# Vitesse du battement du néon (en millisecondes)
NEON_SPEED = 80  # Plus petit = plus rapide

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
        # PIL ellipse : (left, top, right, bottom) où right et bottom sont INCLUS
        # Pour un cercle parfait de 48 pixels, on utilise (0, 0, 47, 47)
        draw.ellipse((0, 0, size-1, size-1), fill=255)
        
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

def load_config():
    """Charge la configuration depuis le fichier JSON"""
    global CENTRAL_NEON, ZONE_BASIC_OPACITY, ZONE_HOVER_OPACITY, SHOW_CENTRAL_ICON, ACTION_ZONE_COLORS, MENU_OPACITY, MENU_BACKGROUND_COLOR, NEON_COLOR, NEON_SPEED
    
    if not os.path.exists(CONFIG_FILE):
        return
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        CENTRAL_NEON = config.get('central_neon', CENTRAL_NEON)
        ZONE_BASIC_OPACITY = config.get('zone_basic_opacity', ZONE_BASIC_OPACITY)
        ZONE_HOVER_OPACITY = config.get('zone_hover_opacity', ZONE_HOVER_OPACITY)
        SHOW_CENTRAL_ICON = config.get('show_central_icon', SHOW_CENTRAL_ICON)
        MENU_OPACITY = config.get('menu_opacity', MENU_OPACITY)
        NEON_SPEED = config.get('neon_speed', NEON_SPEED)
        
        # Charger la couleur du fond du menu
        menu_bg = config.get('menu_background_color', MENU_BACKGROUND_COLOR)
        MENU_BACKGROUND_COLOR = tuple(menu_bg) if isinstance(menu_bg, list) else menu_bg
        
        # Charger la couleur du néon
        neon_col = config.get('neon_color', NEON_COLOR)
        NEON_COLOR = tuple(neon_col) if isinstance(neon_col, list) else neon_col
        
        # Charger les couleurs et migrer l'ancien format si nécessaire
        loaded_colors = config.get('action_zone_colors', ACTION_ZONE_COLORS)
        ACTION_ZONE_COLORS = {}
        
        for action, color_value in loaded_colors.items():
            if isinstance(color_value, str):
                # Ancien format : nom de couleur -> convertir en RGB
                if color_value in COLOR_PALETTE:
                    ACTION_ZONE_COLORS[action] = COLOR_PALETTE[color_value]
                    print(f"[Config] Migration: {action} '{color_value}' -> {COLOR_PALETTE[color_value]}")
                else:
                    # Couleur inconnue, utiliser la valeur par défaut
                    default_colors = {
                        "copy": (255, 150, 100),
                        "term": (100, 255, 150),
                        "exec": (100, 150, 255)
                    }
                    ACTION_ZONE_COLORS[action] = default_colors.get(action, (255, 255, 255))
            elif isinstance(color_value, list):
                # Nouveau format : liste RGB -> convertir en tuple
                ACTION_ZONE_COLORS[action] = tuple(color_value)
            else:
                # Déjà un tuple
                ACTION_ZONE_COLORS[action] = color_value
        
        print(f"[Config] Configuration chargée: {config}")
    except Exception as e:
        print(f"[Erreur] Impossible de charger la configuration: {e}")

def create_color_icon(rgb_tuple, size=16):
    """Crée une icône carrée de couleur pour les ComboBox"""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(*rgb_tuple))
    return QIcon(pixmap)

def save_config():
    """Sauvegarde la configuration dans le fichier JSON"""
    config = {
        'central_neon': CENTRAL_NEON,
        'zone_basic_opacity': ZONE_BASIC_OPACITY,
        'zone_hover_opacity': ZONE_HOVER_OPACITY,
        'show_central_icon': SHOW_CENTRAL_ICON,
        'action_zone_colors': ACTION_ZONE_COLORS,
        'menu_opacity': MENU_OPACITY,
        'menu_background_color': MENU_BACKGROUND_COLOR,
        'neon_color': NEON_COLOR,
        'neon_speed': NEON_SPEED
    }
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"[Config] Configuration sauvegardée: {config}")
    except Exception as e:
        print(f"[Erreur] Impossible de sauvegarder la configuration: {e}")

# ===== GESTION DES CLIPS STOCKÉS =====

def load_stored_clips():
    """Charge les clips stockés depuis le fichier JSON"""
    if not os.path.exists(STORED_CLIPS_FILE):
        return []
    
    try:
        with open(STORED_CLIPS_FILE, 'r', encoding='utf-8') as f:
            clips = json.load(f)
        print(f"[Stored Clips] {len(clips)} clips chargés")
        return clips
    except Exception as e:
        print(f"[Erreur] Impossible de charger les clips stockés: {e}")
        return []

def save_stored_clips(clips):
    """Sauvegarde les clips stockés dans le fichier JSON"""
    try:
        with open(STORED_CLIPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(clips, f, indent=4, ensure_ascii=False)
        print(f"[Stored Clips] {len(clips)} clips sauvegardés")
    except Exception as e:
        print(f"[Erreur] Impossible de sauvegarder les clips stockés: {e}")

def add_stored_clip(alias, action, string):
    """Ajoute un clip au stockage"""
    clips = load_stored_clips()
    clips.append({
        'alias': alias,
        'action': action,
        'string': string
    })
    save_stored_clips(clips)
    return clips

def remove_stored_clip(alias):
    """Supprime un clip du stockage"""
    clips = load_stored_clips()
    clips = [clip for clip in clips if clip.get('alias') != alias]
    save_stored_clips(clips)
    return clips


# Charger la configuration au démarrage
load_config()

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
        distance_below = menu_radius + 20  # Rayon du menu + marge
        
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
        self._neon_color = NEON_COLOR
        self._widget_opacity = 1.0
        self._scale_factor = 0.1  # Démarrer petit pour l'animation

        self.current_index = 0
        
        # Stocker les couleurs par action pour chaque bouton
        self._button_colors = []  # Liste des couleurs pour chaque bouton
        self._button_actions = []  # Liste des actions pour chaque bouton
        self._button_labels = []  # Liste des labels pour chaque bouton
        self._hovered_action = None  # Action survolée (None, "copy", "term", ou "exec")
        self._hovered_button_index = None  # Index du bouton survolé
        self._central_icon = None  # Pixmap de l'icône centrale à afficher
        self._action_badges = {}  # Dictionnaire des badges globaux par action
        
        # Activer le tracking de la souris pour détecter le hover
        self.setMouseTracking(True)
        
        
        # === NOUVELLE FENÊTRE TOOLTIP ===
        self.tooltip_window = TooltipWindow(parent=self)
        
        # Créer les boutons initiaux
        self._create_buttons(buttons)

    def _create_buttons(self, buttons):
        """Crée les boutons pour le menu radial"""
        # Couleurs par type d'action (utilise directement les RGB)
        action_colors = {
            action: QColor(*rgb, 25)
            for action, rgb in ACTION_ZONE_COLORS.items()
        }
        
        # Tooltips pour les boutons spéciaux
        special_tooltips = {
            "➕": "Ajouter",
            "✏️": "Modifier",
            "➖": "Supprimer",
            "📦": "Stockage"
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
            # Activer le hover tracking pour ce bouton
            btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            
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
            if label in SPECIAL_BUTTONS:
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
            # Trouver l'index du bouton survolé
            if watched in self.buttons and SHOW_CENTRAL_ICON:
                button_index = self.buttons.index(watched)
                self._hovered_button_index = button_index
                
                # Créer l'icône centrale pour ce bouton
                if button_index < len(self._button_labels):
                    label = self._button_labels[button_index]
                    # Créer un pixmap adapté au type de label
                    if "/" in label:
                        # C'est un chemin d'image
                        self._central_icon = image_pixmap(label, 64)
                    elif is_emoji(label):
                        # C'est un emoji
                        self._central_icon = emoji_pixmap(label, 48)
                    else:
                        # C'est du texte simple
                        self._central_icon = text_pixmap(label, 48)
                    self.update()
            
            # Afficher le message de hover dans la fenêtre tooltip
            if watched in self._tooltips:
                tooltip_text = self._tooltips[watched]
                # Afficher dans la fenêtre tooltip en dessous (durée infinie)
                self.tooltip_window.show_message(tooltip_text, 0)
                self._update_tooltip_position()
                
        elif event.type() == QEvent.Type.Leave:
            # Effacer l'icône centrale quand on quitte le bouton
            if watched in self.buttons and SHOW_CENTRAL_ICON:
                self._central_icon = None
                self._hovered_button_index = None
                self.update()
            
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
        # Ne plus modifier le style des boutons - l'opacité n'affecte que le fond maintenant
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
        # Calculer la distance au centre
        center = self.rect().center()
        dx = event.pos().x() - center.x()
        dy = event.pos().y() - center.y()
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Si on clique au centre (distance < 30), revenir au menu principal
        if distance < 30:
            self.handle_click_outside()
            return
        
        if not any(btn.geometry().contains(event.pos()) for btn in self.buttons):
            # Masquer tous les badges
            for badge in self._action_badges.values():
                badge.setVisible(False)
            # Masquer la fenêtre tooltip
            self.tooltip_window.hide()
            self.handle_click_outside()
    
    def leaveEvent(self, event):
        """Efface l'icône centrale quand la souris quitte le widget"""
        if SHOW_CENTRAL_ICON and self._central_icon is not None:
            self._central_icon = None
            self._hovered_button_index = None
            self.update()
    
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
            if self._hovered_action is not None or self._central_icon is not None:
                self._hovered_action = None
                self._hovered_button_index = None
                self._central_icon = None
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
        
        # Ne pas appliquer l'opacité globalement - seulement au fond
        # painter.setOpacity(self._widget_opacity)  # SUPPRIMÉ
        
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

        # Dessiner le fond global avec opacité contrôlée par MENU_OPACITY
        # _widget_opacity va de 0.0 à 1.0, on le convertit en alpha 0-255
        background_alpha = int(255 * self._widget_opacity)
        painter.setBrush(QColor(*MENU_BACKGROUND_COLOR, background_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)
        
        # Dessiner les zones colorées pour TOUS les boutons avec des actions
        # Toutes les zones sont toujours visibles avec une opacité de base légère
        action_colors_base = {
            action: QColor(*rgb, ZONE_BASIC_OPACITY)
            for action, rgb in ACTION_ZONE_COLORS.items()
        }

        action_colors_hover = {
            action: QColor(*rgb, ZONE_HOVER_OPACITY)
            for action, rgb in ACTION_ZONE_COLORS.items()
        }
        
        angle_step = 360 / len(self.buttons)
        
        # Dessiner toutes les zones
        for i, action in enumerate(self._button_actions):
            if action in action_colors_base:
                # Choisir la couleur selon si c'est survolé ou non
                if action == self._hovered_action:
                    color = action_colors_hover[action]
                else:
                    color = action_colors_base[action]
                
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

        if self._central_icon:
            # Afficher l'icône centrale du bouton survolé
            icon_size = int(64 * self._scale_factor)  # Taille scalée
            icon_x = center.x() - icon_size // 2
            icon_y = center.y() - icon_size // 2
            
            # Créer un pixmap scalé
            scaled_icon = self._central_icon.scaled(
                icon_size, 
                icon_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(int(icon_x), int(icon_y), scaled_icon)
        elif self._central_text:
            # Afficher le texte central (mode édition/suppression)
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", int(24 * self._scale_factor))
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._central_text)


    def handle_click_outside(self):
        """Gère le clic en dehors du menu (sur le tracker ou au centre)"""
        # Si on est en mode modification, suppression ou stockage, revenir au menu de base
        if self.app_instance and (self.app_instance.update_mode or self.app_instance.delete_mode or self.app_instance.store_mode):
            self.app_instance.update_mode = False
            self.app_instance.delete_mode = False
            self.app_instance.store_mode = False
            self.app_instance.refresh_menu()
        # Si on est dans le menu de sélection 📦 (2 boutons seulement)
        elif len(self.buttons) == 2:
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
                if label in SPECIAL_BUTTONS:
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
        self.store_mode = False
        
        # Créer une fenêtre tooltip pour l'application (utilisée dans les dialogues)
        self.tooltip_window = TooltipWindow()
        self._dialog_emoji_labels = []
        self._dialog_help_label = None
        self._dialog_slider = None
        self._dialog_image_preview = None  # Label pour l'aperçu de l'image
        self._dialog_temp_image_path = None  # Chemin temporaire de l'image sélectionnée
        self._dialog_remove_image_button = None  # Bouton pour supprimer l'image

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
        self.current_popup.set_neon_color(NEON_COLOR)
        # ===== NÉON BLEU MENU PRINCIPAL =====
        # Pour activer le néon bleu clignotant sur le menu principal :
        self.current_popup.toggle_neon(CENTRAL_NEON)
        # self.current_popup.timer.start(80)  # 100ms = clignotement lent (50ms = rapide)
        # Pour désactiver, changez True en False et commentez la ligne timer.start()
        # ====================================
        
        # Reconstruire buttons_sub depuis actions_map_sub avec tri
        self.buttons_sub = []
        
        # Séparer les boutons spéciaux des autres
        special_buttons = SPECIAL_BUTTONS
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
        
        # Réappliquer l'opacité configurée
        self.current_popup.set_widget_opacity(MENU_OPACITY / 100.0)
        
        # Réappliquer le néon central configuré
        self.current_popup.toggle_neon(CENTRAL_NEON)
        if CENTRAL_NEON:
            # Redémarrer le timer avec la nouvelle vitesse
            self.current_popup.timer.stop()
            self.current_popup.timer.start(NEON_SPEED)
        
        # CRITIQUE: Forcer le mouse tracking après le refresh
        self.current_popup.setMouseTracking(True)

    def update_clip(self, x, y, slider_value=0):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode modification
        self.update_mode = True
        
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in SPECIAL_BUTTONS}
        
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
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in SPECIAL_BUTTONS}
        
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
                    if name not in SPECIAL_BUTTONS:
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
        
        # Stocker le nom initial pour la comparaison
        initial_name_stored = initial_name
        
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
        
        # Conteneur pour l'aperçu de l'image avec bouton de suppression
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        image_container_layout.setSpacing(4)
        
        # Aperçu de l'image (caché par défaut)
        image_preview = QLabel()
        image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_preview.setFixedSize(100, 100)
        image_preview.setStyleSheet("""
            QLabel {
                border: 2px solid rgba(255, 255, 255, 30);
                border-radius: 50px;
                background-color: rgba(0, 0, 0, 50);
            }
        """)
        image_preview.setVisible(False)
        self._dialog_image_preview = image_preview
        
        # Bouton de suppression de l'image
        remove_image_button = QPushButton("❌")
        remove_image_button.setFixedSize(30, 30)
        remove_image_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 70, 70, 100);
                border: 1px solid rgba(255, 100, 100, 150);
                border-radius: 15px;
                padding: 0px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 150);
            }
        """)
        remove_image_button.setVisible(False)
        remove_image_button.setProperty("help_text", "Supprimer l'image")
        remove_image_button.installEventFilter(self)
        self._dialog_remove_image_button = remove_image_button
        
        def remove_image():
            """Supprime l'aperçu de l'image et vide le champ nom"""
            self._dialog_temp_image_path = None
            if self._dialog_image_preview:
                self._dialog_image_preview.setVisible(False)
                self._dialog_image_preview.clear()
            if self._dialog_remove_image_button:
                self._dialog_remove_image_button.setVisible(False)
            name_input.clear()
        
        remove_image_button.clicked.connect(remove_image)
        
        # Détecter les modifications manuelles du champ nom pour cacher l'image
        def on_name_changed(text):
            """Cache l'aperçu si l'utilisateur modifie le texte manuellement"""
            # Si on a une image temporaire et que le texte ne correspond plus au nom attendu
            if self._dialog_temp_image_path:
                expected_name = os.path.splitext(os.path.basename(self._dialog_temp_image_path))[0]
                if text != expected_name:
                    # L'utilisateur a modifié le texte, effacer l'aperçu
                    self._dialog_temp_image_path = None
                    if self._dialog_image_preview:
                        self._dialog_image_preview.setVisible(False)
                        self._dialog_image_preview.clear()
                    if self._dialog_remove_image_button:
                        self._dialog_remove_image_button.setVisible(False)
            # Si on édite une image existante et que le texte change
            elif initial_name_stored and "/" in initial_name_stored and text != initial_name_stored:
                # L'utilisateur a modifié le chemin, effacer l'aperçu
                if self._dialog_image_preview:
                    self._dialog_image_preview.setVisible(False)
                    self._dialog_image_preview.clear()
                if self._dialog_remove_image_button:
                    self._dialog_remove_image_button.setVisible(False)
        
        name_input.textChanged.connect(on_name_changed)
        
        image_container_layout.addWidget(image_preview, alignment=Qt.AlignmentFlag.AlignCenter)
        image_container_layout.addWidget(remove_image_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Si on édite un clip avec une image existante, l'afficher
        if initial_name and "/" in initial_name and os.path.exists(initial_name):
            pixmap = QPixmap(initial_name)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    100, 100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                rounded = QPixmap(100, 100)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 100, 100)
                painter.setClipPath(path)
                x_offset = (100 - scaled_pixmap.width()) // 2
                y_offset = (100 - scaled_pixmap.height()) // 2
                painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
                painter.end()
                image_preview.setPixmap(rounded)
                image_preview.setVisible(True)
                remove_image_button.setVisible(True)
        
        layout.addWidget(image_container)
        
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
                # Stocker le chemin temporairement (ne pas créer le thumbnail maintenant)
                self._dialog_temp_image_path = file_path
                
                # Mettre seulement le nom de fichier (sans chemin) dans name_input
                file_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(file_name)[0]
                name_input.setText(name_without_ext)
                
                # Afficher l'aperçu de l'image
                if self._dialog_image_preview:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        # Redimensionner en gardant les proportions
                        scaled_pixmap = pixmap.scaled(
                            100, 100,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        
                        # Créer un pixmap rond
                        rounded = QPixmap(100, 100)
                        rounded.fill(Qt.GlobalColor.transparent)
                        painter = QPainter(rounded)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        
                        # Dessiner un cercle pour le masque
                        path = QPainterPath()
                        path.addEllipse(0, 0, 100, 100)
                        painter.setClipPath(path)
                        
                        # Centrer l'image
                        x = (100 - scaled_pixmap.width()) // 2
                        y = (100 - scaled_pixmap.height()) // 2
                        painter.drawPixmap(x, y, scaled_pixmap)
                        painter.end()
                        
                        self._dialog_image_preview.setPixmap(rounded)
                        self._dialog_image_preview.setVisible(True)
                        
                        # Rendre visible le bouton de suppression
                        if self._dialog_remove_image_button:
                            self._dialog_remove_image_button.setVisible(True)
                        
                        print(f"Image sélectionnée: {file_path}")
                    else:
                        print("Erreur lors du chargement de l'image")

        def open_emoji_selector():
            path = EMOJIS_FILE
            if not os.path.exists(path):
                print(f"Fichier introuvable : {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                emojis = [line.strip() for line in f if line.strip()]
            selector = EmojiSelector(emojis, parent=dialog)

            def on_emoji_selected(emoji):
                # Remplacer tout le texte par l'emoji sélectionné
                name_input.setFocus()
                name_input.setText(emoji)
                name_input.setCursorPosition(len(emoji))
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
        
        # CRITIQUE: Nettoyer les variables du dialogue
        self._dialog_temp_image_path = None
        self._dialog_image_preview = None
        self._dialog_remove_image_button = None
        
        # CRITIQUE: Réactiver le mouse tracking du menu radial après fermeture du dialogue
        if self.current_popup:
            self.current_popup.setMouseTracking(True)
        
        return dialog

    
    # ===== MODE STOCKAGE DE CLIPS =====
    
    def store_clip_mode(self, x, y):
        """Active le mode stockage de clips"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode stockage
        self.store_mode = True
        
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in SPECIAL_BUTTONS}
        
        # Trier les clips
        sorted_clips = sort_actions_map(clips_only)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_store(name, value, action, x, y),
                    tooltip,
                    action
                )
            )
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("💾")
            self.current_popup.set_neon_color("vert")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)
    
    def make_handler_store(self, name, value, action, x, y):
        """Crée un handler pour stocker un clip"""
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            
            # Stocker le clip
            add_stored_clip(name, action if action else "copy", value)
            
            # Supprimer le clip du menu radial
            self.actions_map_sub.pop(name, None)
            delete_from_json(CLIP_NOTES_FILE_JSON, name)
            
            # NE PAS supprimer le thumbnail - on en a besoin pour l'affichage dans le stockage
            # if os.path.exists(name):
            #     os.remove(name)
            
            # Afficher une confirmation brève
            if self.current_popup:
                self.current_popup.set_central_text("✓")
                QTimer.singleShot(500, lambda: self.current_popup.set_central_text("💾"))
            
            # Rester en mode stockage et rafraîchir
            self.store_clip_mode(x, y)
            
        return handler
    
    def show_storage_menu(self, x, y):
        """Affiche un menu pour choisir entre stocker un clip ou voir les clips stockés"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Remplacer temporairement les boutons par les 2 options
        self.buttons_sub = [
            ("📋", lambda: self.show_stored_clips_dialog(x, y), "Clips stockés", None),
            ("💾", lambda: self.store_clip_mode(x, y), "Stocker des clips", None)
        ]
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("📦")
    
    def show_stored_clips_dialog(self, x, y):
        """Affiche la fenêtre de dialogue avec la liste des clips stockés"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Charger les clips stockés
        stored_clips = load_stored_clips()
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("📋 Clips stockés")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Appliquer une palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        dialog.setPalette(palette)
        
        dialog.setFixedSize(750, 500)
        dialog.move(x - 375, y - 200)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Titre
        title_label = QLabel("📋 Clips stockés")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title_label)
        
        # Zone de défilement pour la liste
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: rgba(35, 35, 35, 255);
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 6px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(5)
        
        if not stored_clips:
            empty_label = QLabel("Aucun clip stocké")
            empty_label.setStyleSheet("color: gray; padding: 20px; font-style: italic;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(empty_label)
        else:
            # En-tête
            header_layout = QHBoxLayout()
            
            alias_header = QLabel("Alias")
            alias_header.setStyleSheet("font-weight: bold; color: black;")
            alias_header.setFixedWidth(50)
            
            action_header = QLabel("Action")
            action_header.setStyleSheet("font-weight: bold; color: black;")
            action_header.setFixedWidth(80)
            
            value_header = QLabel("Valeur")
            value_header.setStyleSheet("font-weight: bold; color: black;")
            
            # header_layout.addWidget(icon_header)
            header_layout.addWidget(alias_header)
            header_layout.addWidget(action_header)
            header_layout.addWidget(value_header)
            header_layout.addStretch()
            
            scroll_layout.addLayout(header_layout)
            
            # Ligne de séparation
            separator = QLabel()
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: rgba(100, 100, 100, 150);")
            scroll_layout.addWidget(separator)
            
            # Liste des clips
            for clip_data in stored_clips:
                clip_layout = QHBoxLayout()
                
                alias = clip_data.get('alias', '')
                
                # Alias (image, emoji ou texte)
                alias_label = QLabel()
                alias_label.setFixedSize(50, 50)
                
                if "/" in alias:
                    # C'est une image - vérifier si elle existe encore
                    if os.path.exists(alias):
                        pixmap = image_pixmap(alias, 48)
                        alias_label.setPixmap(pixmap)
                        alias_label.setScaledContents(True)
                    else:
                        # Image manquante - afficher un placeholder
                        alias_label.setText("🖼️")
                        alias_label.setStyleSheet("color: gray; font-size: 32px;")
                        alias_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                elif is_emoji(alias):
                    # C'est un emoji
                    pixmap = emoji_pixmap(alias, 32)
                    alias_label.setPixmap(pixmap)
                    alias_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    # C'est du texte
                    # pixmap = text_pixmap(alias, 32)
                    # alias_label.setPixmap(pixmap)
                    alias_label.setText(alias)
                    alias_label.setWordWrap(True)
                    alias_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                              
                # Action
                action_label = QLabel(clip_data.get('action', 'copy'))
                action_label.setFixedWidth(80)
                action_label.setStyleSheet("color: blue;")
                
                # String (tronquée si trop longue)
                string = clip_data.get('string', '')
                string_display = string[:50] + "..." if len(string) > 50 else string
                string_label = QLabel(string_display)
                string_label.setStyleSheet("color: black;")
                string_label.setWordWrap(True)
                
                # Bouton restaurer
                restore_btn = QPushButton("↩️")
                restore_btn.setFixedSize(30, 30)
                restore_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(100, 200, 100, 100);
                        border: 1px solid rgba(100, 255, 100, 150);
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(100, 255, 100, 150);
                    }
                """)
                restore_btn.clicked.connect(lambda checked, a=alias, cd=clip_data: self.restore_clip_to_menu(a, cd, dialog, x, y))
                
                # Bouton supprimer
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(200, 100, 100, 100);
                        border: 1px solid rgba(255, 100, 100, 150);
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 100, 100, 150);
                    }
                """)
                delete_btn.clicked.connect(lambda checked, a=alias: self.delete_stored_clip_and_refresh(a, dialog, x, y))
                
                clip_layout.addWidget(alias_label)
                # clip_layout.addWidget(alias_text)
                clip_layout.addWidget(action_label)
                clip_layout.addWidget(string_label)
                clip_layout.addStretch()
                clip_layout.addWidget(restore_btn)
                clip_layout.addWidget(delete_btn)
                
                scroll_layout.addLayout(clip_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Bouton Fermer
        close_button = QPushButton("Fermer")
        close_button.setFixedHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 100);
                color: white;
                border: 1px solid rgba(150, 150, 150, 150);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 150);
            }
        """)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addLayout(layout)
        
        # Réactiver le mouse tracking après fermeture
        dialog.finished.connect(lambda: self.current_popup.setMouseTracking(True) if self.current_popup else None)
        
        dialog.exec()
    
    def delete_stored_clip_and_refresh(self, alias, dialog, x, y):
        """Affiche une confirmation avant de supprimer un clip stocké"""
        # Fermer le dialogue actuel
        dialog.accept()
        
        # Afficher la confirmation
        confirm_dialog = QDialog(self.tracker)
        confirm_dialog.setWindowTitle("🗑️ Supprimer du stockage")
        confirm_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        confirm_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        confirm_dialog.setPalette(palette)
        
        confirm_dialog.setFixedSize(350, 150)
        confirm_dialog.move(x - 175, y - 75)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Message
        display_name = alias if "/" not in alias else os.path.basename(alias)
        message = QLabel(f"Supprimer définitivement\n'{display_name}'\ndu stockage ?")
        message.setStyleSheet("color: white; font-size: 14px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 100);
                border: 1px solid rgba(150, 150, 150, 150);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 150);
            }
        """)
        cancel_button.clicked.connect(lambda: (confirm_dialog.reject(), self.show_stored_clips_dialog(x, y)))
        
        delete_button = QPushButton("🗑️ Supprimer")
        delete_button.setFixedHeight(40)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 100, 100, 100);
                border: 1px solid rgba(255, 100, 100, 150);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 150);
            }
        """)
        
        def confirm_delete():
            # Supprimer le thumbnail s'il existe
            if os.path.exists(alias):
                os.remove(alias)
            
            remove_stored_clip(alias)
            confirm_dialog.accept()
            self.show_stored_clips_dialog(x, y)
        
        delete_button.clicked.connect(confirm_delete)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(delete_button)
        layout.addLayout(buttons_layout)
        
        dialog_layout = QVBoxLayout(confirm_dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addLayout(layout)
        
        confirm_dialog.exec()
    
    def restore_clip_to_menu(self, alias, clip_data, dialog, x, y):
        """Restaure un clip stocké vers le menu radial"""
        # Récupérer les données du clip
        action = clip_data.get('action', 'copy')
        string = clip_data.get('string', '')
        
        # Ajouter au menu radial (dans le fichier JSON)
        append_to_actions_file_json(CLIP_NOTES_FILE_JSON, alias, string, action)
        
        # Ajouter directement dans actions_map_sub pour mise à jour immédiate
        if action == "copy":
            self.actions_map_sub[alias] = [(paperclip_copy, [string], {}), string, action]
        elif action == "term":
            self.actions_map_sub[alias] = [(execute_terminal, [string], {}), string, action]
        elif action == "exec":
            self.actions_map_sub[alias] = [(execute_command, [string], {}), string, action]
        
        # Supprimer du stockage
        remove_stored_clip(alias)
        
        # Mettre à jour le menu en arrière-plan
        self.refresh_menu()
        
        # Fermer le dialogue actuel et rouvrir la fenêtre de stockage
        dialog.accept()
        self.show_stored_clips_dialog(x, y)
    
    def show_config_dialog(self, x, y):
        """Affiche le dialogue de configuration"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("⚙️ Configuration")
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
        
        dialog.setFixedSize(400, 720)
        
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x, y)
        
        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)
        
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titre
        title = QLabel("⚙️ Configuration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # --- Couleurs des zones ---
        colors_label = QLabel("🎨 Couleurs des zones")
        colors_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(colors_label)
        
        # Variables pour stocker les couleurs sélectionnées
        selected_colors = {
            "copy": ACTION_ZONE_COLORS["copy"],
            "term": ACTION_ZONE_COLORS["term"],
            "exec": ACTION_ZONE_COLORS["exec"]
        }
        
        def create_color_button(action_name, label_text, rgb):
            """Crée un bouton coloré qui ouvre un color picker"""
            layout_h = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(100)
            
            button = QPushButton()
            button.setFixedHeight(30)
            button.setFixedWidth(150)
            
            def update_button_color():
                r, g, b = selected_colors[action_name]
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({r}, {g}, {b});
                        border: 2px solid rgba(255, 255, 255, 100);
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid rgba(255, 255, 255, 200);
                    }}
                """)
                button.setText(f"RGB({r}, {g}, {b})")
            
            def pick_color():
                r, g, b = selected_colors[action_name]
                initial_color = QColor(r, g, b)
                color = QColorDialog.getColor(initial_color, dialog, f"Choisir la couleur pour {label_text}")
                if color.isValid():
                    selected_colors[action_name] = (color.red(), color.green(), color.blue())
                    update_button_color()
            
            button.clicked.connect(pick_color)
            update_button_color()
            
            layout_h.addWidget(label)
            layout_h.addWidget(button)
            layout_h.addStretch()
            return layout_h
        
        # Boutons pour chaque action
        copy_layout = create_color_button("copy", "✂️ Copie", ACTION_ZONE_COLORS["copy"])
        layout.addLayout(copy_layout)
        
        term_layout = create_color_button("term", "💻 Terminal", ACTION_ZONE_COLORS["term"])
        layout.addLayout(term_layout)
        
        exec_layout = create_color_button("exec", "🚀 Exécution", ACTION_ZONE_COLORS["exec"])
        layout.addLayout(exec_layout)
        
        # --- Opacités ---
        opacity_label = QLabel("🔆 Opacités")
        opacity_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(opacity_label)
        
        # Slider pour opacité du menu
        menu_opacity_layout = QVBoxLayout()
        menu_opacity_label = QLabel(f"Opacité générale {MENU_OPACITY}")
        menu_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        menu_opacity_slider.setMinimum(0)
        menu_opacity_slider.setMaximum(100)
        menu_opacity_slider.setValue(MENU_OPACITY)
        menu_opacity_slider.valueChanged.connect(lambda v: menu_opacity_label.setText(f"Opacité générale {v}"))
        menu_opacity_layout.addWidget(menu_opacity_label)
        menu_opacity_layout.addWidget(menu_opacity_slider)
        layout.addLayout(menu_opacity_layout)
        
        # Couleur du fond du menu
        menu_bg_color_layout = QHBoxLayout()
        menu_bg_color_label = QLabel("Couleur du fond")
        menu_bg_color_label.setFixedWidth(150)
        
        menu_bg_color_button = QPushButton()
        menu_bg_color_button.setFixedHeight(30)
        menu_bg_color_button.setFixedWidth(150)
        
        # Variable pour stocker la couleur du fond du menu
        selected_menu_bg_color = list(MENU_BACKGROUND_COLOR)
        
        def update_menu_bg_button():
            r, g, b = selected_menu_bg_color
            menu_bg_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
            """)
            menu_bg_color_button.setText(f"RGB({r}, {g}, {b})")
        
        def pick_menu_bg_color():
            r, g, b = selected_menu_bg_color
            initial_color = QColor(r, g, b)
            color = QColorDialog.getColor(initial_color, dialog, "Choisir la couleur du fond du menu")
            if color.isValid():
                selected_menu_bg_color[0] = color.red()
                selected_menu_bg_color[1] = color.green()
                selected_menu_bg_color[2] = color.blue()
                update_menu_bg_button()
        
        menu_bg_color_button.clicked.connect(pick_menu_bg_color)
        update_menu_bg_button()
        
        menu_bg_color_layout.addWidget(menu_bg_color_label)
        menu_bg_color_layout.addWidget(menu_bg_color_button)
        menu_bg_color_layout.addStretch()
        layout.addLayout(menu_bg_color_layout)
        
        # Slider pour opacité de base
        basic_opacity_layout = QVBoxLayout()
        basic_opacity_label = QLabel(f"Opacité des zones d'action {ZONE_BASIC_OPACITY}")
        basic_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        basic_opacity_slider.setMinimum(0)
        basic_opacity_slider.setMaximum(100)
        basic_opacity_slider.setValue(ZONE_BASIC_OPACITY)
        basic_opacity_slider.valueChanged.connect(lambda v: basic_opacity_label.setText(f"Opacité des zones d'action {v}"))
        basic_opacity_layout.addWidget(basic_opacity_label)
        basic_opacity_layout.addWidget(basic_opacity_slider)
        layout.addLayout(basic_opacity_layout)
        
        # Slider pour opacité au survol
        hover_opacity_layout = QVBoxLayout()
        hover_opacity_label = QLabel(f"Opacité des zones d'action au survol {ZONE_HOVER_OPACITY}")
        hover_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        hover_opacity_slider.setMinimum(0)
        hover_opacity_slider.setMaximum(100)
        hover_opacity_slider.setValue(ZONE_HOVER_OPACITY)
        hover_opacity_slider.valueChanged.connect(lambda v: hover_opacity_label.setText(f"Opacité des zones d'action au survol {v}"))
        hover_opacity_layout.addWidget(hover_opacity_label)
        hover_opacity_layout.addWidget(hover_opacity_slider)
        layout.addLayout(hover_opacity_layout)
        
        # --- Options ---
        options_label = QLabel("⚡ Options")
        options_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(options_label)
        
        # Checkbox pour l'icône centrale
        icon_checkbox = QCheckBox("Afficher l'icône du clip survolé")
        icon_checkbox.setChecked(SHOW_CENTRAL_ICON)
        layout.addWidget(icon_checkbox)
        
        # Checkbox pour le néon central
        neon_checkbox = QCheckBox("Afficher le néon cosmétique")
        neon_checkbox.setChecked(CENTRAL_NEON)
        layout.addWidget(neon_checkbox)
        
        # Couleur du néon
        neon_color_layout = QHBoxLayout()
        neon_color_label = QLabel("Couleur du néon")
        neon_color_label.setFixedWidth(150)
        
        neon_color_button = QPushButton()
        neon_color_button.setFixedHeight(30)
        neon_color_button.setFixedWidth(150)
        
        # Variable pour stocker la couleur du néon
        selected_neon_color = list(NEON_COLOR)
        
        def update_neon_button():
            r, g, b = selected_neon_color
            neon_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
            """)
            neon_color_button.setText(f"RGB({r}, {g}, {b})")
        
        def pick_neon_color():
            r, g, b = selected_neon_color
            initial_color = QColor(r, g, b)
            color = QColorDialog.getColor(initial_color, dialog, "Choisir la couleur du néon")
            if color.isValid():
                selected_neon_color[0] = color.red()
                selected_neon_color[1] = color.green()
                selected_neon_color[2] = color.blue()
                update_neon_button()
        
        neon_color_button.clicked.connect(pick_neon_color)
        update_neon_button()
        
        neon_color_layout.addWidget(neon_color_label)
        neon_color_layout.addWidget(neon_color_button)
        neon_color_layout.addStretch()
        layout.addLayout(neon_color_layout)
        
        # Slider pour la vitesse du néon
        neon_speed_layout = QVBoxLayout()
        neon_speed_label = QLabel(f"Vitesse du néon: {NEON_SPEED}ms")
        neon_speed_slider = QSlider(Qt.Orientation.Horizontal)
        # Bornes des vitesses
        neon_speed_slider.setMinimum(1)
        neon_speed_slider.setMaximum(200)
        neon_speed_slider.setValue(NEON_SPEED)
        neon_speed_slider.valueChanged.connect(lambda v: neon_speed_label.setText(f"Vitesse du néon: {v}ms"))
        neon_speed_layout.addWidget(neon_speed_label)
        neon_speed_layout.addWidget(neon_speed_slider)
        layout.addLayout(neon_speed_layout)
        
        # Boutons Sauvegarder et Annuler
        layout.addStretch()
        buttons_layout = QHBoxLayout()
        
        # Bouton Annuler
        cancel_button = QPushButton("❌")
        cancel_button.setFixedHeight(40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 100, 100, 100);
                border: 1px solid rgba(255, 100, 100, 150);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 150);
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        
        # Bouton Sauvegarder
        save_button = QPushButton("💾")
        save_button.setFixedHeight(40)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 200, 100, 100);
                border: 1px solid rgba(100, 255, 100, 150);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(100, 255, 100, 150);
            }
        """)
        
        def save_and_close():
            global CENTRAL_NEON, ZONE_BASIC_OPACITY, ZONE_HOVER_OPACITY, SHOW_CENTRAL_ICON, ACTION_ZONE_COLORS, MENU_OPACITY, MENU_BACKGROUND_COLOR, NEON_COLOR, NEON_SPEED
            
            # Mettre à jour les variables globales
            ACTION_ZONE_COLORS["copy"] = selected_colors["copy"]
            ACTION_ZONE_COLORS["term"] = selected_colors["term"]
            ACTION_ZONE_COLORS["exec"] = selected_colors["exec"]
            ZONE_BASIC_OPACITY = basic_opacity_slider.value()
            ZONE_HOVER_OPACITY = hover_opacity_slider.value()
            MENU_OPACITY = menu_opacity_slider.value()
            MENU_BACKGROUND_COLOR = tuple(selected_menu_bg_color)
            NEON_COLOR = tuple(selected_neon_color)
            NEON_SPEED = neon_speed_slider.value()
            SHOW_CENTRAL_ICON = icon_checkbox.isChecked()
            CENTRAL_NEON = neon_checkbox.isChecked()
            
            # Sauvegarder dans le fichier
            save_config()
            
            # Fermer le dialogue
            dialog.accept()
        
        save_button.clicked.connect(save_and_close)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(save_button)
        layout.addLayout(buttons_layout)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        dialog.exec()
        
        # Réactiver le mouse tracking du menu radial après fermeture
        if self.current_popup:
            self.current_popup.setMouseTracking(True)
        
        # Si le dialogue a été accepté (sauvegarde), rafraîchir le menu
        if dialog.result() == QDialog.DialogCode.Accepted:
            self.refresh_menu()

    def new_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input, slider):
            name = name_input.text().strip()
            value = value_input.toPlainText().strip().replace('\n', '\\n')
            
            if name and value:
                # Si une image a été sélectionnée, créer le thumbnail
                if self._dialog_temp_image_path:
                    thumbnail_path = create_thumbnail(self._dialog_temp_image_path)
                    if thumbnail_path:
                        name = thumbnail_path  # Utiliser le chemin du thumbnail comme nom
                        print(f"Thumbnail créé: {thumbnail_path}")
                    else:
                        print("Erreur lors de la création du thumbnail")
                        return
                
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
                
                # append_to_actions_file(CLIP_NOTES_FILE, name, value)
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
                
                # Si une nouvelle image a été sélectionnée, créer le thumbnail
                if self._dialog_temp_image_path:
                    thumbnail_path = create_thumbnail(self._dialog_temp_image_path)
                    if thumbnail_path:
                        new_name = thumbnail_path  # Utiliser le chemin du thumbnail comme nom
                        print(f"Nouveau thumbnail créé: {thumbnail_path}")
                    else:
                        print("Erreur lors de la création du thumbnail")
                        return
                
                if new_name != old_name:
                    self.actions_map_sub.pop(old_name, None)
                    # Supprimer l'ancien alias du JSON
                    delete_from_json(CLIP_NOTES_FILE_JSON, old_name)
                    # Supprimer l'ancien thumbnail s'il existe (si c'est un chemin de fichier)
                    if "/" in old_name and os.path.exists(old_name):
                        try:
                            os.remove(old_name)
                            print(f"Ancien thumbnail supprimé: {old_name}")
                        except Exception as e:
                            print(f"Erreur lors de la suppression de l'ancien thumbnail: {e}")
                
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
            "➖": "Supprimer",
            "⚙️": "Configuration",
            "📦": "Stockage"
        }
        
        self.actions_map_sub = {
            "➕": [(self.new_clip,    [x,y], {}), special_button_tooltips["➕"], None],
            "✏️": [(self.update_clip, [x,y], {}), special_button_tooltips["✏️"], None],
            "➖": [(self.delete_clip, [x,y], {}), special_button_tooltips["➖"], None],
            "⚙️": [(self.show_config_dialog, [x,y], {}), special_button_tooltips["⚙️"], None],
            "📦": [(self.show_storage_menu, [x,y], {}), special_button_tooltips["📦"], None],
        }
        populate_actions_map_from_file(CLIP_NOTES_FILE_JSON, self.actions_map_sub, execute_command)

        # Séparer les boutons spéciaux des autres
        special_buttons = SPECIAL_BUTTONS
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
        
        # Appliquer l'opacité configurée
        self.current_popup.set_widget_opacity(MENU_OPACITY / 100.0)
        
        # ===== NÉON BLEU MENU PRINCIPAL =====
        # Activer le néon bleu clignotant dès l'ouverture
        self.current_popup.toggle_neon(CENTRAL_NEON)
        self.current_popup.timer.start(NEON_SPEED)
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