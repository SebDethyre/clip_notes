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
        self._buttons = []
        self._button_labels = []  # Pour stocker les labels des boutons
        self._tooltips = {}
        self._closing = False
        self._central_icon_label = ""  # Icône centrale (vide = pas d'icône)
        
        # Connecter le signal destroyed pour nettoyer la référence dans le parent
        self.destroyed.connect(self._on_destroyed)
        
        # Paramètres du sous-menu (plus petit que le menu principal)
        self.btn_size = 55
        self.radius = 38
        self.diameter = 2 * (self.radius + self.btn_size)
        self.widget_size = self.diameter - 54
        
        # Stocker le centre pour le positionnement
        self._center_x = center_x
        self._center_y = center_y
        
        # Positionner le widget pour que son centre soit sur le bouton
        self._target_x = center_x - self.widget_size // 2
        self._target_y = center_y - self.widget_size // 2
        
        self.resize(self.widget_size, self.widget_size)
        self.move(self._target_x, self._target_y)
        
        # Timer pour fermeture retardée (permet les transitions hover)
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._check_and_close)
        
        # Créer les boutons
        self._create_buttons(buttons)
        
        # Animation d'ouverture
        self._scale_factor = 0.1
        self._anim = None
        
        # Navigation clavier
        self._focused_index = -1
    
    def _on_destroyed(self):
        """Appelé quand le widget est détruit - nettoie la référence dans le parent"""
        if self.parent_menu and hasattr(self.parent_menu, '_hover_submenu'):
            self.parent_menu._hover_submenu = None
    
    def _create_buttons(self, buttons):
        """Crée les boutons du sous-menu"""
        if not buttons:
            return
        
        angle_step = 360 / len(buttons)
        center_offset = self.widget_size // 2
        
        for i, (label, callback, tooltip) in enumerate(buttons):
            # Stocker le label
            self._button_labels.append(label)
            
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
            btn.clicked.connect(self._make_click_handler(callback))
            btn.installEventFilter(self)
            
            if tooltip:
                self._tooltips[btn] = tooltip
            
            self._buttons.append(btn)
    
    def _make_click_handler(self, callback):
        """Crée un handler de clic qui exécute l'action (le callback gère la fermeture)"""
        def handler():
            self._closing = True
            callback()
            # Note: le callback (ex: _storage_action_clips) se charge de fermer le sous-menu
        return handler
    
    def eventFilter(self, watched, event):
        """Gère les événements de hover sur les boutons du sous-menu"""
        if event.type() == QEvent.Type.Enter:
            # Annuler la fermeture si on entre sur un bouton
            if self._close_timer.isActive():
                self._close_timer.stop()
            
            # Afficher le tooltip dans le parent_menu si disponible
            if watched in self._tooltips and self.parent_menu:
                tooltip_data = self._tooltips[watched]
                # Supporter l'ancien format (string) et le nouveau (tuple)
                if isinstance(tooltip_data, tuple):
                    tooltip_text, tooltip_html = tooltip_data
                else:
                    tooltip_text, tooltip_html = tooltip_data, None
                self.parent_menu.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
                self.parent_menu._update_tooltip_position()
            
            # Afficher l'icône survolée dans le menu parent
            if watched in self._buttons and self.parent_menu:
                button_index = self._buttons.index(watched)
                if button_index < len(self._button_labels):
                    label = self._button_labels[button_index]
                    # Créer un pixmap adapté au type de label
                    if "/" in label:
                        self.parent_menu._central_icon = image_pixmap(label, 64)
                    elif is_emoji(label):
                        self.parent_menu._central_icon = emoji_pixmap(label, 48)
                    else:
                        self.parent_menu._central_icon = text_pixmap(label, 48)
                    self.parent_menu.update()
                
        elif event.type() == QEvent.Type.Leave:
            # Masquer le tooltip
            if self.parent_menu:
                self.parent_menu.tooltip_window.hide()
            
            # Effacer l'icône centrale du parent
            if watched in self._buttons and self.parent_menu:
                self.parent_menu._central_icon = None
                self.parent_menu.update()
        
        return super().eventFilter(watched, event)
    
    def enterEvent(self, event):
        """Quand la souris entre dans le sous-menu"""
        # Annuler tout timer de fermeture
        if self._close_timer.isActive():
            self._close_timer.stop()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Quand la souris quitte le sous-menu"""
        if not self._closing:
            # Lancer un timer pour vérifier si on doit fermer
            self._close_timer.start(100)  # 100ms de délai
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Gère les clics dans le sous-menu - ignore les clics au centre (hors boutons)"""
        # Vérifier si le clic est sur un bouton
        for btn in self._buttons:
            if btn.geometry().contains(event.pos()):
                # Laisser le bouton gérer le clic
                return super().mousePressEvent(event)
        
        # Clic en dehors des boutons - ne rien faire (ignorer)
        event.accept()
    
    def _check_and_close(self):
        """Vérifie si la souris est sur le bouton parent ou le sous-menu, sinon ferme"""
        if self._closing:
            return
        
        # Vérifier si la souris est sur ce widget
        cursor_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        if self.rect().contains(local_pos):
            return  # Souris encore sur le sous-menu
        
        # Vérifier si la souris est sur le bouton ➖ du menu parent
        if self.parent_menu and hasattr(self.parent_menu, '_storage_button_index'):
            storage_idx = self.parent_menu._storage_button_index
            if storage_idx is not None and storage_idx < len(self.parent_menu.buttons):
                storage_btn = self.parent_menu.buttons[storage_idx]
                btn_global_pos = storage_btn.mapToGlobal(storage_btn.rect().topLeft())
                btn_rect_global = QRect(btn_global_pos, storage_btn.size())
                if btn_rect_global.contains(cursor_pos):
                    return  # Souris sur le bouton ➖
        
        # Sinon fermer le sous-menu
        self._closing = True
        if self.parent_menu:
            self.parent_menu._hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            # Effacer l'icône centrale
            self.parent_menu._central_icon = None
            self.parent_menu.update()
        self.close()

    def schedule_close(self):
        """Planifie la fermeture du sous-menu (appelé depuis le parent)"""
        if not self._closing:
            self._close_timer.start(100)

    def cancel_close(self):
        """Annule la fermeture planifiée"""
        if self._close_timer.isActive():
            self._close_timer.stop()

    def paintEvent(self, event):
        """Dessine le fond du sous-menu"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        
        # Dessiner un cercle de fond semi-transparent
        scaled_diameter = int(self.diameter * self._scale_factor)
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
        if self._central_icon_label and self._scale_factor > 0.5:
            icon_size = int(24 * self._scale_factor)
            if is_emoji(self._central_icon_label):
                icon_pixmap = emoji_pixmap(self._central_icon_label, icon_size)
            else:
                icon_pixmap = text_pixmap(self._central_icon_label, icon_size)
            painter.drawPixmap(
                center.x() - icon_size // 2,
                center.y() - icon_size // 2,
                icon_pixmap
            )
    
    def animate_open(self):
        """Animation d'ouverture du sous-menu"""
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(200)
        self._anim.setStartValue(0.1)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        def update_scale(value):
            self._scale_factor = value
            self._apply_scale()
        
        self._anim.valueChanged.connect(update_scale)
        self._anim.finished.connect(self._on_open_finished)
        self._anim.start()
    
    def _apply_scale(self):
        """Applique le facteur d'échelle aux boutons"""
        center_offset = self.widget_size // 2
        angle_step = 360 / len(self._buttons) if self._buttons else 360
        
        for i, btn in enumerate(self._buttons):
            angle = math.radians(i * angle_step - 90)
            
            # Position originale
            orig_bx = center_offset + self.radius * math.cos(angle) - self.btn_size // 2
            orig_by = center_offset + self.radius * math.sin(angle) - self.btn_size // 2
            
            # Appliquer le scale depuis le centre
            scaled_bx = center_offset + (orig_bx - center_offset) * self._scale_factor
            scaled_by = center_offset + (orig_by - center_offset) * self._scale_factor
            scaled_size = int(self.btn_size * self._scale_factor)
            
            btn.move(int(scaled_bx), int(scaled_by))
            btn.setFixedSize(max(1, scaled_size), max(1, scaled_size))
            btn.setIconSize(QSize(int(28 * self._scale_factor), int(28 * self._scale_factor)))
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
    
    def _on_open_finished(self):
        """Appelé quand l'animation d'ouverture est terminée"""
        for btn in self._buttons:
            btn.setVisible(True)
    
    # === Navigation clavier ===
    
    def _handle_key_right(self):
        """Navigue vers le bouton suivant (sens horaire)"""
        if not self._buttons:
            return
        
        if self._focused_index == -1:
            self._focused_index = 0
        else:
            self._focused_index = (self._focused_index + 1) % len(self._buttons)
        
        self._update_focus_style()
        self._show_focused_tooltip()
    
    def _handle_key_left(self):
        """Navigue vers le bouton précédent (sens anti-horaire)"""
        if not self._buttons:
            return
        
        if self._focused_index == -1:
            self._focused_index = len(self._buttons) - 1
        else:
            self._focused_index = (self._focused_index - 1) % len(self._buttons)
        
        self._update_focus_style()
        self._show_focused_tooltip()
    
    def _handle_key_enter(self):
        """Active le bouton focusé"""
        if 0 <= self._focused_index < len(self._buttons):
            self._buttons[self._focused_index].click()
    
    def _handle_key_escape(self):
        """Ferme le sous-menu et revient au menu principal"""
        self._closing = True
        if self.parent_menu:
            self.parent_menu._hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            # Effacer l'icône centrale
            self.parent_menu._central_icon = None
            self.parent_menu.update()
        self.close()
    
    def _update_focus_style(self):
        """Met à jour le style des boutons pour montrer le focus"""
        for i, btn in enumerate(self._buttons):
            scaled_size = int(self.btn_size * self._scale_factor) if self._scale_factor else self.btn_size
            if i == self._focused_index:
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
    
    def _show_focused_tooltip(self):
        """Affiche le tooltip du bouton focusé et met à jour l'icône du menu parent"""
        if not (0 <= self._focused_index < len(self._buttons)):
            return
        
        focused_btn = self._buttons[self._focused_index]
        if focused_btn in self._tooltips and self.parent_menu:
            tooltip_data = self._tooltips[focused_btn]
            # Supporter l'ancien format (string) et le nouveau (tuple)
            if isinstance(tooltip_data, tuple):
                tooltip_text, tooltip_html = tooltip_data
            else:
                tooltip_text, tooltip_html = tooltip_data, None
            self.parent_menu.tooltip_window.show_message(tooltip_text, 0, html=tooltip_html)
            self.parent_menu._update_tooltip_position()
        
        # Afficher l'icône focusée dans le menu parent
        if self.parent_menu and self._focused_index < len(self._button_labels):
            label = self._button_labels[self._focused_index]
            if "/" in label:
                self.parent_menu._central_icon = image_pixmap(label, 64)
            elif is_emoji(label):
                self.parent_menu._central_icon = emoji_pixmap(label, 48)
            else:
                self.parent_menu._central_icon = text_pixmap(label, 48)
            self.parent_menu.update()
