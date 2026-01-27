import math
from PyQt6.QtCore import Qt, QEvent, QSize, QRect, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QIcon, QPen
from PyQt6.QtWidgets import QWidget, QPushButton
from utils import *

class HoverSubMenu(QWidget):
    """Sous-menu radial qui apparaît au hover d'un bouton (pour ➖)"""
    
    def __init__(self, center_x, center_y, buttons, parent_menu=None, app_instance=None):
        # Utiliser parent_menu comme parent Qt pour éviter l'erreur Wayland
        super().__init__(parent_menu)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        
        self.parent_menu = parent_menu
        self.app_instance = app_instance
        self.buttons = []
        self.button_labels = []  # Pour stocker les labels des boutons
        self.tooltips = {}
        self.closing = False
        self.central_icon_label = ""  # Icône centrale (vide = pas d'icône)
        
        # Variables pour le drag du groupe depuis le centre
        self.is_group_submenu = False  # Sera mis à True si c'est un sous-menu de groupe
        self.group_alias = None  # Alias du groupe (sera défini après création)
        self.children_data = []  # Données complètes des clips enfants (pour le drag)
        self.drag_pending = False
        self.drag_start_pos = None
        self.drag_threshold = 10  # Pixels minimum pour déclencher un drag
        self.center_radius = 25  # Rayon de la zone centrale pour le drag
        
        # Variables pour le drag d'un clip enfant (sortir du groupe)
        self.dragged_child_index = None  # Index du bouton enfant en cours de drag
        self.dragged_child_button = None  # Référence au bouton en cours de drag
        
        # Connecter le signal destroyed pour nettoyer la référence dans le parent
        self.destroyed.connect(self.on_destroyed)
        
        # Paramètres du sous-menu (plus petit que le menu principal)
        self.btn_size = 55
        self.radius = 38
        self.diameter = 2 * (self.radius + self.btn_size)
        self.widget_size = self.diameter - 54
        
        # Stocker le centre pour le positionnement
        self.center_x = center_x
        self.center_y = center_y
        
        # Positionner le widget pour que son centre soit sur le bouton
        self.target_x = center_x - self.widget_size // 2
        self.target_y = center_y - self.widget_size // 2
        
        self.resize(self.widget_size, self.widget_size)
        self.move(self.target_x, self.target_y)
        
        # Rayon de détection pour la fermeture (cercle englobant les boutons)
        self.detection_radius = self.radius + self.btn_size // 2 + 5  # +5 marge
        
        # Créer les boutons
        self.create_buttons(buttons)
        
        # Animation d'ouverture
        self.scale_factor = 0.1
        self.anim = None
        
        # Navigation clavier
        self.focused_index = -1
    
    def on_destroyed(self):
        """Appelé quand le widget est détruit - nettoie la référence dans le parent"""
        if self.parent_menu and hasattr(self.parent_menu, 'hover_submenu'):
            self.parent_menu.hover_submenu = None
    
    def create_buttons(self, buttons):
        """Crée les boutons du sous-menu"""
        if not buttons:
            return
        
        angle_step = 360 / len(buttons)
        center_offset = self.widget_size // 2
        
        for i, (label, callback, tooltip) in enumerate(buttons):
            # Stocker le label
            self.button_labels.append(label)
            
            # Position du bouton - décalé de 90° pour commencer en haut
            angle = math.radians(i * angle_step - 90)
            bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
            by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
            
            btn = QPushButton("", self)
            btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            
            # Icône - gérer images, emojis et texte (même logique que RadialMenu)
            if "/" in label:
                # C'est un chemin d'image
                btn.setIcon(QIcon(image_pixmap(label, 38)))
                btn.setIconSize(QSize(38, 38))
            elif is_emoji(label):
                btn.setIcon(QIcon(emoji_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            else:
                btn.setIcon(QIcon(text_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            
            # Style différent pour les images
            if "/" in label:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border-radius: {self.btn_size // 2}px;
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                    QPushButton:hover {{
                        background-color: rgba(120, 120, 120, 200);
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(80, 80, 80, 50);
                        border-radius: {self.btn_size // 2}px;
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                    QPushButton:hover {{
                        background-color: rgba(120, 120, 120, 250);
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                """)
            
            btn.setFixedSize(self.btn_size, self.btn_size)
            btn.move(int(bx), int(by))
            btn.clicked.connect(self.make_click_handler(callback))
            btn.installEventFilter(self)
            
            if tooltip:
                self.tooltips[btn] = tooltip
            
            self.buttons.append(btn)
    
    def make_click_handler(self, callback):
        """Crée un handler de clic qui exécute l'action (le callback gère la fermeture)"""
        def handler():
            self.closing = True
            callback()
            # Note: le callback (ex: _storage_action_clips) se charge de fermer le sous-menu
        return handler
    
    def eventFilter(self, watched, event):
        """Gère les événements de hover et drag sur les boutons du sous-menu"""
        if event.type() == QEvent.Type.Enter:
            # Afficher le tooltip dans le parent_menu si disponible
            if watched in self.tooltips and self.parent_menu:
                tooltip_data = self.tooltips[watched]
                # Supporter l'ancien format (string) et le nouveau (tuple)
                if isinstance(tooltip_data, tuple):
                    tooltip_text, tooltip_html = tooltip_data
                else:
                    tooltip_text, tooltip_html = tooltip_data, None
                self.parent_menu.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
                self.parent_menu.update_tooltip_position()

            if watched in self.buttons and self.parent_menu.show_central_icon:
                button_index = self.buttons.index(watched)
                self.hovered_button_index = button_index
                
                # Créer l'icône centrale pour ce bouton (sauf pendant le drag)
                if button_index < len(self.button_labels):
                    label = self.button_labels[button_index]
                    # Créer un pixmap adapté au type de label
                    if "/" in label:
                        # C'est un chemin d'image
                        self.parent_menu.central_icon = image_pixmap(label, 64)
                    elif is_emoji(label):
                        # C'est un emoji
                        self.parent_menu.central_icon = emoji_pixmap(label, 48)
                    else:
                        # C'est du texte simple
                        self.parent_menu.central_icon = text_pixmap(label, 48)
                
        elif event.type() == QEvent.Type.Leave:
            # Masquer le tooltip
            if self.parent_menu:
                self.parent_menu.tooltip_window.hide()
            
            # Effacer l'icône centrale du parent
            if watched in self.buttons and self.parent_menu:
                self.parent_menu.central_icon = None
                self.parent_menu.update()
        
        # === Drag d'un clip enfant (pour le sortir du groupe) ===
        elif event.type() == QEvent.Type.MouseButtonPress and not (self.parent_menu.app_instance.get_update_mode() or self.parent_menu.app_instance.get_delete_mode() or self.parent_menu.app_instance.get_store_mode()):
            if self.is_group_submenu and watched in self.buttons:
                if event.button() == Qt.MouseButton.LeftButton:
                    button_index = self.buttons.index(watched)
                    self.dragged_child_index = button_index
                    self.dragged_child_button = watched
                    self.drag_start_pos = event.pos()
                    self.drag_pending = True
        
        elif event.type() == QEvent.Type.MouseMove:
            if self.drag_pending and self.dragged_child_button is not None:
                if self.drag_start_pos is not None:
                    delta = event.pos() - self.drag_start_pos
                    distance = math.sqrt(delta.x() ** 2 + delta.y() ** 2)
                    
                    if distance > self.drag_threshold:
                        # Seuil atteint - transférer le drag au RadialMenu parent
                        self.start_child_drag()
                        return True
        
        elif event.type() == QEvent.Type.MouseButtonRelease:
            # Reset du drag si on relâche sans avoir atteint le seuil
            if self.dragged_child_button is not None:
                self.dragged_child_index = None
                self.dragged_child_button = None
                self.drag_start_pos = None
                self.drag_pending = False
        
        return super().eventFilter(watched, event)
    
    def enterEvent(self, event):
        """Quand la souris entre dans le sous-menu"""
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Quand la souris quitte le widget - fermer immédiatement"""
        if not self.closing:
            self.close_submenu()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Gère les clics dans le sous-menu"""
        # Vérifier si le clic est sur un bouton
        for btn in self.buttons:
            if btn.geometry().contains(event.pos()):
                # Laisser le bouton gérer le clic
                return super().mousePressEvent(event)
        
        # Si c'est un groupe submenu, vérifier si le clic est au centre
        if self.is_group_submenu and self.group_alias and event.button() == Qt.MouseButton.LeftButton:
            # Calculer la distance au centre
            center = self.rect().center()
            dx = event.pos().x() - center.x()
            dy = event.pos().y() - center.y()
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < self.center_radius:
                if self.app_instance and self.app_instance.get_update_mode():
                    print(self.group_alias)
                    self.app_instance.show_group_edit_dialog(self.group_alias, dx, dy)
                    event.accept()
                    return
                if not (self.parent_menu.app_instance.get_update_mode() or self.parent_menu.app_instance.get_delete_mode() or self.parent_menu.app_instance.get_store_mode()):
                # Clic au centre - préparer le drag du groupe
                    self.drag_pending = True
                    self.drag_start_pos = event.pos()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    event.accept()
                    return
        
        # Clic en dehors des boutons et du centre - ignorer
        event.accept()
    
    def mouseMoveEvent(self, event):
        """Gère le mouvement de la souris pour le drag du groupe et la détection de sortie"""
        # Vérifier si on est hors du cercle de détection
        center = self.rect().center()
        dx = event.pos().x() - center.x()
        dy = event.pos().y() - center.y()
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > self.detection_radius and not self.closing:
            # Souris hors du cercle - fermer immédiatement
            self.close_submenu()
            return
        
        if self.drag_pending and self.drag_start_pos is not None:
            # Calculer la distance parcourue
            delta = event.pos() - self.drag_start_pos
            drag_distance = math.sqrt(delta.x() ** 2 + delta.y() ** 2)
            
            if drag_distance > self.drag_threshold:
                # Seuil atteint - transférer le drag au RadialMenu parent
                self.start_group_drag()
                return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Gère le relâchement de la souris"""
        if self.drag_pending:
            self.drag_pending = False
            self.drag_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)
    
    def start_group_drag(self):
        """Transfère le drag du groupe au RadialMenu parent"""
        if not self.parent_menu or not self.group_alias:
            return
        
        # Trouver l'index du groupe dans le RadialMenu parent
        group_index = None
        for i, label in enumerate(self.parent_menu.button_labels):
            if label == self.group_alias:
                group_index = i
                break
        
        if group_index is None:
            return
        
        # Fermer ce sous-menu
        self.closing = True
        self.parent_menu.hover_submenu = None
        
        # Activer le drag sur le parent
        self.parent_menu.drag_active = True
        self.parent_menu.dragged_button_index = group_index
        self.parent_menu.current_grabed_clip_label = self.group_alias
        self.parent_menu.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.parent_menu.grabMouse()
        
        # Fermer ce widget
        self.close()
    
    def start_child_drag(self):
        """Transfère le drag d'un clip enfant au RadialMenu parent (pour le sortir du groupe)"""
        if not self.parent_menu or not self.group_alias or self.dragged_child_index is None:
            return
        
        # Récupérer les données du clip enfant
        if self.dragged_child_index >= len(self.children_data):
            return
        
        child_data = self.children_data[self.dragged_child_index]
        child_alias = child_data.get('alias', '')
        
        # Fermer ce sous-menu
        self.closing = True
        self.parent_menu.hover_submenu = None
        
        # Stocker les infos du clip enfant en cours de drag sur le parent
        self.parent_menu.drag_active = True
        self.parent_menu.dragged_button_index = None  # Pas un bouton du menu principal
        self.parent_menu.current_grabed_clip_label = child_alias
        self.parent_menu.dragging_child_from_group = True  # Nouveau flag
        self.parent_menu.dragging_child_group_alias = self.group_alias  # Groupe source
        self.parent_menu.dragging_child_data = child_data  # Données du clip
        self.parent_menu.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.parent_menu.grabMouse()
        
        # Fermer ce widget
        self.close()
    
    def close_submenu(self):
        """Ferme le sous-menu immédiatement"""
        if self.closing:
            return
        
        self.closing = True
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            # Effacer l'icône centrale
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()

    def paintEvent(self, event):
        """Dessine le fond du sous-menu"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        
        # Dessiner un cercle de fond semi-transparent
        scaled_diameter = int(self.diameter * self.scale_factor)
        circle_rect = QRect(
            (self.widget_size - scaled_diameter) // 2,
            (self.widget_size - scaled_diameter) // 2,
            scaled_diameter,
            scaled_diameter
        )
        
        # Fond du sous-menu (légèrement plus clair que le menu principal)
        painter.setBrush(QColor(70, 70, 70, 0))
        painter.setPen(QPen(QColor(255, 255, 255, 0), 2))
        painter.drawEllipse(circle_rect)
        
        # === Pour les groupes : afficher l'icône au centre avec indicateur de drag ===
        if self.is_group_submenu and self.group_alias and self.scale_factor > 0.5:
            # Dessiner un cercle central pour indiquer la zone de drag
            drag_zone_radius = int(self.center_radius * self.scale_factor)
            painter.setBrush(QColor(100, 100, 100, 100))
            painter.setPen(QPen(QColor(255, 255, 255, 80), 2))
            painter.drawEllipse(center, drag_zone_radius, drag_zone_radius)
            
            # Dessiner l'icône du groupe au centre
            icon_size = int(28 * self.scale_factor)
            label = self.group_alias
            
            if "/" in label:
                icon_pixmap = image_pixmap(label, icon_size)
            elif is_emoji(label):
                icon_pixmap = emoji_pixmap(label, icon_size)
            else:
                icon_pixmap = text_pixmap(label, icon_size)
            
            painter.drawPixmap(
                center.x() - icon_size // 2,
                center.y() - icon_size // 2,
                icon_pixmap
            )
        # Icône centrale standard (seulement si définie et pas un groupe)
        elif self.central_icon_label and self.scale_factor > 0.5:
            icon_size = int(24 * self.scale_factor)
            if is_emoji(self.central_icon_label):
                icon_pixmap = emoji_pixmap(self.central_icon_label, icon_size)
            else:
                icon_pixmap = text_pixmap(self.central_icon_label, icon_size)
            painter.drawPixmap(
                center.x() - icon_size // 2,
                center.y() - icon_size // 2,
                icon_pixmap
            )
    
    def animate_open(self):
        """Animation d'ouverture du sous-menu"""
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.setStartValue(0.1)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        def update_scale(value):
            self.scale_factor = value
            self.apply_scale()
        
        self.anim.valueChanged.connect(update_scale)
        self.anim.finished.connect(self.on_open_finished)
        self.anim.start()
    
    def apply_scale(self):
        """Applique le facteur d'échelle aux boutons"""
        center_offset = self.widget_size // 2
        angle_step = 360 / len(self.buttons) if self.buttons else 360
        
        for i, btn in enumerate(self.buttons):
            angle = math.radians(i * angle_step - 90)
            
            # Position originale
            orig_bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
            orig_by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
            
            # Appliquer le scale depuis le centre
            scaled_bx = center_offset + (orig_bx - center_offset) * self.scale_factor
            scaled_by = center_offset + (orig_by - center_offset) * self.scale_factor
            scaled_size = int(self.btn_size * self.scale_factor)
            
            btn.move(int(scaled_bx), int(scaled_by))
            btn.setFixedSize(max(1, scaled_size), max(1, scaled_size))
            btn.setIconSize(QSize(int(28 * self.scale_factor), int(28 * self.scale_factor)))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(80, 80, 80, 50);
                    border-radius: {max(1, scaled_size // 2)}px;
                    border: 2px solid rgba(255, 255, 255, 0);
                }}
                QPushButton:hover {{
                    background-color: rgba(120, 120, 120, 250);
                    border: 2px solid rgba(255, 255, 255, 0);
                }}
            """)
        self.update()
    
    def on_open_finished(self):
        """Appelé quand l'animation d'ouverture est terminée"""
        for btn in self.buttons:
            btn.setVisible(True)
    
    # === Navigation clavier ===
    
    def handle_key_right(self):
        """Navigue vers le bouton suivant (sens horaire)"""
        if not self.buttons:
            return
        
        if self.focused_index == -1:
            self.focused_index = 0
        else:
            self.focused_index = (self.focused_index + 1) % len(self.buttons)
        
        self.update_focus_style()
        self.show_focused_tooltip()
    
    def handle_key_left(self):
        """Navigue vers le bouton précédent (sens anti-horaire)"""
        if not self.buttons:
            return
        
        if self.focused_index == -1:
            self.focused_index = len(self.buttons) - 1
        else:
            self.focused_index = (self.focused_index - 1) % len(self.buttons)
        
        self.update_focus_style()
        self.show_focused_tooltip()
    
    def handle_key_enter(self):
        """Active le bouton focusé"""
        if 0 <= self.focused_index < len(self.buttons):
            self.buttons[self.focused_index].click()
    
    def handle_key_escape(self):
        """Ferme le sous-menu et revient au menu principal"""
        self.closing = True
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            # Effacer l'icône centrale
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()
    
    def update_focus_style(self):
        """Met à jour le style des boutons pour montrer le focus"""
        for i, btn in enumerate(self.buttons):
            scaled_size = int(self.btn_size * self.scale_factor) if self.scale_factor else self.btn_size
            if i == self.focused_index:
                # Bouton focusé - bordure plus visible
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(120, 120, 120, 250);
                        border-radius: {self.btn_size // 2}px;
                        border: 3px solid rgba(255, 255, 255, 255);
                    }}
                """)
            else:
                # Style normal
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(80, 80, 80, 220);
                        border-radius: {self.btn_size // 2}px;
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                    QPushButton:hover {{
                        background-color: rgba(120, 120, 120, 250);
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                """)
    
    def show_focused_tooltip(self):
        """Affiche le tooltip du bouton focusé et met à jour l'icône du menu parent"""
        if not (0 <= self.focused_index < len(self.buttons)):
            return
        
        focused_btn = self.buttons[self.focused_index]
        if focused_btn in self.tooltips and self.parent_menu:
            tooltip_data = self.tooltips[focused_btn]
            # Supporter l'ancien format (string) et le nouveau (tuple)
            if isinstance(tooltip_data, tuple):
                tooltip_text, tooltip_html = tooltip_data
            else:
                tooltip_text, tooltip_html = tooltip_data, None
            self.parent_menu.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
            self.parent_menu.update_tooltip_position()
        
        # Afficher l'icône focusée dans le menu parent
        if self.parent_menu and self.focused_index < len(self.button_labels):
            label = self.button_labels[self.focused_index]
            if "/" in label:
                self.parent_menu.central_icon = image_pixmap(label, 64)
            elif is_emoji(label):
                self.parent_menu.central_icon = emoji_pixmap(label, 48)
            else:
                self.parent_menu.central_icon = text_pixmap(label, 48)
            self.parent_menu.update()