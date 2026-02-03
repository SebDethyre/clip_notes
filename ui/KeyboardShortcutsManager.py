"""
Gestionnaire de raccourcis clavier pour ClipNotes
- ShortcutCaptureDialog : Fenêtre style Ubuntu pour capturer un raccourci
- KeyboardShortcutsManager : Fenêtre avec tableau récapitulatif des raccourcis
"""

import json
import os
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QKeySequence, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QScrollArea, QFrame, QAbstractItemView, QTabWidget, QSizePolicy
)

from utils import emoji_pixmap, image_pixmap, text_pixmap, is_emoji


class ShortcutCaptureDialog(QDialog):
    """
    Fenêtre de capture de raccourci clavier style Ubuntu.
    Se met en attente directe du raccourci de l'utilisateur.
    Distingue les touches Ctrl/Alt/Shift gauche et droite.
    Accepte les lettres simples et les chiffres.
    """
    
    def __init__(self, parent=None, current_shortcut="", nb_icons_menu=None):
        super().__init__(parent)
        self.captured_shortcut = None
        self.current_modifiers = set()
        self.current_key = None
        self.waiting_for_key = True
        self.nb_icons_menu = nb_icons_menu
        
        self.setWindowTitle("Définir le raccourci")
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Conteneur avec fond sombre
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 25, 30, 250);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 20);
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)
        
        # Titre
        title_label = QLabel("Appuyez sur le nouveau raccourci")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_label)
        
        # Zone d'affichage du raccourci
        self.shortcut_display = QLabel("En attente...")
        self.shortcut_display.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-size: 20px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 120);
                border-radius: 8px;
                padding: 16px;
                border: 2px solid rgba(255, 215, 0, 100);
            }
        """)
        self.shortcut_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.shortcut_display.setMinimumHeight(60)
        container_layout.addWidget(self.shortcut_display)
        
        # Info sur le raccourci actuel
        if current_shortcut:
            current_label = QLabel(f"Raccourci actuel : {current_shortcut}")
            current_label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 150);
                    font-size: 12px;
                    background: transparent;
                    border: none;
                }
            """)
            current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(current_label)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        # Bouton Annuler
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 10px 24px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        # Bouton Effacer le raccourci
        clear_btn = QPushButton("Effacer")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 100, 100, 30);
                border: 1px solid rgba(255, 100, 100, 60);
                border-radius: 8px;
                padding: 10px 24px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 60);
            }
        """)
        clear_btn.clicked.connect(self.clear_shortcut)
        buttons_layout.addWidget(clear_btn)
        
        # Bouton Valider
        self.validate_btn = QPushButton("Valider")
        self.validate_btn.setEnabled(False)
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 200, 100, 30);
                border: 1px solid rgba(100, 200, 100, 60);
                border-radius: 8px;
                padding: 10px 24px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(100, 200, 100, 60);
            }
            QPushButton:disabled {
                background-color: rgba(80, 80, 80, 30);
                border: 1px solid rgba(80, 80, 80, 60);
                color: rgba(255, 255, 255, 80);
            }
        """)
        self.validate_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.validate_btn)
        
        container_layout.addLayout(buttons_layout)
        main_layout.addWidget(container)
        
        # Focus pour recevoir les événements clavier
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
    
    def clear_shortcut(self):
        """Efface le raccourci actuel"""
        self.captured_shortcut = ""
        self.accept()
    
    def keyPressEvent(self, event):
        """Capture les touches pressées"""
        if not self.waiting_for_key:
            return super().keyPressEvent(event)
        
        key = event.key()
        native_modifiers = event.nativeModifiers()
        
        # Détecter les modificateurs avec distinction gauche/droite
        modifiers = []
        
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.nativeScanCode() == 37:
                modifiers.append("Ctrl_L")
            elif event.nativeScanCode() == 105:
                modifiers.append("Ctrl_R")
            else:
                modifiers.append("Ctrl")
        
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            if event.nativeScanCode() == 64:
                modifiers.append("Alt_L")
            elif event.nativeScanCode() == 108:
                modifiers.append("AltGr")
            else:
                modifiers.append("Alt")
        
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if event.nativeScanCode() == 50:
                modifiers.append("Shift_L")
            elif event.nativeScanCode() == 62:
                modifiers.append("Shift_R")
            else:
                modifiers.append("Shift")
        
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Super")
        
        # Ignorer si c'est juste un modificateur seul
        modifier_keys = {
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr
        }
        
        if key in modifier_keys:
            # Afficher les modificateurs en cours
            if modifiers:
                self.shortcut_display.setText(" + ".join(modifiers) + " + ...")
            return
        
        # C'est une vraie touche - obtenir son nom
        key_name = QKeySequence(key).toString()
        
        # Gérer les touches spéciales
        special_keys = {
            Qt.Key.Key_Escape: "Échap",
            Qt.Key.Key_Return: "Entrée",
            Qt.Key.Key_Enter: "Entrée",
            Qt.Key.Key_Space: "Espace",
            Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Backspace: "Retour",
            Qt.Key.Key_Delete: "Suppr",
            Qt.Key.Key_Home: "Début",
            Qt.Key.Key_End: "Fin",
            Qt.Key.Key_PageUp: "PageHaut",
            Qt.Key.Key_PageDown: "PageBas",
            Qt.Key.Key_Up: "↑",
            Qt.Key.Key_Down: "↓",
            Qt.Key.Key_Left: "←",
            Qt.Key.Key_Right: "→",
        }
        
        if key in special_keys:
            key_name = special_keys[key]
        
        # Construire le raccourci final
        # On accepte TOUT : lettres, chiffres, touches spéciales, avec ou sans modificateurs
        if modifiers:
            self.captured_shortcut = " + ".join(modifiers) + " + " + key_name
        else:
            self.captured_shortcut = key_name
        
        self.shortcut_display.setText(self.captured_shortcut)
        self.shortcut_display.setStyleSheet("""
            QLabel {
                color: #90EE90;
                font-size: 20px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 120);
                border-radius: 8px;
                padding: 16px;
                border: 2px solid rgba(100, 200, 100, 100);
            }
        """)
        self.validate_btn.setEnabled(True)
    
    def keyReleaseEvent(self, event):
        """Gère le relâchement des touches"""
        pass


