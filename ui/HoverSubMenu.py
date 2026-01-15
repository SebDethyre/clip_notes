import math
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize, QRect, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QIcon, QCursor, QPen
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
        
        # Timer pour fermeture retardée (permet les transitions hover)
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.check_and_close)
        
        # Créer les boutons
        self.create_buttons(buttons)
        
        # Animation d'ouverture
        self.scale_factor = 0.1
        self.anim = None
        
        # Navigation clavier
        self.focused_index = -1
    
    def on_destroyed(self):
        """Appelé quand le widget est détruit - nettoie la référence dans le parent"""
        if self.parent_menu and hasattr(self.parent_menu, '_hover_submenu'):
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
            
            # Icône
            if is_emoji(label):
                btn.setIcon(QIcon(emoji_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            else:
                btn.setIcon(QIcon(text_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            
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
        """Gère les événements de hover sur les boutons du sous-menu"""
        if event.type() == QEvent.Type.Enter:
            # Annuler la fermeture si on entre sur un bouton
            if self.close_timer.isActive():
                self.close_timer.stop()
            
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
            
            # Afficher l'icône survolée dans le menu parent
            if watched in self.buttons and self.parent_menu:
                button_index = self.buttons.index(watched)
                if button_index < len(self.button_labels):
                    label = self.button_labels[button_index]
                    # Créer un pixmap adapté au type de label
                    if "/" in label:
                        self.parent_menu.central_icon = image_pixmap(label, 64)
                    elif is_emoji(label):
                        self.parent_menu.central_icon = emoji_pixmap(label, 48)
                    else:
                        self.parent_menu.central_icon = text_pixmap(label, 48)
                    self.parent_menu.update()
                
        elif event.type() == QEvent.Type.Leave:
            # Masquer le tooltip
            if self.parent_menu:
                self.parent_menu.tooltip_window.hide()
            
            # Effacer l'icône centrale du parent
            if watched in self.buttons and self.parent_menu:
                self.parent_menu.central_icon = None
                self.parent_menu.update()
        
        return super().eventFilter(watched, event)
    
    def enterEvent(self, event):
        """Quand la souris entre dans le sous-menu"""
        # Annuler tout timer de fermeture
        if self.close_timer.isActive():
            self.close_timer.stop()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Quand la souris quitte le sous-menu"""
        if not self.closing:
            # Lancer un timer pour vérifier si on doit fermer
            self.close_timer.start(100)  # 100ms de délai
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Gère les clics dans le sous-menu - ignore les clics au centre (hors boutons)"""
        # Vérifier si le clic est sur un bouton
        for btn in self.buttons:
            if btn.geometry().contains(event.pos()):
                # Laisser le bouton gérer le clic
                return super().mousePressEvent(event)
        
        # Clic en dehors des boutons - ne rien faire (ignorer)
        event.accept()
    
    def check_and_close(self):
        """Vérifie si la souris est sur le bouton parent ou le sous-menu, sinon ferme"""
        if self.closing:
            return
        
        # Vérifier si la souris est sur ce widget
        cursor_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        if self.rect().contains(local_pos):
            return  # Souris encore sur le sous-menu
        
        # Vérifier si la souris est sur le bouton ➖ du menu parent
        if self.parent_menu and hasattr(self.parent_menu, '_storage_button_index'):
            storage_idx = self.parent_menu.storage_button_index
            if storage_idx is not None and storage_idx < len(self.parent_menu.buttons):
                storage_btn = self.parent_menu.buttons[storage_idx]
                btn_global_pos = storage_btn.mapToGlobal(storage_btn.rect().topLeft())
                btn_rect_global = QRect(btn_global_pos, storage_btn.size())
                if btn_rect_global.contains(cursor_pos):
                    return  # Souris sur le bouton ➖
        
        # Sinon fermer le sous-menu
        self.closing = True
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            # Effacer l'icône centrale
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()

    def schedule_close(self):
        """Planifie la fermeture du sous-menu (appelé depuis le parent)"""
        if not self.closing:
            self.close_timer.start(100)

    def cancel_close(self):
        """Annule la fermeture planifiée"""
        if self.close_timer.isActive():
            self.close_timer.stop()

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
        
        # Icône centrale (seulement si définie)
        if self.central_icon_label and self.scale_factor > 0.5:
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
                        border-radius: {max(1, scaled_size // 2)}px;
                        border: 3px solid rgba(255, 255, 255, 255);
                    }}
                """)
            else:
                # Style normal
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(80, 80, 80, 220);
                        border-radius: {max(1, scaled_size // 2)}px;
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
