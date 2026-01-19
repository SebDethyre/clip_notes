import math
from PyQt6.QtGui import QPainter, QColor, QIcon, QRadialGradient, QFont, QPen, QCursor
from PyQt6.QtCore import Qt, QSize, QTimer, QRect, QEasingCurve, QVariantAnimation, QEvent, QPointF, QRectF
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton
from PyQt6.QtWidgets import QLabel

from utils import *
from ui import HoverSubMenu, RadialKeyboardListener, TooltipWindow

class RadialMenu(QWidget):
    def __init__(self, x, y, buttons, parent=None, sub=False, tracker=None, app_instance=None, neon_color=None, action_zone_colors=None, nb_icons_menu=None, show_central_icon=None, menu_background_color=None, zone_basic_opacity=None, zone_hover_opacity=None):
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
        
        self.target_x = x - self.widget_size // 2
        self.target_y = y - self.widget_size // 2
        
        self.resize(self.widget_size, self.widget_size)
        self.move(self.target_x, self.target_y)

        self.x = x
        self.y = y
        self.central_text = ""
        self.tooltips = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)

        step = 2
        max_val = 50
        min_val = 0

        up = list(range(min_val, max_val + 1, step))
        down = list(range(max_val - step, min_val - 1, -step))
        sequence = up + down
        self.keyframes = sequence
        self.neon_radius = self.keyframes[0]  
        self.neon_enabled = False
        self.neon_opacity = 120
        self.neon_color = neon_color
        self.widget_opacity = 1.0
        self.scale_factor = 0.1  # Démarrer petit pour l'animation

        self.current_index = 0
        self.current_grabed_clip_label = None

        self.action_zone_colors = action_zone_colors
        self.nb_icons_menu = nb_icons_menu
        self.show_central_icon = show_central_icon
        self.menu_background_color = menu_background_color
        self.zone_basic_opacity = zone_basic_opacity
        self.zone_hover_opacity = zone_hover_opacity
        
        # Stocker les couleurs par action pour chaque bouton
        self.button_colors = []  # Liste des couleurs pour chaque bouton
        self.button_actions = []  # Liste des actions pour chaque bouton
        self.button_labels = []  # Liste des labels pour chaque bouton
        self.hovered_action = None  # Action survolée (None, "copy", "term", ou "exec")
        self.hovered_button_index = None  # Index du bouton survolé
        self.central_icon = None  # Pixmap de l'icône centrale à afficher
        self.action_badges = {}  # Dictionnaire des badges globaux par action
        
        # Navigation au clavier
        self.focused_index = -1  # -1 = pas de focus visible
        self.keyboard_used = False  # Pour savoir si le clavier a été utilisé
        
        # === DRAG & DROP SUR LE CERCLE ===
        self.reorder_mode = False  # Mode réordonnancement activé
        self.drag_active = False  # Un drag est en cours
        self.dragged_button_index = None  # Index du bouton en cours de drag
        self.drop_indicator_angle = None  # Angle où afficher l'indicateur de drop (en degrés)
        self.drop_target_info = None  # Info sur où insérer: (target_index, insert_before)
        self.drag_pending = False  # True si on a cliqué mais pas encore bougé
        self.drag_start_pos = None  # Position de départ du clic
        self.drag_threshold = 10  # Distance minimale en pixels pour déclencher un drag
        
        # Activer le tracking de la souris pour détecter le hover
        self.setMouseTracking(True)
        
        
        # === NOUVELLE FENÊTRE TOOLTIP ===
        self.tooltip_window = TooltipWindow(parent=self)
        
        # === LISTENER CLAVIER ===
        self.keyboard_listener = RadialKeyboardListener(self)
        QApplication.instance().installEventFilter(self.keyboard_listener)
        
        # === SOUS-MENU HOVER (pour ➖) ===
        self.hover_submenu = None  # Le sous-menu actuellement affiché
        self.storage_button_index = None  # Index du bouton ➖
        # self.hover_close_timer = QTimer(self)  # Timer pour fermeture retardée
        # self.hover_close_timer.setSingleShot(True)
        # self.hover_close_timer.timeout.connect(self.check_hover_submenu_close)
        self.special_buttons_by_numbers = {
            4 : ["➖", "⚙️", "🔧", "➕"],
            5 : ["➖", "📦", "⚙️", "🔧", "➕"],
            6 : ["➖", "📋", "💾", "⚙️", "🔧", "➕"]
        }
        # === ANIMATION BOUTONS SPÉCIAUX (hover sur ➕) ===
        self.special_buttons_revealed = False  # Les boutons spéciaux sont-ils complètement révélés ?
        self.special_animating = False  # Animation en cours ?
        self.special_reveal_timer = QTimer(self)
        self.special_reveal_timer.setSingleShot(True)
        self.special_reveal_timer.timeout.connect(self.reveal_next_special_button)
        self.special_reveal_queue = []  # File d'attente des boutons à révéler
        self.plus_button_index = None  # Index du bouton ➕
        self.special_button_indices = []  # Indices des boutons spéciaux (sauf ➕)
        
        # Animation de fermeture (reverse)
        self.special_hide_timer = QTimer(self)
        self.special_hide_timer.setSingleShot(True)
        self.special_hide_timer.timeout.connect(self.hide_next_special_button)
        self.special_hide_queue = []  # File d'attente des boutons à cacher
        
        # Tracking de la zone spéciale
        self.mouse_in_special_zone = False  # La souris est-elle dans la zone des boutons spéciaux ?
        
        # Créer les boutons initiaux
        self.create_buttons(buttons)

    def create_buttons(self, buttons):
        """Crée les boutons pour le menu radial"""
        # Couleurs par type d'action (utilise directement les RGB)
        action_colors = {
            action: QColor(*rgb, 25)
            for action, rgb in self.action_zone_colors.items()
        }
        
        # Tooltips pour les boutons spéciaux
        if self.nb_icons_menu == 4:
            special_tooltips = {
                "➕": "Ajouter",
                "🔧": "Modifier",
                "⚙️": "Configurer",
                "➖": "Supprimer"
            }
        elif self.nb_icons_menu == 5:
            special_tooltips = {
                "➕": "Ajouter",
                "🔧": "Modifier",
                "⚙️": "Configurer",
                "➖": "Supprimer",
                "📦": "Stocker"
            }
        elif self.nb_icons_menu == 6:
            special_tooltips = {
                "➕": "Ajouter",
                "🔧": "Modifier",
                "⚙️": "Configurer",
                "💾": "Stocker",
                "📋": "Stock",
                "➖": "Supprimer",
            }
        if buttons:
            angle_step = 360 / len(buttons)
            for i, button in enumerate(buttons):
                if len(button) == 2:
                    label, callback = button
                    tooltip = ""
                    action = None
                    tooltip_html = None
                elif len(button) == 3:
                    label, callback, tooltip = button
                    action = None
                    tooltip_html = None
                elif len(button) == 4:
                    label, callback, tooltip, action = button
                    tooltip_html = None
                elif len(button) == 5:
                    label, callback, tooltip, action, tooltip_html = button
                else:
                    label, callback = button
                    tooltip = ""
                    action = None
                    tooltip_html = None
                
                # Si c'est un bouton spécial sans tooltip, utiliser le tooltip par défaut
                if label in special_tooltips and not tooltip:
                    tooltip = special_tooltips[label]
                # Stocker la couleur, l'action et le label pour ce bouton
                color = action_colors.get(action, None)
                self.button_colors.append(color)
                self.button_actions.append(action)
                self.button_labels.append(label)
                    
                angle = math.radians(i * angle_step)
                # Le centre du menu radial est maintenant au centre du widget agrandi
                center_offset = self.widget_size // 2
                bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
                by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2

                btn = QPushButton("", self)
                # Activer le hover tracking pour ce bouton
                btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
                # Activer le mouse tracking pour recevoir les événements MouseMove
                btn.setMouseTracking(True)
                
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
                
                # Les boutons spéciaux (➕ 🔧 ➖) ont un fond transparent MAIS coloré au hover
                special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
                if label in special_buttons:
                    # Stocker l'index du bouton ➕ et des autres boutons spéciaux
                    if label == "➕":
                        self.plus_button_index = i
                    else:
                        self.special_button_indices.append(i)
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
                if self.nb_icons_menu == 4:
                    if label == "➖":
                        self.storage_button_index = i
                        # Le clic ouvre aussi le sous-menu (pour la navigation clavier)
                        btn.clicked.connect(lambda checked=False, b=btn: self.show_storage_submenu(b))
                    else:
                        btn.clicked.connect(self.make_click_handler(callback, label, tooltip, action))
                elif self.nb_icons_menu == 5:   
                    # Cas spécial : le bouton 📦 ouvre le sous-menu de stockage
                    if label == "📦":
                        self.storage_button_index = i
                        # Le clic ouvre aussi le sous-menu (pour la navigation clavier)
                        btn.clicked.connect(lambda checked=False, b=btn: self.show_storage_submenu(b))
                    else:
                        btn.clicked.connect(self.make_click_handler(callback, label, tooltip, action))
                elif self.nb_icons_menu == 6:   
                    btn.clicked.connect(self.make_click_handler(callback, label, tooltip, action))
                
                # Installer l'eventFilter pour tous les boutons (pour tooltips et badges)
                btn.installEventFilter(self)
                if tooltip:
                    self.tooltips[btn] = (tooltip, tooltip_html)
                self.buttons.append(btn)
            
        # Créer les 3 badges globaux (un par action) - seront positionnés dynamiquement
        self.action_badges = {}
        badge_info = {
            "copy": "✂️",
            "term": "💻", 
            "exec": "🚀"
        }
        
        for action, emoji in badge_info.items():
            badge = QLabel(emoji, self)
            # Utiliser la couleur de la zone d'action avec son opacité
            if self.action_zone_colors and action in self.action_zone_colors:
                r, g, b = self.action_zone_colors[action]
                opacity = self.zone_hover_opacity if self.zone_hover_opacity else 120
                badge.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba({r}, {g}, {b}, {opacity});
                        border-radius: 17px;
                        padding: 4px;
                        font-size: 22px;
                    }}
                """)
            else:
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
            self.action_badges[action] = badge

    def update_buttons(self, buttons):
        """Met à jour les boutons existants sans recréer le widget entier"""
        # Sauvegarder l'état actuel
        was_visible = self.isVisible()
        current_opacity = self.widget_opacity
        
        # Détruire les anciens boutons
        for btn in self.buttons:
            btn.removeEventFilter(self)
            btn.deleteLater()
        
        # Détruire les anciens badges
        if hasattr(self, 'action_badges'):
            for badge in self.action_badges.values():
                badge.deleteLater()
        
        self.buttons.clear()
        self.tooltips.clear()
        self.button_colors.clear()
        self.button_actions.clear()
        self.button_labels.clear()
        self.action_badges = {}
        self.storage_button_index = None  # Réinitialiser l'index du bouton ➖
        self.plus_button_index = None  # Réinitialiser l'index du bouton ➕
        self.special_button_indices = []  # Réinitialiser les indices des boutons spéciaux
        self.special_buttons_revealed = False  # Réinitialiser l'état de révélation
        self.special_animating = False  # Réinitialiser l'état d'animation
        self.special_reveal_queue = []  # Vider la file d'attente de révélation
        self.special_hide_queue = []  # Vider la file d'attente de fermeture
        self.special_reveal_timer.stop()
        self.special_hide_timer.stop()
        self.mouse_in_special_zone = False  # Réinitialiser le tracking de zone
        
        # Réinitialiser l'état du drag & drop
        self.drag_active = False
        self.drag_pending = False
        self.drag_start_pos = None
        self.dragged_button_index = None
        self.drop_indicator_angle = None
        self.drop_target_info = None
        self.current_grabed_clip_label = None
        # Note: on ne réinitialise PAS reorder_mode ici car il est géré par app_instance
        
        # Fermer le sous-menu hover s'il existe
        if self.hover_submenu is not None:
            try:
                self.hover_submenu.close()
            except RuntimeError:
                pass
            self.hover_submenu = None
        
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
            self.move(self.x - self.widget_size // 2, self.y - self.widget_size // 2)
        # Réinitialiser le hover
        self.hovered_action = None
        
        # Créer les nouveaux boutons
        self.create_buttons(buttons)
        # Restaurer l'état
        if was_visible:
            self.set_widget_opacity(current_opacity)
            # Utiliser reveal_buttons pour respecter la logique des boutons spéciaux
            self.reveal_buttons()
        
        # CRITIQUE: Réactiver le mouse tracking après la reconstruction
        self.setMouseTracking(True)
        # Repositionner la fenêtre tooltip
        self.update_tooltip_position()
        
        # Réinitialiser le focus visuel mais garder l'état du clavier
        # Si l'utilisateur a déjà utilisé le clavier, on garde cet état
        self.focused_index = -1
        # Ne PAS réinitialiser _keyboard_used pour garder l'état entre sous-menus
        
        self.update()

    def eventFilter(self, watched, event):
        """Gère les événements de hover sur les boutons"""
        
        # === GESTION DU DRAG & DROP DES CLIPS (toujours actif) ===
        if watched in self.buttons:
            button_index = self.buttons.index(watched)
            label = self.button_labels[button_index] if button_index < len(self.button_labels) else ""
            special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
            is_clip = label not in special_buttons and button_index < len(self.button_actions) and self.button_actions[button_index] is not None
            
            if event.type() == QEvent.Type.MouseButtonPress and is_clip:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Mémoriser pour détecter si c'est un drag ou un clic
                    self.drag_pending = True
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.dragged_button_index = button_index
                    self.current_grabed_clip_label = label
                    # Ne pas consommer l'événement tout de suite
            
            if event.type() == QEvent.Type.MouseMove and self.drag_pending and not self.drag_active:
                if self.drag_start_pos is not None:
                    # Calculer la distance parcourue
                    current_pos = event.globalPosition().toPoint()
                    dx = current_pos.x() - self.drag_start_pos.x()
                    dy = current_pos.y() - self.drag_start_pos.y()
                    distance = (dx * dx + dy * dy) ** 0.5
                    
                    if distance > self.drag_threshold:
                        # C'est un vrai drag, l'activer
                        self.drag_active = True
                        self.drag_pending = False
                        self.drop_indicator_angle = None
                        self.drop_target_info = None
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self.tooltip_window.hide()
                        self.grabMouse()
                        self.update()
                        return True
            
            if event.type() == QEvent.Type.MouseButtonRelease and is_clip:
                if event.button() == Qt.MouseButton.LeftButton and self.drag_pending and not self.drag_active:
                    # C'était un clic simple, pas un drag - exécuter l'action du clip
                    self.drag_pending = False
                    self.drag_start_pos = None
                    self.dragged_button_index = None
                    self.current_grabed_clip_label = None
                    # Laisser l'événement passer pour déclencher le clic normal
                    return False
        
        if event.type() == QEvent.Type.Enter:
            # Trouver l'index du bouton survolé
            if watched in self.buttons and self.show_central_icon:
                button_index = self.buttons.index(watched)
                self.hovered_button_index = button_index
                
                # === Changer le curseur pour les clips (toujours actif) ===
                if not self.drag_active:
                    label = self.button_labels[button_index] if button_index < len(self.button_labels) else ""
                    special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
                    is_clip = label not in special_buttons and button_index < len(self.button_actions) and self.button_actions[button_index] is not None
                    if is_clip:
                        # C'est un clip, montrer qu'on peut l'attraper
                        self.setCursor(Qt.CursorShape.OpenHandCursor)
                
                # Vérifier si on entre dans la zone spéciale
                all_special_indices = self.special_button_indices + ([self.plus_button_index] if self.plus_button_index is not None else [])
                if button_index in all_special_indices:
                    if not self.mouse_in_special_zone:
                        self.mouse_in_special_zone = True
                        self.on_enter_special_zone()
                else:
                    # On entre sur un bouton non-spécial
                    # Ne pas interrompre l'animation de révélation en cours
                    if self.mouse_in_special_zone and not (self.special_animating and self.special_reveal_queue):
                        self.mouse_in_special_zone = False
                        self.on_leave_special_zone()
                
                # Cas spécial : hover sur le bouton ➖ -> ouvrir le sous-menu
                if button_index == self.storage_button_index:
                    self.show_storage_submenu(watched)
                
                # Créer l'icône centrale pour ce bouton (sauf pendant le drag)
                if not self.drag_active and button_index < len(self.button_labels):
                    label = self.button_labels[button_index]
                    # Créer un pixmap adapté au type de label
                    if "/" in label:
                        # C'est un chemin d'image
                        self.central_icon = image_pixmap(label, 64)
                    elif is_emoji(label):
                        # C'est un emoji
                        self.central_icon = emoji_pixmap(label, 48)
                    else:
                        # C'est du texte simple
                        self.central_icon = text_pixmap(label, 48)
                    self.update()
            
            # Afficher le message de hover dans la fenêtre tooltip (sauf pendant le drag)
            if not self.drag_active and watched in self.tooltips:
                tooltip_data = self.tooltips[watched]
                # Supporter l'ancien format (string) et le nouveau (tuple)
                if isinstance(tooltip_data, tuple):
                    tooltip_text, tooltip_html = tooltip_data
                else:
                    tooltip_text, tooltip_html = tooltip_data, None
                # Afficher dans la fenêtre tooltip en dessous (durée infinie)
                self.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
                self.update_tooltip_position()
                
        elif event.type() == QEvent.Type.Leave:
            # Effacer l'icône centrale quand on quitte le bouton (sauf pendant le drag)
            if watched in self.buttons and self.show_central_icon and not self.drag_active:
                self.central_icon = None
                self.hovered_button_index = None
                self.update()
            
            # Réinitialiser le curseur quand on quitte un clip (si pas en drag)
            if not self.drag_active:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # Masquer le message quand on quitte le bouton (sauf pendant le drag)
            if not self.drag_active:
                self.tooltip_window.hide()
        
        return super().eventFilter(watched, event)
    
    def is_angle_in_special_zone(self, mouse_angle):
        """Détermine si l'angle de la souris correspond à une zone de bouton spécial"""
        # Obtenir les boutons visibles
        visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
        if not visible_indices:
            return False
        
        num_visible = len(visible_indices)
        angle_step = 360 / num_visible
        
        # Tous les indices spéciaux (y compris ➕)
        all_special_indices = self.special_button_indices + ([self.plus_button_index] if self.plus_button_index is not None else [])
        
        # Trouver la position de chaque bouton spécial visible dans le cercle
        for pos, btn_index in enumerate(visible_indices):
            if btn_index in all_special_indices:
                # Calculer l'angle de ce bouton
                button_angle = pos * angle_step
                
                # Vérifier si l'angle de la souris est dans cette zone
                half_step = angle_step / 2
                min_angle = (button_angle - half_step) % 360
                max_angle = (button_angle + half_step) % 360
                
                # Gérer le cas où la zone traverse 0°
                if min_angle > max_angle:
                    if mouse_angle >= min_angle or mouse_angle < max_angle:
                        return True
                else:
                    if min_angle <= mouse_angle < max_angle:
                        return True
        
        return False
    
    def on_enter_special_zone(self):
        """Appelé quand la souris entre dans la zone des boutons spéciaux"""
        # Arrêter l'animation de fermeture si en cours
        self.special_hide_timer.stop()
        self.special_hide_queue = []
        
        # Démarrer l'animation de révélation si pas déjà révélé
        if not self.special_buttons_revealed and not self.special_animating:
            self.start_special_reveal_animation()
    
    def on_leave_special_zone(self):
        """Appelé quand la souris sort de la zone des boutons spéciaux"""
        # Ne pas interrompre l'animation de révélation en cours
        # Une fois démarrée, elle doit aller jusqu'au bout
        if self.special_animating and self.special_reveal_queue:
            return
        
        # Ne pas cacher si le sous-menu hover est ouvert
        if self.hover_submenu is not None:
            try:
                if self.hover_submenu.isVisible():
                    return
            except RuntimeError:
                self.hover_submenu = None
        
        # Démarrer l'animation de fermeture si les boutons sont révélés
        if self.special_buttons_revealed or self.special_animating:
            self.start_special_hide_animation()
    
    def start_special_reveal_animation(self):
        """Démarre l'animation de révélation des boutons spéciaux"""
        if self.special_buttons_revealed and not self.special_animating:
            return
        
        # Arrêter l'animation de fermeture si en cours
        self.special_hide_timer.stop()
        self.special_hide_queue = []
        
        self.special_animating = True
        
        # Créer la file d'attente des boutons à révéler (en partant du plus proche de ➕)
        # Seulement les boutons qui ne sont pas encore visibles
        # Les indices sont dans l'ordre ["➖", "📦"?, "⚙️", "🔧"] 
        # On veut révéler dans l'ordre inverse : "🔧" → "⚙️" → "📦"? → "➖"
        hidden_special = [i for i in self.special_button_indices if not self.buttons[i].isVisible()]
        self.special_reveal_queue = list(reversed(hidden_special))
        
        # Révéler le premier bouton immédiatement
        if self.special_reveal_queue:
            self.reveal_next_special_button()
        else:
            # Tous déjà visibles
            self.special_buttons_revealed = True
            self.special_animating = False
    
    def reveal_next_special_button(self):
        """Révèle le prochain bouton de la file d'attente et repositionne le cercle"""
        if not self.special_reveal_queue:
            # Animation terminée
            self.special_buttons_revealed = True
            self.special_animating = False
            return
        
        # Extraire le prochain index
        next_index = self.special_reveal_queue.pop(0)
        
        # Révéler le bouton
        if next_index < len(self.buttons):
            self.buttons[next_index].setVisible(True)
        
        # Repositionner tous les boutons visibles (le cercle grandit)
        self.reposition_visible_buttons()
        
        # Planifier le prochain si la file n'est pas vide
        if self.special_reveal_queue:
            self.special_reveal_timer.start(30)  # 30ms entre chaque bouton
        else:
            # Animation terminée
            self.special_buttons_revealed = True
            self.special_animating = False
    
    def start_special_hide_animation(self):
        """Démarre l'animation de fermeture des boutons spéciaux (animation inverse)"""
        # Arrêter l'animation de révélation si elle est en cours
        self.special_reveal_timer.stop()
        self.special_reveal_queue = []
        
        self.special_animating = True
        
        # Créer la file d'attente des boutons à cacher (ordre inverse de la révélation)
        # On cache dans l'ordre : "➖" → "📦"? → "⚙️" → "🔧"
        # C'est l'ordre normal de _special_button_indices (pas reversed)
        visible_special = [i for i in self.special_button_indices if self.buttons[i].isVisible()]
        self.special_hide_queue = list(visible_special)  # Ordre normal pour cacher
        print(self.special_hide_queue)
        # Cacher le premier bouton immédiatement
        if self.special_hide_queue:
            self.hide_next_special_button()
        else:
            # Tous déjà cachés
            self.special_buttons_revealed = False
            self.special_animating = False
    
    def hide_next_special_button(self):
        """Cache le prochain bouton de la file d'attente et repositionne le cercle"""
        if not self.special_hide_queue:
            # Animation terminée
            self.special_buttons_revealed = False
            self.special_animating = False
            return
        
        # Extraire le prochain index à cacher
        next_index = self.special_hide_queue.pop(0)
        
        # Cacher le bouton
        if next_index < len(self.buttons):
            self.buttons[next_index].setVisible(False)
        
        # Repositionner tous les boutons visibles (le cercle rétrécit)
        self.reposition_visible_buttons()
        
        # Planifier le prochain si la file n'est pas vide
        if self.special_hide_queue:
            self.special_hide_timer.start(30)  # 30ms entre chaque bouton
        else:
            # Animation terminée
            self.special_buttons_revealed = False
            self.special_animating = False
    
    def reposition_visible_buttons(self):
        """Repositionne les boutons visibles uniformément sur le cercle et ajuste le rayon"""
        # Obtenir les indices des boutons visibles (dans l'ordre)
        visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
        
        if not visible_indices:
            return
        num_visible = len(visible_indices)
        
        # Recalculer le rayon en fonction du nombre de boutons visibles
        old_radius = self.radius
        if num_visible <= 7:
            self.radius = 80
        else:
            self.radius = int(80 * (num_visible / 7))
        
        # Redimensionner le widget si le rayon a changé
        if old_radius != self.radius:
            self.diameter = 2 * (self.radius + self.btn_size)
            self.widget_size = self.diameter + 100
            self.resize(self.widget_size, self.widget_size)
            self.move(self.x - self.widget_size // 2, self.y - self.widget_size // 2)
        
        # Repositionner chaque bouton visible uniformément sur le cercle
        angle_step = 360 / num_visible
        center_offset = self.widget_size // 2
        
        for pos, btn_index in enumerate(visible_indices):
            angle = math.radians(pos * angle_step)
            bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
            by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
            
            btn = self.buttons[btn_index]
            btn.move(int(bx), int(by))
            btn.setFixedSize(self.btn_size, self.btn_size)
            
            # Mettre à jour la taille de l'icône selon le type
            label = self.button_labels[btn_index] if btn_index < len(self.button_labels) else ""
            if "/" in label:
                btn.setIconSize(QSize(48, 48))
            else:
                btn.setIconSize(QSize(32, 32))
        # Mettre à jour la position de la tooltip
        self.update_tooltip_position()
        # Redessiner
        self.update()
    
    def show_storage_submenu(self, storage_button):
        """Affiche le sous-menu de stockage au hover du bouton ➖"""
        # Ne pas recréer si déjà ouvert (vérifier aussi si l'objet C++ existe encore)
        if self.hover_submenu is not None:
            try:
                if self.hover_submenu.isVisible():
                    return
            except RuntimeError:
                # L'objet a été détruit, on peut en recréer un
                self.hover_submenu = None
        
        # Calculer le centre du bouton ➖ en coordonnées globales
        btn_rect = storage_button.geometry()
        btn_center_local = btn_rect.center()
        btn_center_global = self.mapToGlobal(btn_center_local)
        
        # Créer les boutons du sous-menu
        x, y = self.x, self.y
        if self.nb_icons_menu == 4:
            submenu_buttons = [
                ("📋", lambda: self.storage_action_clips(x, y), "Clips stockés"),
                ("🗑️", lambda: self.storage_action_delete(x, y), "Supprimer"),
                ("💾", lambda: self.storage_action_store(x, y), "Stocker"),
            ]
        elif self.nb_icons_menu == 5:
            submenu_buttons = [
                ("📋", lambda: self.storage_action_clips(x, y), "Clips stockés"),
                ("💾", lambda: self.storage_action_store(x, y), "Stocker"),
            ]
        
        # Créer le sous-menu avec self comme parent (nécessaire pour Wayland)
        self.hover_submenu = HoverSubMenu(
            btn_center_global.x(),
            btn_center_global.y(),
            submenu_buttons,
            parent_menu=self,
            app_instance=self.app_instance
        )
        self.hover_submenu.show()
        self.hover_submenu.animate_open()
    
    def storage_action_delete(self, x, y):
        """Action pour passer en mode delete"""
        # Effacer l'icône centrale
        self.central_icon = None
        self.update()
        # Fermer proprement le sous-menu
        if self.hover_submenu is not None:
            try:
                submenu = self.hover_submenu
                self.hover_submenu = None
                submenu.closing = True
                submenu.close()
            except RuntimeError:
                # L'objet a déjà été détruit
                self.hover_submenu = None
        # Appeler la méthode de App
        if self.app_instance:
            self.app_instance.delete_clip(x, y)
    
    def storage_action_clips(self, x, y):
        """Action pour afficher les clips stockés"""
        # Effacer l'icône centrale
        self.central_icon = None
        self.update()
        # Fermer proprement le sous-menu
        if self.hover_submenu is not None:
            try:
                submenu = self.hover_submenu
                self.hover_submenu = None
                submenu.closing = True
                submenu.close()
            except RuntimeError:
                # L'objet a déjà été détruit
                self.hover_submenu = None
        # Appeler la méthode de App
        if self.app_instance:
            self.app_instance.show_stored_clips_dialog(x, y)
    
    def storage_action_store(self, x, y):
        """Action pour passer en mode stockage"""
        # Effacer l'icône centrale
        self.central_icon = None
        self.update()
        # Fermer proprement le sous-menu
        if self.hover_submenu is not None:
            try:
                submenu = self.hover_submenu
                self.hover_submenu = None
                submenu.closing = True
                submenu.close()
            except RuntimeError:
                # L'objet a déjà été détruit
                self.hover_submenu = None
        # Appeler la méthode de App
        if self.app_instance:
            self.app_instance.store_clip_mode(x, y)
    
    def check_hover_submenu_close(self):
        """Vérifie si le sous-menu doit être fermé"""
        if not self.hover_submenu:
            return
        # Vérifier si l'objet existe encore
        try:
            self.hover_submenu.isVisible()
        except RuntimeError:
            self.hover_submenu = None
            return
        cursor_pos = QCursor.pos()
        # Vérifier si la souris est sur le sous-menu
        try:
            submenu_pos = self.hover_submenu.mapFromGlobal(cursor_pos)
            if self.hover_submenu.rect().contains(submenu_pos):
                return  # Souris sur le sous-menu, ne pas fermer
        except RuntimeError:
            self.hover_submenu = None
            return
        # Vérifier si la souris est sur le bouton ➖
        if self.storage_button_index is not None and self.storage_button_index < len(self.buttons):
            storage_btn = self.buttons[self.storage_button_index]
            btn_pos = storage_btn.mapFromGlobal(cursor_pos)
            if storage_btn.rect().contains(btn_pos):
                return  # Souris sur le bouton, ne pas fermer
        # Fermer le sous-menu
        try:
            self.hover_submenu.close()
        except RuntimeError:
            pass
        self.hover_submenu = None
        self.tooltip_window.hide()

    def update_tooltip_position(self):
        """Met à jour la position de la fenêtre tooltip en dessous du menu"""
        self.tooltip_window.position_below_menu(self.x, self.y, self.radius + self.btn_size)

    def set_central_text(self, value):
        self.central_text = value
        self.update()

    def get_neon_radius(self):
        return self.neon_radius

    def set_neon_radius(self, value):
        self.neon_radius = value
        self.update()

    def get_neon_opacity(self):
        return self.neon_opacity

    def set_neon_opacity(self, value):
        self.neon_opacity = value
        self.update()

    def get_neon_color(self):
        return self.neon_color

    def set_neon_color(self, value):
        self.neon_color = value
        self.update()

    def get_widget_opacity(self):
        return self.widget_opacity

    def set_widget_opacity(self, value):
        self.widget_opacity = value
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
            # if action is None:
            #     message = f"✓ {label}"
            #     self.tooltip_window.show_message(message, 1000)
            #     self.update_tooltip_position()
            
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
        
        # === MODE RÉORDONNANCEMENT : Début du drag ===
        if self.reorder_mode and event.button() == Qt.MouseButton.LeftButton:
            # Vérifier si on clique sur un bouton (clip)
            for i, btn in enumerate(self.buttons):
                if btn.geometry().contains(event.pos()) and btn.isVisible():
                    # Vérifier que c'est un clip et pas un bouton spécial
                    label = self.button_labels[i] if i < len(self.button_labels) else ""
                    special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
                    if label not in special_buttons:
                        # Démarrer le drag
                        self.drag_active = True
                        self.dragged_button_index = i
                        self.drop_indicator_angle = None
                        self.drop_target_info = None
                        # Changer le curseur
                        self.setCursor(Qt.CursorShape.ClosedHandCursor)
                        self.update()
                        return
        
        if not any(btn.geometry().contains(event.pos()) for btn in self.buttons):
            # Masquer tous les badges
            for badge in self.action_badges.values():
                badge.setVisible(False)
            # Masquer la fenêtre tooltip
            self.tooltip_window.hide()
            self.handle_click_outside()
    
    def mouseReleaseEvent(self, event):
        """Gère la fin du drag en mode réordonnancement"""
        if self.drag_active and event.button() == Qt.MouseButton.LeftButton:
            # Libérer la capture de la souris
            self.releaseMouse()
            
            # Fin du drag
            if self.drop_target_info is not None and self.dragged_button_index is not None:
                # drop_target_info contient (target_index, insert_before, target_action)
                target_index, insert_before, target_action = self.drop_target_info
                
                # Récupérer les alias
                source_alias = self.button_labels[self.dragged_button_index] if self.dragged_button_index < len(self.button_labels) else None
                target_alias = self.button_labels[target_index] if target_index < len(self.button_labels) else None
                
                if source_alias and target_alias and source_alias != target_alias:
                    # Effectuer le déplacement via l'app_instance
                    if self.app_instance:
                        from utils import move_clip_in_json
                        success = move_clip_in_json(
                            self.app_instance.clip_notes_file_json,
                            source_alias,
                            target_alias,
                            insert_before,
                            new_action=target_action  # Passer la nouvelle action
                        )
                        if success:
                            # Réinitialiser l'état du drag AVANT de rafraîchir
                            self.drag_active = False
                            self.drag_pending = False
                            self.drag_start_pos = None
                            self.dragged_button_index = None
                            self.drop_indicator_angle = None
                            self.drop_target_info = None
                            self.hovered_action = None
                            self.current_grabed_clip_label = None
                            self.setCursor(Qt.CursorShape.ArrowCursor)
                            # Masquer les badges
                            for badge in self.action_badges.values():
                                badge.setVisible(False)
                            
                            # Afficher un message de confirmation
                            self.tooltip_window.show_message("✓ Clip déplacé", 1000)
                            self.update_tooltip_position()
                            # Rafraîchir le menu selon le mode
                            if self.reorder_mode:
                                self.app_instance.reorder_clip_mode(self.x, self.y)
                            else:
                                self.app_instance.refresh_menu()
                            return
            
            # Réinitialiser l'état du drag
            self.drag_active = False
            self.drag_pending = False
            self.drag_start_pos = None
            self.dragged_button_index = None
            self.drop_indicator_angle = None
            self.drop_target_info = None
            self.hovered_action = None
            self.current_grabed_clip_label = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Masquer les badges
            for badge in self.action_badges.values():
                badge.setVisible(False)
            self.update()
    
    def leaveEvent(self, event):
        """Efface l'icône centrale quand la souris quitte le widget"""
        if self.show_central_icon and self.central_icon is not None:
            self.central_icon = None
            self.hovered_button_index = None
            self.update()
        
        # Sortie de zone spéciale si on était dedans
        if self.mouse_in_special_zone:
            self.mouse_in_special_zone = False
            self.on_leave_special_zone()
        
        # Annuler le drag si en cours
        if self.drag_active or self.drag_pending:
            if self.drag_active:
                self.releaseMouse()
            self.drag_active = False
            self.drag_pending = False
            self.drag_start_pos = None
            self.dragged_button_index = None
            self.drop_indicator_angle = None
            self.drop_target_info = None
            self.current_grabed_clip_label = None
            self.hovered_action = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Masquer les badges
            for badge in self.action_badges.values():
                badge.setVisible(False)
            self.update()

        
    def mouseMoveEvent(self, event):
        """Détecte quelle action est survolée par la souris (zone angulaire complète)
        et gère également la détection des zones spéciales pour l'expand/collapse"""
        
        # === GESTION DU DRAG EN COURS (grabMouse actif) ===
        if self.drag_active:
            # Calculer l'angle de la souris
            center = self.rect().center()
            dx = event.pos().x() - center.x()
            dy = event.pos().y() - center.y()
            
            angle_rad = math.atan2(dy, dx)
            if angle_rad < 0:
                angle_rad += 2 * math.pi
            angle_deg = math.degrees(angle_rad)
            
            # Obtenir les boutons visibles
            visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
            num_visible = len(visible_indices)
            
            if num_visible > 0:
                self._update_drop_indicator(angle_deg, visible_indices, num_visible)
                self.update()
            return  # Pas de gestion de hover pendant le drag
        
        if not self.buttons:
            return
        
        # Obtenir les boutons visibles
        visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
        if not visible_indices:
            return
        num_visible = len(visible_indices)
        
        # Calculer la position relative au centre
        center = self.rect().center()
        dx = event.pos().x() - center.x()
        dy = event.pos().y() - center.y()
        # Calculer la distance au centre
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Calculer l'angle de la souris (0° = droite, sens horaire)
        angle_rad = math.atan2(dy, dx)
        
        # Normaliser pour être positif (0 à 2π)
        if angle_rad < 0:
            angle_rad += 2 * math.pi
        
        # Convertir en degrés
        angle_deg = math.degrees(angle_rad)
        
        # Si on est trop près du centre ou au-delà de la zone externe, pas de hover
        if distance < 30 or distance > self.radius + self.btn_size + 10:
            if self.hovered_action is not None or self.central_icon is not None:
                self.hovered_action = None
                self.hovered_button_index = None
                self.central_icon = None
                # Masquer tous les badges
                for badge in self.action_badges.values():
                    badge.setVisible(False)
                self.update()
            # Sortie de zone spéciale si on était dedans
            if self.mouse_in_special_zone:
                self.mouse_in_special_zone = False
                self.on_leave_special_zone()
            return
        
        # === GESTION DE LA ZONE SPÉCIALE (expand/collapse) ===
        in_special_zone = self.is_angle_in_special_zone(angle_deg)
        
        if in_special_zone and not self.mouse_in_special_zone:
            # On entre dans la zone spéciale
            self.mouse_in_special_zone = True
            self.on_enter_special_zone()
        elif not in_special_zone and self.mouse_in_special_zone:
            # On sort de la zone spéciale
            self.mouse_in_special_zone = False
            self.on_leave_special_zone()
        
        # === GESTION DES HOVERS D'ACTIONS (basé sur boutons VISIBLES) ===
        # Trouver l'index du bouton VISIBLE correspondant à cet angle
        angle_step = 360 / num_visible
        visible_pos = int(round(angle_deg / angle_step)) % num_visible
        # Convertir la position visible en index réel du bouton
        button_index = visible_indices[visible_pos]
        # Récupérer l'action de ce bouton
        hovered_action = None
        if button_index < len(self.button_actions):
            hovered_action = self.button_actions[button_index]
        
        # Mettre à jour si l'action survolée a changé
        if hovered_action != self.hovered_action:
            self.hovered_action = hovered_action
            # Masquer tous les badges d'abord
            for badge in self.action_badges.values():
                badge.setVisible(False)
            
            # Si une action est survolée, calculer la position et afficher son badge
            if self.hovered_action and self.hovered_action in self.action_badges:
                # Trouver tous les indices des boutons VISIBLES ayant cette action
                indices_visible_pos = [pos for pos, idx in enumerate(visible_indices) 
                                       if idx < len(self.button_actions) and self.button_actions[idx] == self.hovered_action]
                
                if indices_visible_pos:
                    # Calculer l'angle moyen de tous ces boutons avec moyenne vectorielle
                    angles_rad = [math.radians(pos * angle_step) for pos in indices_visible_pos]
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
                    badge = self.action_badges[self.hovered_action]
                    badge.move(int(badge_x - badge.width() / 2), int(badge_y - badge.height() / 2))
                    badge.setVisible(True)
            self.update()
    
    def _update_drop_indicator(self, mouse_angle_deg, visible_indices, num_visible):
        """
        Calcule la position de l'indicateur de drop pendant un drag.
        L'indicateur apparaît entre deux boutons adjacents, ou avant le premier / après le dernier.
        Permet de changer l'action du clip en le déplaçant vers une autre zone.
        Met à jour hovered_action en temps réel pour refléter la zone sous la souris.
        
        Args:
            mouse_angle_deg: Angle de la souris en degrés (0° = droite)
            visible_indices: Liste des indices des boutons visibles
            num_visible: Nombre de boutons visibles
        """
        if not self.drag_active or self.dragged_button_index is None:
            return
        
        # Boutons spéciaux à ignorer
        special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
        
        # Calculer l'angle par bouton visible
        angle_step = 360 / num_visible
        
        # === 1. Mettre à jour hovered_action en fonction de l'angle de la souris ===
        # Trouver quel bouton est sous l'angle de la souris
        old_hovered_action = self.hovered_action
        for pos, btn_index in enumerate(visible_indices):
            button_angle = pos * angle_step
            # Calculer la distance angulaire
            dist = abs(button_angle - mouse_angle_deg)
            if dist > 180:
                dist = 360 - dist
            # Si la souris est dans la zone de ce bouton (demi-angle de chaque côté)
            if dist < angle_step / 2:
                action = self.button_actions[btn_index] if btn_index < len(self.button_actions) else None
                if action is not None:
                    self.hovered_action = action
                break
        
        # === 1b. Afficher le badge de l'action survolée (comme en mode normal) ===
        if self.hovered_action != old_hovered_action:
            # Masquer tous les badges d'abord
            for badge in self.action_badges.values():
                badge.setVisible(False)
            
            # Si une action est survolée, calculer la position et afficher son badge
            if self.hovered_action and self.hovered_action in self.action_badges:
                # Trouver tous les indices des boutons VISIBLES ayant cette action
                indices_visible_pos = [pos for pos, idx in enumerate(visible_indices) 
                                       if idx < len(self.button_actions) and self.button_actions[idx] == self.hovered_action]
                
                if indices_visible_pos:
                    # Calculer l'angle moyen de tous ces boutons avec moyenne vectorielle
                    angles_rad = [math.radians(pos * angle_step) for pos in indices_visible_pos]
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
                    badge = self.action_badges[self.hovered_action]
                    badge.move(int(badge_x - badge.width() / 2), int(badge_y - badge.height() / 2))
                    badge.setVisible(True)
        
        # === 2. Trouver tous les clips (pas les boutons spéciaux) ===
        all_clips = []
        for pos, btn_index in enumerate(visible_indices):
            label = self.button_labels[btn_index] if btn_index < len(self.button_labels) else ""
            action = self.button_actions[btn_index] if btn_index < len(self.button_actions) else None
            if label not in special_buttons and action is not None:
                all_clips.append((btn_index, pos, action))
        
        if len(all_clips) < 1:
            # Pas de clips pour réordonner
            self.drop_indicator_angle = None
            self.drop_target_info = None
            return
        
        # === 3. Calculer toutes les positions de drop possibles ===
        drop_positions = []
        
        # Filtrer les clips sans celui qu'on drag
        clips_without_dragged = [(btn_index, pos, action) for btn_index, pos, action in all_clips 
                                  if btn_index != self.dragged_button_index]
        
        if not clips_without_dragged:
            self.drop_indicator_angle = None
            self.drop_target_info = None
            return
        
        # Pour chaque paire de clips adjacents
        for i in range(len(clips_without_dragged)):
            curr_btn_index, curr_pos, curr_action = clips_without_dragged[i]
            next_i = (i + 1) % len(clips_without_dragged)
            next_btn_index, next_pos, next_action = clips_without_dragged[next_i]
            
            # Calculer les angles
            curr_angle = curr_pos * angle_step
            next_angle = next_pos * angle_step
            
            # Gérer le passage par 0°
            diff = next_angle - curr_angle
            if diff > 180:
                diff -= 360
            elif diff < -180:
                diff += 360
            
            if curr_action == next_action:
                # Même zone : une seule position au milieu
                indicator_angle = (curr_angle + diff / 2) % 360
                drop_positions.append((indicator_angle, next_btn_index, True, curr_action))
            else:
                # Zones différentes : deux positions distinctes
                # Position pour "fin de zone courante" (1/3 de l'espace)
                indicator_end_curr = (curr_angle + diff / 3) % 360
                drop_positions.append((indicator_end_curr, curr_btn_index, False, curr_action))
                
                # Position pour "début de zone suivante" (2/3 de l'espace)
                indicator_start_next = (curr_angle + 2 * diff / 3) % 360
                drop_positions.append((indicator_start_next, next_btn_index, True, next_action))
        
        # === 4. Ajouter des positions explicites AVANT le premier clip et APRÈS le dernier ===
        if len(clips_without_dragged) == 1:
            # Un seul clip : ajouter des positions avant et après
            only_btn_index, only_pos, only_action = clips_without_dragged[0]
            only_angle = only_pos * angle_step
            
            # Position avant
            indicator_before = (only_angle - angle_step / 2) % 360
            drop_positions.append((indicator_before, only_btn_index, True, only_action))
            
            # Position après
            indicator_after = (only_angle + angle_step / 2) % 360
            drop_positions.append((indicator_after, only_btn_index, False, only_action))
        else:
            # Plusieurs clips : ajouter des positions aux extrémités absolues
            # Trouver le premier et dernier clip (par position sur le cercle)
            sorted_by_pos = sorted(clips_without_dragged, key=lambda x: x[1])
            first_btn_index, first_pos, first_action = sorted_by_pos[0]
            last_btn_index, last_pos, last_action = sorted_by_pos[-1]
            
            first_angle = first_pos * angle_step
            last_angle = last_pos * angle_step
            
            # Position AVANT le tout premier clip (juste avant lui)
            indicator_before_first = (first_angle - angle_step * 0.4) % 360
            drop_positions.append((indicator_before_first, first_btn_index, True, first_action))
            
            # Position APRÈS le tout dernier clip (juste après lui)
            # IMPORTANT: Toujours ajouter cette position pour permettre de mettre un clip en dernier
            indicator_after_last = (last_angle + angle_step * 0.4) % 360
            drop_positions.append((indicator_after_last, last_btn_index, False, last_action))
        
        # === 5. Trouver la position de drop la plus proche de la souris ===
        best_indicator_angle = None
        best_target_info = None
        min_distance = float('inf')
        
        for indicator_angle, btn_index, insert_before, action in drop_positions:
            dist = abs(indicator_angle - mouse_angle_deg)
            if dist > 180:
                dist = 360 - dist
            
            if dist < min_distance:
                min_distance = dist
                best_indicator_angle = indicator_angle
                best_target_info = (btn_index, insert_before, action)
        
        # Afficher l'indicateur si la souris est assez proche
        if min_distance < angle_step * 0.8:
            self.drop_indicator_angle = best_indicator_angle
            self.drop_target_info = best_target_info
        else:
            self.drop_indicator_angle = None
            self.drop_target_info = None
    
    def handle_key_left(self):
        """Gère la flèche droite"""
        if not self.buttons:
            return
        print(len(self.buttons))
        print(self.focused_index)
        if self.focused_index == len(self.buttons) - 1:
            self.start_special_reveal_animation()
        if self.focused_index == self.nb_icons_menu - 1:
            self.start_special_hide_animation()
        # Première utilisation : initialiser le focus
        if not self.keyboard_used:
            self.keyboard_used = True
            self.initialize_focus()
        else:
            # Aller au bouton suivant (sens horaire)
            self.focused_index = (self.focused_index + 1) % len(self.buttons)
        
        self.show_focused_button_info()
        self.update()
    
    def handle_key_right(self):
        """Gère la flèche gauche"""
        if not self.buttons:
            return
        print(self.focused_index)
        if self.focused_index == self.nb_icons_menu:
            self.start_special_reveal_animation()
        if self.focused_index == 0:
            self.start_special_hide_animation()
        # Première utilisation : initialiser le focus
        if not self.keyboard_used:
            self.keyboard_used = True
            self.initialize_focus()
        else:
            # Aller au bouton précédent (sens anti-horaire)
            self.focused_index = (self.focused_index - 1) % len(self.buttons)
        
        self.show_focused_button_info()
        self.update()
    
    def handle_key_enter(self):
        """Gère la touche Entrée"""
        if 0 <= self.focused_index < len(self.buttons):
            self.buttons[self.focused_index].click()
    
    def handle_key_escape(self):
        """Gère la touche Escape"""
        self.handle_click_outside()
    
    def initialize_focus(self):
        """Initialise le focus sur le premier clip ou sur ➕"""
        # Les boutons spéciaux varient selon nb_icons_menu (4, 5 ou 6 boutons)
        # S'il y a plus de boutons que le nombre d'icônes fixes, les clips commencent après
        button_mumber = self.nb_icons_menu
        if len(self.buttons) > button_mumber:
            # Il y a des clips, aller au premier clip
            self.focused_index = button_mumber
        else:
            # Pas de clips, trouver le bouton ➕
            for i, label in enumerate(self.button_labels):
                if label == "➕":
                    self.focused_index = i
                    break
    
    def show_focused_button_info(self):
        """Affiche les infos du bouton focusé"""
        if not (0 <= self.focused_index < len(self.buttons)):
            return
        
        # Afficher le tooltip
        focused_button = self.buttons[self.focused_index]
        if focused_button in self.tooltips:
            tooltip_data = self.tooltips[focused_button]
            # Supporter l'ancien format (string) et le nouveau (tuple)
            if isinstance(tooltip_data, tuple):
                tooltip_text, tooltip_html = tooltip_data
            else:
                tooltip_text, tooltip_html = tooltip_data, None
            self.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
            self.update_tooltip_position()
        
        # Afficher l'icône centrale si activé
        if self.show_central_icon and self.focused_index < len(self.button_labels):
            label = self.button_labels[self.focused_index]
            if "/" in label:
                self.central_icon = image_pixmap(label, 64)
            elif is_emoji(label):
                self.central_icon = emoji_pixmap(label, 48)
            else:
                self.central_icon = text_pixmap(label, 48)
    
    def reveal_buttons(self):
        # Réinitialiser l'état des boutons spéciaux
        self.special_buttons_revealed = False
        self.special_animating = False
        self.mouse_in_special_zone = False
        
        for i, btn in enumerate(self.buttons):
            # Les boutons spéciaux (sauf ➕) restent cachés jusqu'au hover sur ➕
            if i in self.special_button_indices:
                btn.setVisible(False)
            else:
                btn.setVisible(True)
        
        # Repositionner les boutons visibles pour que le cercle soit adapté
        self.reposition_visible_buttons()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        # Appliquer le scale au diamètre
        scaled_diameter = int(self.diameter * self.scale_factor)
        
        # Le cercle du menu radial (plus petit que le widget)
        circle_rect = QRect(
            (self.widget_size - scaled_diameter) // 2,
            (self.widget_size - scaled_diameter) // 2,
            scaled_diameter,
            scaled_diameter
        )

        # Dessiner le fond global avec opacité contrôlée par MENU_OPACITY
        # _widget_opacity va de 0.0 à 1.0, on le convertit en alpha 0-255
        background_alpha = int(255 * self.widget_opacity)
        painter.setBrush(QColor(*self.menu_background_color, background_alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(circle_rect)
        
        # Dessiner les zones colorées seulement pour les boutons VISIBLES
        # Les zones sont positionnées selon la position dans le cercle des visibles
        action_colors_base = {
            action: QColor(*rgb, self.zone_basic_opacity)
            for action, rgb in self.action_zone_colors.items()
        }

        action_colors_hover = {
            action: QColor(*rgb, self.zone_hover_opacity)
            for action, rgb in self.action_zone_colors.items()
        }
        
        # Obtenir les indices des boutons visibles
        visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
        
        if visible_indices:
            angle_step = 360 / len(visible_indices)
            
            # Dessiner les zones seulement pour les boutons visibles
            for pos, btn_index in enumerate(visible_indices):
                action = self.button_actions[btn_index] if btn_index < len(self.button_actions) else None
                
                if action in action_colors_base:
                    # Choisir la couleur selon si c'est survolé ou non
                    if action == self.hovered_action:
                        color = action_colors_hover[action]
                    else:
                        color = action_colors_base[action]
                    
                    # Calculer l'angle basé sur la position dans les visibles
                    button_angle = pos * angle_step
                    
                    # Convertir en angle Qt (0° à droite, sens anti-horaire)
                    start_angle = -button_angle - (angle_step / 2)
                    
                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    # drawPie utilise des "16èmes de degrés"
                    painter.drawPie(circle_rect, int(start_angle * 16), int(angle_step * 16))
        
        # === INDICATEUR DE DROP (mode réordonnancement) ===
        # if self.drag_active and self.drop_indicator_angle is not None:
        #     # Dessiner une ligne blanche radiale à l'angle de drop
        #     indicator_angle_rad = math.radians(self.drop_indicator_angle)
            
        #     # Points de la ligne (du centre vers l'extérieur du cercle)
        #     inner_radius = 35 * self.scale_factor  # Commencer un peu après le centre
        #     outer_radius = (self.radius + self.btn_size // 2) * self.scale_factor
            
        #     x1 = center.x() + inner_radius * math.cos(indicator_angle_rad)
        #     y1 = center.y() + inner_radius * math.sin(indicator_angle_rad)
        #     x2 = center.x() + outer_radius * math.cos(indicator_angle_rad)
        #     y2 = center.y() + outer_radius * math.sin(indicator_angle_rad)
            
        #     # Dessiner la ligne blanche épaisse avec effet glow
        #     # D'abord un glow blanc semi-transparent
        #     glow_pen = QPen(QColor(255, 255, 255, 80))
        #     glow_pen.setWidth(12)
        #     glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        #     painter.setPen(glow_pen)
        #     painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
        #     # Puis la ligne blanche principale
        #     indicator_pen = QPen(QColor(255, 255, 255, 230))
        #     indicator_pen.setWidth(6)
        #     indicator_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        #     painter.setPen(indicator_pen)
        #     painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        # if not self.drag_active or self.drop_indicator_angle is None:
        #     return

        # painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # indicator_angle_rad = math.radians(self.drop_indicator_angle)

        # # --- Paramètres ---
        # circle_diameter = 45 * self.scale_factor
        # circle_radius = circle_diameter / 2

        # indicator_offset = 30 * self.scale_factor  # distance avant l'extrémité

        # outer_radius = (self.radius + self.btn_size // 2) * self.scale_factor
        # indicator_radius_pos = outer_radius - indicator_offset

        # # --- Position du rond ---
        # cx = center.x() + indicator_radius_pos * math.cos(indicator_angle_rad)
        # cy = center.y() + indicator_radius_pos * math.sin(indicator_angle_rad)

        # circle_rect = QRectF(
        #     cx - circle_radius,
        #     cy - circle_radius,
        #     circle_diameter,
        #     circle_diameter
        # )
        # if not self.drag_active or self.drop_indicator_angle is None:
        #     return

        # painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # indicator_angle_rad = math.radians(self.drop_indicator_angle)

        # # --- Paramètres du rond ---
        # circle_diameter = 45 * self.scale_factor
        # circle_radius = circle_diameter / 2

        # indicator_offset = 30 * self.scale_factor  # distance avant l'extrémité
        # outer_radius = (self.radius + self.btn_size // 2) * self.scale_factor
        # indicator_radius_pos = outer_radius - indicator_offset

        # # --- Position du centre du rond ---
        # cx = center.x() + indicator_radius_pos * math.cos(indicator_angle_rad)
        # cy = center.y() + indicator_radius_pos * math.sin(indicator_angle_rad)

        # circle_rect = QRectF(
        #     cx - circle_radius,
        #     cy - circle_radius,
        #     circle_diameter,
        #     circle_diameter
        # )

        # # --- Glow ---
        # glow_pen = QPen(QColor(255, 255, 255, 80))
        # glow_pen.setWidth(6)
        # painter.setPen(glow_pen)
        # painter.setBrush(Qt.BrushStyle.NoBrush)
        # painter.drawEllipse(circle_rect)

        # # --- Cercle principal ---
        # painter.setPen(Qt.PenStyle.NoPen)
        # painter.setBrush(QColor(255, 255, 255, 230))
        # painter.drawEllipse(circle_rect)

        # # =========================================================
        # # === CONTENU : IMAGE ou TEXTE (sans rescale)
        # # =========================================================

        # # --- Image ---
        # if hasattr(self, "drop_indicator_icon") and self.drop_indicator_icon:
        #     pixmap = self.drop_indicator_icon
        #     if not pixmap.isNull():
        #         painter.drawPixmap(
        #             int(cx - pixmap.width() / 2),
        #             int(cy - pixmap.height() / 2),
        #             pixmap
        #         )

        # # --- Texte ---
        # elif hasattr(self, "drop_indicator_text") and self.drop_indicator_text:
        #     painter.setPen(QColor(0, 0, 0))  # ou blanc selon ton UX

        #     if hasattr(self, "drop_indicator_font"):
        #         painter.setFont(self.drop_indicator_font)

        #     text_rect = QRectF(
        #         cx - circle_radius,
        #         cy - circle_radius,
        #         circle_diameter,
        #         circle_diameter
        #     )

        #     painter.drawText(
        #         text_rect,
        #         Qt.AlignmentFlag.AlignCenter,
        #         self.drop_indicator_text
        #     )


        # # --- Glow ---
        # glow_pen = QPen(QColor(255, 255, 255, 80))
        # glow_pen.setWidth(6)
        # glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        # painter.setPen(glow_pen)
        # painter.setBrush(Qt.BrushStyle.NoBrush)
        # painter.drawEllipse(circle_rect)

        # # --- Cercle principal ---
        # painter.setPen(Qt.PenStyle.NoPen)
        # painter.setBrush(QColor(255, 255, 255, 230))
        # painter.drawEllipse(circle_rect)

        # # --- Image au centre ---
        # if hasattr(self, "drop_indicator_icon"):
        #     pixmap = QPixmap("/home/simon/repo_seb_dethyre/clip_notes/thumbnails/4697a16f14fd6d08a8ea3301b841a18c.png")
        #     if not pixmap.isNull():
        #         icon_size = circle_diameter * 0.6
        #         scaled = pixmap.scaled(
        #             int(icon_size),
        #             int(icon_size),
        #             Qt.AspectRatioMode.KeepAspectRatio,
        #             Qt.TransformationMode.SmoothTransformation
        #         )

        #         painter.drawPixmap(
        #             int(cx - scaled.width() / 2),
        #             int(cy - scaled.height() / 2),
        #             scaled
        #         )
        
        # === INDICATEUR DE DROP (rond avec icône) ===
        if self.drag_active and self.drop_indicator_angle is not None:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            indicator_angle_rad = math.radians(self.drop_indicator_angle)

            # --- Paramètres du rond ---
            circle_diameter = 45 * self.scale_factor
            circle_radius = circle_diameter / 2

            indicator_offset = 30 * self.scale_factor
            outer_radius = (self.radius + self.btn_size // 2) * self.scale_factor
            indicator_radius_pos = outer_radius - indicator_offset

            # --- Position du centre ---
            cx = center.x() + indicator_radius_pos * math.cos(indicator_angle_rad)
            cy = center.y() + indicator_radius_pos * math.sin(indicator_angle_rad)

            circle_rect = QRectF(
                cx - circle_radius,
                cy - circle_radius,
                circle_diameter,
                circle_diameter
            )

            # --- Glow ---
            glow_pen = QPen(QColor(255, 255, 255, 80))
            glow_pen.setWidth(6)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(circle_rect)

            # --- Cercle principal ---
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))
            painter.drawEllipse(circle_rect)

            # =================================================
            # === CONTENU : IMAGE ou TEXTE depuis la CHAÎNE
            # =================================================

            label = getattr(self, "current_grabed_clip_label", None)

            if label:
                label_lower = label.lower()

                # --- Cas IMAGE ---
                if (
                    "/" in label
                    and (label_lower.endswith(".png") or
                        label_lower.endswith(".jpg") or
                        label_lower.endswith(".jpeg"))
                ):
                    pixmap = QPixmap(label)
                    if not pixmap.isNull():
                        max_size = int(circle_diameter * 0.85)  # marge visuelle

                        src_w = pixmap.width()
                        src_h = pixmap.height()

                        # --- Cas icône : pas de scale ---
                        if src_w <= max_size and src_h <= max_size:
                            draw_pixmap = pixmap

                        # --- Cas image : miniature ---
                        else:
                            draw_pixmap = pixmap.scaled(
                                max_size,
                                max_size,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation
                            )

                        painter.drawPixmap(
                            int(cx - draw_pixmap.width() / 2),
                            int(cy - draw_pixmap.height() / 2),
                            draw_pixmap
                        )

                # --- Cas TEXTE ---
                else:
                    painter.setPen(QColor(0, 0, 0))  # ajuste si besoin

                    text_rect = QRectF(
                        cx - circle_radius,
                        cy - circle_radius,
                        circle_diameter,
                        circle_diameter
                    )

                    painter.drawText(
                        text_rect,
                        Qt.AlignmentFlag.AlignCenter,
                        label
                    )


        if self.neon_enabled:
            scaled_neon_radius = self.neon_radius * self.scale_factor
            gradient = QRadialGradient(QPointF(center), scaled_neon_radius)
            gradient.setColorAt(0.0, couleur_avec_opacite(self.neon_color, self.neon_opacity))
            gradient.setColorAt(1.0, couleur_avec_opacite(self.neon_color, 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(center), scaled_neon_radius, scaled_neon_radius)

        if self.central_icon:
            # Afficher l'icône centrale du bouton survolé
            icon_size = int(64 * self.scale_factor)  # Taille scalée
            icon_x = center.x() - icon_size // 2
            icon_y = center.y() - icon_size // 2
            
            # Créer un pixmap scalé
            scaled_icon = self.central_icon.scaled(
                icon_size, 
                icon_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(int(icon_x), int(icon_y), scaled_icon)
        elif self.central_text:
            # Afficher le texte central (mode édition/suppression)
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", int(24 * self.scale_factor))
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.central_text)
        
        # Dessiner le cercle de focus (seulement si le clavier a été utilisé)
        if self.focused_index >= 0 and self.focused_index < len(self.buttons):
            # Vérifier si le bouton focusé est visible
            if self.buttons[self.focused_index].isVisible():
                # Trouver la position du bouton focusé parmi les visibles
                visible_indices = [i for i, btn in enumerate(self.buttons) if btn.isVisible()]
                if self.focused_index in visible_indices:
                    pos_in_visible = visible_indices.index(self.focused_index)
                    angle_step = 360 / len(visible_indices)
                    angle = math.radians(pos_in_visible * angle_step)
                    center_offset = self.widget_size // 2
                    
                    # Position du centre du bouton focusé (scalée)
                    btn_center_x = center_offset + (self.radius * math.cos(angle)) * self.scale_factor
                    btn_center_y = center_offset + (self.radius * math.sin(angle)) * self.scale_factor
                    
                    # Rayon du cercle de focus
                    focus_radius = int((self.btn_size // 2 + 5) * self.scale_factor)
                    
                    # Dessiner le cercle de fond
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(255, 255, 255, 60))
                    painter.drawEllipse(QPointF(btn_center_x, btn_center_y), focus_radius, focus_radius)
                    
                    # Dessiner le contour
                    pen = QPen(QColor(255, 255, 255, 200))
                    pen.setWidth(3)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(btn_center_x, btn_center_y), focus_radius, focus_radius)

    def handle_click_outside(self):
        """Gère le clic en dehors du menu (sur le tracker ou au centre)"""
        # Effacer l'icône centrale
        self.central_icon = None
        
        # Fermer le sous-menu hover s'il existe et n'est pas déjà détruit
        if self.hover_submenu is not None:
            try:
                # Tester si l'objet C++ existe encore
                self.hover_submenu.isVisible()
                self.hover_submenu.close()
            except RuntimeError:
                # L'objet a déjà été détruit
                pass
            self.hover_submenu = None
        
        # Si on est en mode modification, suppression, stockage ou réordonnancement, revenir au menu de base
        if self.nb_icons_menu == 4:
            button_mumber = 3
        elif self.nb_icons_menu == 5:
            button_mumber = 2
        elif self.nb_icons_menu == 6:
            button_mumber = 1
        if self.app_instance and (self.app_instance.update_mode or self.app_instance.delete_mode or self.app_instance.store_mode or self.app_instance.reorder_mode):
            self.app_instance.update_mode = False
            self.app_instance.delete_mode = False
            self.app_instance.store_mode = False
            self.app_instance.reorder_mode = False
            # Réinitialiser aussi l'état de drag du RadialMenu
            self.reorder_mode = False
            self.drag_active = False
            self.dragged_button_index = None
            self.drop_indicator_angle = None
            self.drop_target_info = None
            self.app_instance.refresh_menu()
        # Si on est dans le menu de sélection 📦 (2 boutons seulement)
        elif len(self.buttons) == button_mumber:
            self.app_instance.refresh_menu()
        else:
            # Sinon, fermer normalement
            self.close_with_animation()

    def animate_open(self):
        # Masquer les badges pendant l'animation
        for badge in self.action_badges.values():
            badge.setVisible(False)
        
        # Masquer la fenêtre tooltip pendant l'animation
        self.tooltip_window.hide()
        
        # Configurer le tracker pour qu'il ferme ce menu quand on clique dessus
        if self.tracker:
            self.tracker.on_click_callback = self.handle_click_outside
        
        # Calculer le rayon initial basé sur les boutons qui seront visibles
        # (tous sauf les spéciaux, sauf ➕)
        initial_visible_count = len(self.buttons) - len(self.special_button_indices)
        if initial_visible_count <= 7:
            self.radius = 80
        else:
            self.radius = int(80 * (initial_visible_count / 7))
        self.diameter = 2 * (self.radius + self.btn_size)
        self.widget_size = self.diameter + 100
        self.resize(self.widget_size, self.widget_size)
        self.move(self.x - self.widget_size // 2, self.y - self.widget_size // 2)
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)  # Réduit de 350ms à 250ms
        self.anim.setStartValue(0.1)  # Partir de 10% de la taille, pas 0
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def update_scale(value):
            self.scale_factor = value
            self.apply_scale()
        
        self.anim.valueChanged.connect(update_scale)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()
    
    def apply_scale(self):
        """Trigger un repaint avec le nouveau scale factor"""
        # Le scale sera appliqué dans paintEvent via une transformation
        # On met aussi à jour la position/taille des boutons
        if self.scale_factor > 0:
            for i, btn in enumerate(self.buttons):
                # Repositionner et redimensionner chaque bouton selon le scale
                angle_step = 360 / len(self.buttons)
                angle = math.radians(i * angle_step)
                center_offset = self.widget_size // 2
                
                # Position originale
                orig_bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
                orig_by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
                
                # Appliquer le scale depuis le centre
                scaled_bx = center_offset + (orig_bx - center_offset) * self.scale_factor
                scaled_by = center_offset + (orig_by - center_offset) * self.scale_factor
                scaled_size = int(self.btn_size * self.scale_factor)
                
                btn.move(int(scaled_bx), int(scaled_by))
                btn.setFixedSize(scaled_size, scaled_size)
                
                # Adapter la taille de l'icône selon le type
                label = self.button_labels[i] if i < len(self.button_labels) else ""
                if "/" in label:
                    # Image - légèrement plus petit pour voir le hover
                    btn.setIconSize(QSize(int(48 * self.scale_factor), int(48 * self.scale_factor)))
                else:
                    # Emoji ou texte - taille d'icône standard
                    btn.setIconSize(QSize(int(32 * self.scale_factor), int(32 * self.scale_factor)))
                
                # Mettre à jour le style avec le border-radius scalé
                special_buttons = self.special_buttons_by_numbers[self.nb_icons_menu]
                if label in special_buttons:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border-radius: {int((self.btn_size // 2) * self.scale_factor)}px;
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
                            border-radius: {int((self.btn_size // 2) * self.scale_factor)}px;
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
                            border-radius: {int((self.btn_size // 2) * self.scale_factor)}px;
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
        self.update_tooltip_position()
    
    def close_with_animation(self):
        self.neon_enabled = False
        
        # Fermer le sous-menu hover s'il existe
        if self.hover_submenu:
            self.hover_submenu.close()
            self.hover_submenu = None
        
        # Masquer les badges pendant l'animation
        for badge in self.action_badges.values():
            badge.setVisible(False)
        
        # Masquer la fenêtre tooltip
        self.tooltip_window.hide()
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.1)  # Finir à 10% de la taille, pas 0
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        
        def update_scale(value):
            self.scale_factor = value
            self.apply_scale()
        
        self.anim.valueChanged.connect(update_scale)
        self.anim.finished.connect(self.on_close_finished)
        self.anim.start()
    
    def on_close_finished(self):
        """Appelé quand l'animation de fermeture est terminée"""
        # Désinstaller le listener clavier
        if hasattr(self, 'keyboard_listener'):
            QApplication.instance().removeEventFilter(self.keyboard_listener)
        
        # Fermer la fenêtre tooltip
        self.tooltip_window.close()
        if self.tracker:
            self.tracker.close()
        self.close()