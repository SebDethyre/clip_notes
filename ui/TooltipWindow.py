
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QWidget, QTextBrowser, QVBoxLayout

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
        
        # QTextBrowser pour afficher du texte OU du HTML riche
        self.text_browser = QTextBrowser(self)
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_browser.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                color: white;
                background-color: rgba(80, 80, 80, 200);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text_browser)
        
        # Timer pour l'auto-masquage
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide)
        self.hide_timer.setSingleShot(True)
        
        # Taille max pour éviter les tooltips géants
        self.setMaximumWidth(600)
        self.setMaximumHeight(400)
        
        # État initial
        self.hide()
    
    def show_message(self, text, duration_ms=0, html=None):
        """
        Affiche un message.
        
        Args:
            text: Le texte à afficher (fallback si pas de HTML)
            duration_ms: Durée d'affichage en millisecondes (0 = infini)
            html: Le HTML riche à afficher (optionnel, prioritaire sur text)
        """
        if not text and not html:
            self.hide()
            return
        
        # Textes longs (>100 chars) ou HTML : comportement adapté
        if html or (text and len(text) > 100):
            # Retirer les contraintes de taille fixe
            self.setMinimumSize(0, 0)
            self.setMaximumSize(600, 400)
            self.text_browser.setMinimumSize(0, 0)
            self.text_browser.setMaximumSize(600, 400)
            
            if html:
                self.text_browser.setHtml(html)
            else:
                self.text_browser.setPlainText(text)
            
            # Ajuster la taille au contenu
            doc = self.text_browser.document()
            doc.setTextWidth(560)  # Largeur fixe pour le calcul
            content_height = min(int(doc.size().height()) + 20, 400)
            content_width = min(int(doc.idealWidth()) + 40, 600)
            # S'assurer d'une largeur minimale raisonnable
            content_width = max(content_width, 200)
            self.text_browser.setFixedSize(content_width, content_height)
            self.calculated_width = content_width
            self.setFixedSize(content_width, content_height)
        else:
            # Textes courts : nouveau comportement avec taille fixe
            self.text_browser.setPlainText(text)
            font = self.text_browser.font()
            fm = QFontMetrics(font)
            # Calculer la taille du texte multi-lignes
            max_text_width = 600 - 48
            text_rect = fm.boundingRect(
                QRect(0, 0, max_text_width, 10000),
                Qt.TextFlag.TextWordWrap,
                text
            )
            content_width = text_rect.width() + 48
            content_height = text_rect.height() + 24
            content_width = min(max(content_width, 60), 600)
            content_height = min(content_height, 400)
            
            self.text_browser.setFixedSize(content_width, content_height)
            self.calculated_width = content_width
            self.setFixedSize(content_width, content_height)
        
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
        
        # Utiliser la largeur calculée si disponible, sinon self.width()
        width = getattr(self, '_calculated_width', self.width())
        
        # Calculer la position
        tooltip_x = menu_center_x - width // 2
        tooltip_y = menu_center_y + distance_below
        
        self.move(tooltip_x, tooltip_y)