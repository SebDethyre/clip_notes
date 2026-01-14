

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtWidgets import QListWidget, QAbstractItemView
from utils import *
class AutoScrollListWidget(QListWidget):
    """
    QListWidget avec auto-scroll pendant le drag & drop.
    Quand on approche du bord haut ou bas, la liste scrolle automatiquement.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration de l'auto-scroll
        self._auto_scroll_margin = 40  # Zone de détection en pixels
        self._auto_scroll_speed = 3    # Pixels par tick
        self._auto_scroll_interval = 20  # Intervalle en ms (plus petit = plus fluide)
        
        # Timer pour l'auto-scroll
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)
        self._auto_scroll_direction = 0  # -1 = haut, 0 = stop, 1 = bas
    
    def dragMoveEvent(self, event):
        """Gère le déplacement pendant le drag pour activer l'auto-scroll"""
        # Position du curseur relative au widget
        pos = event.position().toPoint()
        widget_height = self.viewport().height()
        
        # Déterminer si on est dans une zone d'auto-scroll
        if pos.y() < self._auto_scroll_margin:
            # Zone haute - scroller vers le haut
            self._auto_scroll_direction = -1
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start(self._auto_scroll_interval)
        elif pos.y() > widget_height - self._auto_scroll_margin:
            # Zone basse - scroller vers le bas
            self._auto_scroll_direction = 1
            if not self._auto_scroll_timer.isActive():
                self._auto_scroll_timer.start(self._auto_scroll_interval)
        else:
            # Zone centrale - arrêter l'auto-scroll
            self._auto_scroll_direction = 0
            self._auto_scroll_timer.stop()
        
        # Appeler l'implémentation parente pour le comportement normal du drag
        super().dragMoveEvent(event)
    
    def dragLeaveEvent(self, event):
        """Arrête l'auto-scroll quand le drag quitte le widget"""
        self._auto_scroll_direction = 0
        self._auto_scroll_timer.stop()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """Arrête l'auto-scroll quand on drop"""
        self._auto_scroll_direction = 0
        self._auto_scroll_timer.stop()
        super().dropEvent(event)
    
    def _do_auto_scroll(self):
        """Effectue le scroll automatique"""
        if self._auto_scroll_direction == 0:
            self._auto_scroll_timer.stop()
            return
        
        # Récupérer la scrollbar verticale
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            new_value = scrollbar.value() + (self._auto_scroll_direction * self._auto_scroll_speed)
            scrollbar.setValue(new_value)