"""
StorageBar - Barre horizontale pour le sous-menu de stockage
Remplace le HoverSubMenu radial par une barre horizontale avec bords totalement arrondis
"""

from PyQt6.QtCore import Qt, QEvent, QSize, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QIcon, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import QWidget, QPushButton
from utils import is_emoji, emoji_pixmap, text_pixmap, image_pixmap


class StorageBar(QWidget):
    """Barre horizontale de sous-menu qui apparaît au hover d'un bouton (pour ➖)"""
    
    def __init__(self, anchor_x, anchor_y, buttons, parent_menu=None, app_instance=None, 
                 menu_background_color=None, menu_opacity=1.0):
        """
        Args:
            anchor_x: Position X du centre du bouton d'origine (sera recouvert par le coin gauche)
            anchor_y: Position Y du centre du bouton d'origine
            buttons: Liste de tuples (label, callback, tooltip)
            parent_menu: Le menu radial parent
            app_instance: Instance de l'application
            menu_background_color: Couleur de fond (tuple RGB ou None pour défaut)
            menu_opacity: Opacité du menu (0.0 à 1.0)
        """
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
        self.button_labels = []
        self.tooltips = {}
        self.closing = False
        
        # Connecter le signal destroyed pour nettoyer la référence dans le parent
        self.destroyed.connect(self.on_destroyed)
        
        # Paramètres de la barre
        self.btn_size = 50  # Taille des boutons (carrés)
        self.btn_spacing = 8  # Espacement entre les boutons
        self.padding_h = 10  # Padding horizontal (réduit pour les bords arrondis)
        self.padding_v = 8   # Padding vertical
        
        # Couleur de fond - utiliser celle du menu radial si fournie
        if menu_background_color:
            r, g, b = menu_background_color
            # Appliquer l'opacité (convertir 0.0-1.0 en 0-255)
            alpha = int(menu_opacity * 255)
            self.bg_color = QColor(r, g, b, alpha)
        else:
            self.bg_color = QColor(60, 60, 60, 220)
        self.border_color = QColor(100, 100, 100, 150)
        
        # Calculer les dimensions
        num_buttons = len(buttons)
        self.bar_width = (num_buttons * self.btn_size) + ((num_buttons - 1) * self.btn_spacing) + (2 * self.padding_h)
        self.bar_height = self.btn_size + (2 * self.padding_v)
        
        # Bords totalement arrondis (pilule) : rayon = moitié de la hauteur
        self.corner_radius = self.bar_height // 2
        
        # Position : le coin gauche recouvre le bouton d'origine
        # Décaler de half_btn_size pour que le premier bouton soit centré sur anchor_x
        self.anchor_x = anchor_x
        self.anchor_y = anchor_y
        half_btn = self.btn_size // 2
        self.target_x = anchor_x - self.padding_h - half_btn
        self.target_y = anchor_y - self.bar_height // 2
        
        self.resize(self.bar_width, self.bar_height)
        self.move(self.target_x, self.target_y)
        
        # Créer les boutons
        self.create_buttons(buttons)
        
        # Animation d'ouverture
        self.scale_factor = 1.0
        self.opacity = 1.0
        self.anim = None
        self.target_width = self.bar_width
        self.current_width = self.bar_width
        
        # Navigation clavier
        self.focused_index = -1
    
    def on_destroyed(self):
        """Appelé quand le widget est détruit - nettoie la référence dans le parent"""
        if self.parent_menu and hasattr(self.parent_menu, 'hover_submenu'):
            self.parent_menu.hover_submenu = None
    
    def create_buttons(self, buttons):
        """Crée les boutons de la barre horizontale"""
        if not buttons:
            return
        
        for i, (label, callback, tooltip) in enumerate(buttons):
            self.button_labels.append(label)
            
            # Position du bouton (horizontal)
            bx = self.padding_h + i * (self.btn_size + self.btn_spacing)
            by = self.padding_v
            
            btn = QPushButton("", self)
            btn.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            
            # Icône - gérer images, emojis et texte
            if "/" in label:
                btn.setIcon(QIcon(image_pixmap(label, 34)))
                btn.setIconSize(QSize(34, 34))
            elif is_emoji(label):
                btn.setIcon(QIcon(emoji_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            else:
                btn.setIcon(QIcon(text_pixmap(label, 28)))
                btn.setIconSize(QSize(28, 28))
            
            # Style du bouton
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(80, 80, 80, 100);
                    border-radius: {self.btn_size // 2}px;
                    border: 2px solid rgba(255, 255, 255, 0);
                }}
                QPushButton:hover {{
                    background-color: rgba(120, 120, 120, 200);
                    border: 2px solid rgba(255, 255, 255, 50);
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
        """Crée un handler de clic qui exécute l'action"""
        def handler():
            self.closing = True
            callback()
        return handler
    
    def eventFilter(self, watched, event):
        """Gère les événements de hover sur les boutons"""
        if event.type() == QEvent.Type.Enter:
            # Afficher le tooltip
            if watched in self.tooltips and self.parent_menu:
                tooltip_text = self.tooltips[watched]
                self.parent_menu.tooltip_window.show_message(tooltip_text, 0)
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
                    self.parent_menu.update()
            
            return False
        
        return False
    
    def enterEvent(self, event):
        """Appelé quand on entre sur la barre"""
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Ferme la barre avec animation quand on la quitte"""
        if not self.closing:
            self.animate_close()
        super().leaveEvent(event)
    
    def close_immediately(self):
        """Ferme la barre immédiatement sans animation"""
        self.closing = True
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()
    
    def paintEvent(self, event):
        """Dessine le fond de la barre avec coins arrondis"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Appliquer l'opacité globale
        painter.setOpacity(self.opacity)
        
        # Créer le chemin avec coins arrondis
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 
                          self.corner_radius, self.corner_radius)
        
        # Dessiner le fond
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.bg_color))
        painter.drawPath(path)
        
        # Dessiner la bordure
        painter.setPen(QPen(self.border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    
    def animate_open(self):
        """Animation d'ouverture de la barre - élargissement de gauche à droite"""
        # Stocker la largeur finale
        self.target_width = self.bar_width
        self.current_width = 0
        
        # Commencer avec une largeur minimale
        self.resize(1, self.bar_height)
        
        # Cacher tous les boutons au début
        for btn in self.buttons:
            btn.setVisible(False)
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(150)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def update_anim(value):
            # Calculer la largeur actuelle
            self.current_width = int(self.target_width * value)
            self.current_width = max(1, self.current_width)
            
            # Redimensionner le widget
            self.resize(self.current_width, self.bar_height)
            
            # Afficher les boutons qui sont dans la zone visible
            for i, btn in enumerate(self.buttons):
                btn_x = self.padding_h + i * (self.btn_size + self.btn_spacing)
                btn_right = btn_x + self.btn_size
                
                if btn_right <= self.current_width:
                    # Le bouton est entièrement visible
                    btn.setVisible(True)
                    btn.move(int(btn_x), self.padding_v)
                    btn.setFixedSize(self.btn_size, self.btn_size)
                elif btn_x < self.current_width:
                    # Le bouton est partiellement visible - on l'affiche quand même
                    btn.setVisible(True)
                    btn.move(int(btn_x), self.padding_v)
                    btn.setFixedSize(self.btn_size, self.btn_size)
                else:
                    # Le bouton n'est pas encore visible
                    btn.setVisible(False)
            
            self.opacity = min(1.0, value * 2)  # Fade in rapide
            self.update()
        
        self.anim.valueChanged.connect(update_anim)
        self.anim.finished.connect(self.on_open_finished)
        self.anim.start()
    
    def apply_scale(self):
        """Applique le facteur d'échelle aux boutons"""
        for i, btn in enumerate(self.buttons):
            # Position originale
            orig_x = self.padding_h + i * (self.btn_size + self.btn_spacing)
            orig_y = self.padding_v
            
            # Taille scalée
            scaled_size = max(1, int(self.btn_size * self.scale_factor))
            
            # Centrer le bouton scalé sur sa position originale
            center_x = orig_x + self.btn_size / 2
            center_y = orig_y + self.btn_size / 2
            new_x = center_x - scaled_size / 2
            new_y = center_y - scaled_size / 2
            
            btn.move(int(new_x), int(new_y))
            btn.setFixedSize(scaled_size, scaled_size)
            
            icon_size = max(1, int(28 * self.scale_factor))
            btn.setIconSize(QSize(icon_size, icon_size))
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(80, 80, 80, 100);
                    border-radius: {scaled_size // 2}px;
                    border: 2px solid rgba(255, 255, 255, 0);
                }}
                QPushButton:hover {{
                    background-color: rgba(120, 120, 120, 200);
                    border: 2px solid rgba(255, 255, 255, 50);
                }}
            """)
    
    def on_open_finished(self):
        """Appelé quand l'animation d'ouverture est terminée"""
        # S'assurer que la barre a sa taille finale
        self.resize(self.bar_width, self.bar_height)
        self.opacity = 1.0
        
        # S'assurer que tous les boutons sont visibles et bien positionnés
        for i, btn in enumerate(self.buttons):
            btn_x = self.padding_h + i * (self.btn_size + self.btn_spacing)
            btn.move(int(btn_x), self.padding_v)
            btn.setFixedSize(self.btn_size, self.btn_size)
            btn.setVisible(True)
        
        self.update()
    
    def animate_close(self):
        """Animation de fermeture de la barre - rétrécissement de droite à gauche"""
        self.closing = True
        
        # Stocker la largeur actuelle
        self.target_width = self.bar_width
        self.current_width = self.bar_width
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(150)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        def update_anim(value):
            # Calculer la largeur actuelle
            self.current_width = int(self.target_width * value)
            self.current_width = max(1, self.current_width)
            
            # Redimensionner le widget
            self.resize(self.current_width, self.bar_height)
            
            # Cacher les boutons qui sortent de la zone visible
            for i, btn in enumerate(self.buttons):
                btn_x = self.padding_h + i * (self.btn_size + self.btn_spacing)
                btn_right = btn_x + self.btn_size
                
                if btn_x < self.current_width:
                    btn.setVisible(True)
                else:
                    btn.setVisible(False)
            
            self.opacity = value
            self.update()
        
        self.anim.valueChanged.connect(update_anim)
        self.anim.finished.connect(self.on_close_finished)
        self.anim.start()
    
    def on_close_finished(self):
        """Appelé quand l'animation de fermeture est terminée"""
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()
    
    # === Navigation clavier ===
    
    def handle_key_right(self):
        """Navigue vers le bouton suivant (droite)"""
        if not self.buttons:
            return
        
        if self.focused_index == -1:
            self.focused_index = 0
        else:
            self.focused_index = (self.focused_index + 1) % len(self.buttons)
        
        self.update_focus_style()
        self.show_focused_tooltip()
    
    def handle_key_left(self):
        """Navigue vers le bouton précédent (gauche)"""
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
        """Ferme la barre et revient au menu principal"""
        self.closing = True
        if self.parent_menu:
            self.parent_menu.hover_submenu = None
            self.parent_menu.tooltip_window.hide()
            self.parent_menu.central_icon = None
            self.parent_menu.update()
        self.close()
    
    def update_focus_style(self):
        """Met à jour le style des boutons pour montrer le focus"""
        for i, btn in enumerate(self.buttons):
            scaled_size = max(1, int(self.btn_size * self.scale_factor)) if self.scale_factor else self.btn_size
            if i == self.focused_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(120, 120, 120, 200);
                        border-radius: {scaled_size // 2}px;
                        border: 3px solid rgba(255, 255, 255, 255);
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(80, 80, 80, 100);
                        border-radius: {scaled_size // 2}px;
                        border: 2px solid rgba(255, 255, 255, 0);
                    }}
                    QPushButton:hover {{
                        background-color: rgba(120, 120, 120, 200);
                        border: 2px solid rgba(255, 255, 255, 50);
                    }}
                """)
    
    def show_focused_tooltip(self):
        """Affiche le tooltip du bouton focusé et met à jour l'icône du menu parent"""
        if not (0 <= self.focused_index < len(self.buttons)):
            return
        
        focused_btn = self.buttons[self.focused_index]
        if focused_btn in self.tooltips and self.parent_menu:
            tooltip_text = self.tooltips[focused_btn]
            self.parent_menu.tooltip_window.show_message(tooltip_text, 0)
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