# class KeyboardShortcutsManager(QDialog):
class KeyboardShortcutsManager(QWidget):
    """
    Fenêtre affichant le tableau récapitulatif des raccourcis clavier.
    Permet de configurer les raccourcis pour chaque bouton/clip.
    """
    
    def __init__(self, app_instance, parent=None, nb_icons_menu=None, dialog_parent=None):
        super().__init__(parent)
        self.nb_icons_menu = nb_icons_menu
        self.app_instance = app_instance
        self.dialog_parent = dialog_parent  # Référence au dialog parent pour le fermer
        self.shortcuts_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "shortcuts.json"
        )
        self.shortcuts = self.load_shortcuts()

        self.alias_column_width = 80
        self.action_column_width = 90
        self.value_column_width = 290
        self.shortcut_column_width = 150
        self.button_def_column_width = 100
        # self.setWindowTitle("⌨️ Raccourcis clavier")
        # self.setWindowFlags(
        #     Qt.WindowType.Dialog | 
        #     Qt.WindowType.WindowStaysOnTopHint
        # )
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # self.setMinimumSize(850, 500)
        # self.resize(850, 600)
        
        self.setup_ui()

    def get_main_widget(self):
        """Retourne le widget principal contenant toute l'UI (pour l'embed dans un onglet)"""
        # main_layout = QVBoxLayout(self) contient self.container
        return self.findChild(QFrame)  # ton container principal
    
    def load_shortcuts(self):
        """Charge les raccourcis depuis le fichier JSON"""
        if os.path.exists(self.shortcuts_file):
            try:
                with open(self.shortcuts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_shortcuts(self):
        """Sauvegarde les raccourcis dans le fichier JSON"""
        try:
            with open(self.shortcuts_file, 'w', encoding='utf-8') as f:
                json.dump(self.shortcuts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde raccourcis: {e}")
    
    def setup_ui(self):
        """Configure l'interface utilisateur"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Conteneur principal avec fond sombre
        container = QFrame(self)
                # border-radius: 16px;
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(20, 20, 25, 250);
                border: 1px solid rgba(255, 255, 255, 15);
            }
        """)
        self.container_layout = QVBoxLayout(container)
        # container_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.setSpacing(16)
        
        # # Titre
        # title_layout = QHBoxLayout()
        # title_label = QLabel("⌨️ Raccourcis clavier")
        # title_label.setStyleSheet("""
        #     QLabel {
        #         color: white;
        #         font-size: 20px;
        #         font-weight: bold;
        #         background: transparent;
        #         border: none;
        #     }
        # """)
        # title_layout.addWidget(title_label)
        # title_layout.addStretch()
        
        # Bouton fermer
        # close_btn = QPushButton("✕")
        # close_btn.setFixedSize(32, 32)
        # close_btn.setStyleSheet("""
        #     QPushButton {
        #         background-color: rgba(255, 100, 100, 60);
        #         border: none;
        #         border-radius: 16px;
        #         color: white;
        #         font-size: 16px;
        #     }
        #     QPushButton:hover {
        #         background-color: rgba(255, 100, 100, 120);
        #     }
        # """)
        # close_btn.clicked.connect(self.close)
        # title_layout.addWidget(close_btn)
        # container_layout.addLayout(title_layout)
        
        # Info
        info_label = QLabel("Cliquez sur 'Définir' pour configurer un raccourci. Les touches 1-9 lancent directement les clips par défaut.")
        info_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 120);
                font-size: 12px;
                background: transparent;
                border: none;
            }
        """)
        info_label.setWordWrap(True)
        self.container_layout.addWidget(info_label)
        
        # Zone de scroll pour le tableau
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 5);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 30);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 50);
            }
        """)
        
        # Widget conteneur pour le tableau
        self.table_container = QWidget()
        self.table_container.setStyleSheet("background: transparent;")
        self.table_layout = QVBoxLayout(self.table_container)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        self.table_layout.setSpacing(4)
        
        # En-têtes
        self._add_headers()
        
        # Ajouter les lignes
        self.populate_table(self.table_layout)
        
        self.table_layout.addStretch()
        self.scroll_area.setWidget(self.table_container)
        self.container_layout.addWidget(self.scroll_area)
        
        # Boutons du bas
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        reset_btn = QPushButton("Réinitialiser tout")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 100, 100, 30);
                border: 1px solid rgba(255, 100, 100, 60);
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 60);
            }
        """)
        reset_btn.clicked.connect(self.confirm_reset_all_shortcuts)
        buttons_layout.addWidget(reset_btn)
        
        # Bouton Fermer
        close_btn = QPushButton("Fermer")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 50);
                border: 1px solid rgba(150, 150, 150, 80);
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 80);
            }
        """)
        close_btn.clicked.connect(self.close_parent_dialog)
        buttons_layout.addWidget(close_btn)
        
        self.container_layout.addLayout(buttons_layout)
        main_layout.addWidget(container, 1)
        # if isinstance(self.parent(), QTabWidget):
        #     # Prendre toute la taille de l'onglet
        #     self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #     self.resize(self.parent().width(), self.parent().height())
    
    def _add_headers(self):
        """Ajoute les en-têtes du tableau"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        headers = [("Alias", self.alias_column_width), ("Action", self.action_column_width), ("Valeur", self.value_column_width), ("Raccourci", self.shortcut_column_width), ("", self.button_def_column_width)]

        for text, width in headers:
            header = QLabel(text)
            header.setFixedWidth(width)
            header.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 150);
                    font-size: 13px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    padding: 8px;
                }
            """)
            header_layout.addWidget(header)
        header_layout.addStretch()
        self.table_layout.addLayout(header_layout)
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 20);")
        separator.setFixedHeight(1)
        self.table_layout.addWidget(separator)
    
    def refresh_clips_order(self):
        """Rafraîchit l'affichage des clips avec le nouvel ordre des actions"""
        # Supprimer l'ancien contenu du table_layout
        while self.table_layout.count():
            child = self.table_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # Supprimer récursivement les sous-layouts
                self._clear_layout(child.layout())
        
        # Recréer les en-têtes
        self._add_headers()
        
        # Repeupler le tableau
        self.populate_table(self.table_layout)
        
        self.table_layout.addStretch()
    
    def _clear_layout(self, layout):
        """Supprime récursivement tous les éléments d'un layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
    
    def populate_table(self, layout):
        """Remplit le tableau avec les boutons fixes et les clips"""
        nb_icons = self.app_instance.nb_icons_menu
        special_buttons = self.app_instance.special_buttons_by_number[nb_icons]
        
        # Section : Boutons fixes
        section_label = QLabel("📌 Boutons fixes")
        section_label.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 12px 8px 4px 8px;
            }
        """)
        layout.addWidget(section_label)
        # supprimer_text = "Supprimer, Stocker, Stock" if self.nb_icons_menu == 5 else "Supprimer"
        # stocker_text = "Stocker, Stock" if self.nb_icons_menu == 6 else "Stocker, Stock" if self.nb_icons_menu == 7 else "Stocker"
        button_descriptions = {
            "➕": "Ajouter un clip",
            "🔧": "Modifier",
            "⚙️": "Configuration",
            "📦": "Stocker, Stock",
            # "💾": stocker_text,
            "💾": "Stocker",
            # "➖": supprimer_text,
            "➖": "Supprimer",
        }
        
        # Afficher dans l'ordre de button_descriptions
        for btn_label, action in button_descriptions.items():
            if btn_label not in special_buttons:
                continue
            shortcut_key = f"fixed_{btn_label}"
            current_shortcut = self.shortcuts.get(shortcut_key, "")
            row = self.create_row(btn_label, action, "", current_shortcut, shortcut_key, is_image=False)
            layout.addLayout(row)
        
        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        sep.setFixedHeight(1)
        layout.addWidget(sep)
        
        # Section : Clips
        section_label2 = QLabel("📎 Clips (1-9 pour accès rapide)")
        section_label2.setStyleSheet("""
            QLabel {
                color: #90EE90;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 12px 8px 4px 8px;
            }
        """)
        layout.addWidget(section_label2)
        
        # Charger les clips depuis le JSON
        clips = self.load_clips()
        
        # Trier les clips selon le mode de tri configuré
        sort_mode = getattr(self.app_instance, 'sort_mode', 'group')
        
        if sort_mode == "group":
            # Tri par zone d'action
            custom_order = getattr(self.app_instance, 'action_order', ["copy", "term", "exec"])
            action_order = {action: i for i, action in enumerate(custom_order)}
            sorted_clips = sorted(clips, key=lambda c: (action_order.get(c.get('action', 'copy'), 999), clips.index(c)))
        elif sort_mode == "alpha":
            # Tri alphabétique
            sorted_clips = sorted(clips, key=lambda c: c.get('alias', '').lower())
        elif sort_mode == "date":
            # Tri par id (date de création)
            sorted_clips = sorted(clips, key=lambda c: c.get('id', 999999))
        else:  # "custom"
            # Ordre du JSON tel quel
            sorted_clips = clips
        
        action_description = {
            "copy" : "copie",
            "term" : "exécute (terminal)",
            "exec" : "exécute",
        }
        for i, clip in enumerate(sorted_clips):
            alias = clip.get('alias', '')
            string = clip.get('string', '')
            action = action_description.get(clip.get('action', 'copy'), clip.get('action', 'copy'))
            
            # Description courte
            value = string[:100] + "..." if len(string) > 50 else string
            value = value.replace('\n', ' ')
            if not string:
                action = "sous-menu"
                value = "Groupe de clips"
            
            # Raccourci par défaut : 1-9 pour les 9 premiers clips (dans l'ordre trié)
            default_shortcut = str(i + 1) if i < 9 else ""
            shortcut_key = f"clip_{alias}"
            current_shortcut = self.shortcuts.get(shortcut_key, default_shortcut)
            
            is_image = "/" in alias
            row = self.create_row(alias, action, value, current_shortcut, shortcut_key, is_image=is_image)
            layout.addLayout(row)
    
    def create_row(self, icon_label, action, value, current_shortcut, shortcut_key, is_image=False):
        """Crée une ligne du tableau"""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)
        
        # Colonne 1 : Icône
        icon_widget = QLabel()
        icon_widget.setFixedSize(self.alias_column_width, 48)
        icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_widget.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 5);
                border-radius: 8px;
                border: none;
            }
        """)
        
        if is_image and "/" in icon_label:
            try:
                pixmap = image_pixmap(icon_label, 40)
                icon_widget.setPixmap(pixmap)
            except:
                icon_widget.setText("🖼️")
                icon_widget.setStyleSheet(icon_widget.styleSheet() + "font-size: 24px; color: white;")
        elif is_emoji(icon_label):
            pixmap = emoji_pixmap(icon_label, 32)
            icon_widget.setPixmap(pixmap)
        else:
            icon_widget.setText(icon_label)
            icon_widget.setStyleSheet(icon_widget.styleSheet() + "font-size: 20px; color: white;")
        
        row_layout.addWidget(icon_widget)
        
        # Colonne 2 : action
        action_label = QLabel(action)
        action_label.setFixedWidth(self.action_column_width)
        action_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                background: transparent;
                border: none;
                padding: 8px;
            }
        """)
        action_label.setWordWrap(True)
        row_layout.addWidget(action_label)
        
        # Colonne 3 : Valeur de string
        value_label = QLabel(value)
        value_label.setFixedWidth(self.value_column_width)
        value_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                background: transparent;
                border: none;
                padding: 8px;
            }
        """)
        value_label.setWordWrap(True)
        row_layout.addWidget(value_label)
        
        # Colonne 4 : Raccourci actuel
        shortcut_label = QLabel(current_shortcut if current_shortcut else "Non défini")
        shortcut_label.setFixedWidth(self.shortcut_column_width)
        shortcut_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcut_label.setStyleSheet(f"""
            QLabel {{
                color: {"#90EE90" if current_shortcut else "rgba(255, 255, 255, 80)"};
                font-size: 13px;
                font-weight: {"bold" if current_shortcut else "normal"};
                background: rgba(255, 255, 255, 5);
                border-radius: 6px;
                border: none;
                padding: 8px;
            }}
        """)
        shortcut_label.setProperty("shortcut_key", shortcut_key)
        row_layout.addWidget(shortcut_label)
        
        # Colonne 5 : Bouton pour définir
        set_btn = QPushButton("Définir")
        set_btn.setFixedWidth(self.button_def_column_width)
        set_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 150, 255, 40);
                border: 1px solid rgba(100, 150, 255, 80);
                border-radius: 6px;
                padding: 8px;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(100, 150, 255, 80);
            }
        """)
        set_btn.clicked.connect(lambda: self.set_shortcut(shortcut_key, shortcut_label))
        row_layout.addWidget(set_btn)
        
        row_layout.addStretch()
        return row_layout
    
    def set_shortcut(self, shortcut_key, label_widget):
        """Ouvre le dialogue de capture de raccourci"""
        current = self.shortcuts.get(shortcut_key, "")
        dialog = ShortcutCaptureDialog(self, current, self.nb_icons_menu)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_shortcut = dialog.captured_shortcut
            
            if new_shortcut is not None:
                # Vérifier les conflits
                if new_shortcut and self.check_conflict(shortcut_key, new_shortcut):
                    return
                
                # Sauvegarder
                if new_shortcut:
                    self.shortcuts[shortcut_key] = new_shortcut
                else:
                    self.shortcuts.pop(shortcut_key, None)
                
                self.save_shortcuts()
                
                # Mettre à jour l'affichage
                label_widget.setText(new_shortcut if new_shortcut else "Non défini")
                label_widget.setStyleSheet(f"""
                    QLabel {{
                        color: {"#90EE90" if new_shortcut else "rgba(255, 255, 255, 80)"};
                        font-size: 13px;
                        font-weight: {"bold" if new_shortcut else "normal"};
                        background: rgba(255, 255, 255, 5);
                        border-radius: 6px;
                        border: none;
                        padding: 8px;
                    }}
                """)
    
    def check_conflict(self, shortcut_key, new_shortcut):
        """Vérifie si le raccourci est déjà utilisé"""
        for key, shortcut in self.shortcuts.items():
            if key != shortcut_key and shortcut == new_shortcut:
                # Conflit trouvé - on pourrait afficher un message
                # Pour l'instant, on écrase simplement l'ancien
                return False
        return False
    
    def close_parent_dialog(self):
        """Ferme le dialog parent (fenêtre de configuration)"""
        if self.dialog_parent:
            self.dialog_parent.accept()
        else:
            self.close()
    
    def confirm_reset_all_shortcuts(self):
        """Affiche une confirmation avant de réinitialiser les raccourcis"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtGui import QPalette, QColor
        
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("⚠️ Confirmation")
        confirm_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        confirm_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        confirm_dialog.setPalette(palette)
        
        confirm_dialog.setFixedSize(350, 180)
        
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 230);
                border-radius: 12px;
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
        """)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Message
        message = QLabel("Réinitialiser tous les raccourcis ?\n\nCette action est irréversible.")
        message.setStyleSheet("color: white; font-size: 14px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(35)
        cancel_button.clicked.connect(confirm_dialog.reject)
        
        reset_button = QPushButton("Réinitialiser")
        reset_button.setFixedHeight(35)
        reset_button.setStyleSheet("""
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
        reset_button.clicked.connect(lambda: (confirm_dialog.accept(), self.reset_all_shortcuts()))
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(reset_button)
        layout.addLayout(buttons_layout)
        
        dialog_layout = QVBoxLayout(confirm_dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        confirm_dialog.exec()
    
    def reset_all_shortcuts(self):
        """Réinitialise tous les raccourcis"""
        self.shortcuts = {}
        self.save_shortcuts()
        # Recharger la fenêtre
        self.close()
        new_window = KeyboardShortcutsManager(self.app_instance, self.parent(), self.nb_icons_menu, self.dialog_parent)
        new_window.show()
    
    def load_clips(self):
        """Charge les clips depuis le fichier JSON"""
        clip_file = self.app_instance.clip_notes_file_json
        if os.path.exists(clip_file):
            try:
                with open(clip_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []


def get_shortcut_for_clip_index(shortcuts_file, index):
    """
    Retourne le raccourci associé à un clip par son index (0-8 pour touches 1-9).
    """
    if index < 0 or index > 8:
        return None
    
    default_shortcut = str(index + 1)
    
    if os.path.exists(shortcuts_file):
        try:
            with open(shortcuts_file, 'r', encoding='utf-8') as f:
                shortcuts = json.load(f)
                for key, shortcut in shortcuts.items():
                    if shortcut == default_shortcut:
                        return key
        except:
            pass
    
    return default_shortcut


def load_shortcuts(script_dir):
    """Charge les raccourcis depuis le fichier"""
    shortcuts_file = os.path.join(script_dir, "shortcuts.json")
    if os.path.exists(shortcuts_file):
        try:
            with open(shortcuts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}