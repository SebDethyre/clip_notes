import sys, os, time, json, subprocess, signal
from PyQt6.QtGui import QPainter, QColor, QIcon, QPalette, QPixmap, QPainterPath
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QHBoxLayout, QSlider, QDialog, QLineEdit
from PyQt6.QtWidgets import QTextEdit, QTextBrowser, QLabel, QFileDialog, QCheckBox, QColorDialog, QScrollArea, QListWidgetItem, QAbstractItemView

from utils import *
from utils import load_clip_notes_data, populate_actions_map_from_data, get_json_order_from_data, get_clip_data_from_data
from ui import EmojiSelector, AutoScrollListWidget, WhiteDropIndicatorStyle, HoverSubMenu, CursorTracker, TooltipWindow, RadialMenu, CalibrationWindow
from ui import KeyboardShortcutsManager

# Cache pour colors.json (chargé une seule fois)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_COLOR_PALETTE_CACHE = None

def _get_color_palette():
    global _COLOR_PALETTE_CACHE
    if _COLOR_PALETTE_CACHE is None:
        with open(os.path.join(_SCRIPT_DIR, "colors.json"), "r") as f:
            _COLOR_PALETTE_CACHE = json.load(f)
    return _COLOR_PALETTE_CACHE

class ClipNotesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = None
        self.current_popup = None
        self.actions_map_sub = {}
        self.buttons_sub = []
        self.update_mode = False
        self.delete_mode = False
        self.store_mode = False
        # self.reorder_mode = False  # Mode réordonnancement sur le cercle
        
        # Créer une fenêtre tooltip pour l'application (utilisée dans les dialogues)
        self.tooltip_window = TooltipWindow()
        self.dialog_emoji_labels = []
        self.nb_icons_config_labels = []
        self.dialog_help_label = None
        self.dialog_help_browser = None  # QTextBrowser pour preview multilignes avec HTML
        self.dialog_slider = None
        self.nb_icons_dialog_slider = None
        self.dialog_image_preview = None  # Label pour l'aperçu de l'image
        self.dialog_temp_image_path = None  # Chemin temporaire de l'image sélectionnée
        self.dialog_remove_image_button = None  # Bouton pour supprimer l'image

        self.central_neon = False
        self.zone_basic_opacity = 15
        self.zone_hover_opacity = 45
        self.show_central_icon = True
        self.nb_icons_menu = 5
        self.auto_apply_icon = True  # Auto-appliquer l'icône détectée

        self.menu_opacity = 100
        self.menu_background_color = (50, 50, 50)
        self.neon_speed = 80
        self.neon_color = (0, 255, 255)
        
        self.shadow_offset = 4
        self.shadow_color = (200, 200, 200)
        self.shadow_enabled = True
        self.shadow_angle = 135  # Angle en degrés (0=droite, 90=bas, 180=gauche, 270=haut)

        self.action_zone_colors = {
            "copy": (255, 150, 100),  # Orange
            "term": (100, 255, 150),  # Vert
            "exec": (100, 150, 255),  # Bleu
        }
        
        self.dialog_style = """
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
        self.special_buttons_by_number = {
            5 : ["➖", "⌨️", "⚙️", "🔧", "➕"],
            6 : ["➖", "📦", "⌨️", "⚙️", "🔧", "➕"],
            7 : ["➖", "📋", "💾", "⌨️", "⚙️", "🔧", "➕"]
        }
        # Attribution des fonctions aux boutons de menus "fixes"
        self.buttons_actions_by_number = {
            5 : {
                    "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
                    "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
                    "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
                    "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
                    "➖": [(self.show_storage_menu, [0,0], {}), "Supprimer", None],
                },
            6 : {
                    "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
                    "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
                    "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
                    "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
                    "📦": [(self.show_storage_menu, [0,0], {}), "Stocker", None],
                    "➖": [(self.delete_clip, [0,0], {}), "Supprimer", None],
                },
            7 : {
                    "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
                    "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
                    "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
                    "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
                    "💾": [(self.store_clip_mode, [0,0], {}), "Stocker", None],
                    "📋": [(self.show_stored_clips_dialog, [0,0], {}), "Stock", None],
                    "➖": [(self.delete_clip, [0,0], {}), "Supprimer", None],
                }
        }
        # self.buttons_actions_by_number = {
        #     5 : {
        #             "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
        #             "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
        #             "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
        #             "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
        #             "➖": [(self.show_storage_menu, [0,0], {}), "Supprimer", None],
        #         },
        #     6 : {
        #             "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
        #             "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
        #             "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
        #             "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
        #             "📦": [(self.show_storage_menu, [0,0], {}), "Stocker", None],
        #             "➖": [(self.delete_clip, [0,0], {}), "Supprimer", None],
        #         },
        #     7 : {
        #             "➕": [(self.new_clip,    [0,0], {}), "Ajouter", None],
        #             "🔧": [(self.update_clip, [0,0], {}), "Modifier", None],
        #             "⚙️": [(self.show_config_dialog, [0,0], {}), "Configurer", None],
        #             "⌨️": [(self.show_shortcuts_dialog, [0,0], {}), "Raccourcis", None],
        #             "💾": [(self.store_clip_mode, [0,0], {}), "Stocker", None],
        #             "📋": [(self.show_stored_clips_dialog, [0,0], {}), "Stock", None],
        #             "➖": [(self.delete_clip, [0,0], {}), "Supprimer", None],
        #         }
        # }

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.clip_notes_file_json = os.path.join(self.script_dir, "clip_notes.json")
        self.emojis_file = os.path.join(self.script_dir, "emojis.txt")
        self.thumbnails_dir = os.path.join(self.script_dir, "thumbnails")
        self.config_file = os.path.join(self.script_dir, "config.json")
        self.stored_clips_file = os.path.join(self.script_dir, "stored_clips.json")
        self.color_palette = _get_color_palette()
        # Créer le dossier des miniatures s'il n'existe pas
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        # Charger la configuration au démarrage
        self.load_config()
    
    def get_update_mode(self):
        return self.update_mode
    
    def get_delete_mode(self):
        return self.delete_mode
    
    def get_store_mode(self):
        return self.store_mode
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.central_neon = config.get('central_neon', self.central_neon)
            self.zone_basic_opacity = config.get('zone_basic_opacity', self.zone_basic_opacity)
            self.zone_hover_opacity = config.get('zone_hover_opacity', self.zone_hover_opacity)
            self.show_central_icon = config.get('show_central_icon', self.show_central_icon)
            self.nb_icons_menu = config.get('nb_icons_menu', self.nb_icons_menu)
            self.auto_apply_icon = config.get('auto_apply_icon', self.auto_apply_icon)
            self.menu_opacity = config.get('menu_opacity', self.menu_opacity)
            self.neon_speed = config.get('neon_speed', self.neon_speed)

            menu_bg = config.get('menu_background_color', self.menu_background_color)
            self.menu_background_color = tuple(menu_bg) if isinstance(menu_bg, list) else menu_bg
            
            # Charger la couleur du néon
            neon_col = config.get('neon_color', self.neon_color)
            self.neon_color = tuple(neon_col) if isinstance(neon_col, list) else neon_col
            
            # Charger les paramètres d'ombre
            self.shadow_offset = config.get('shadow_offset', self.shadow_offset)
            shadow_col = config.get('shadow_color', self.shadow_color)
            self.shadow_color = tuple(shadow_col) if isinstance(shadow_col, list) else shadow_col
            self.shadow_enabled = config.get('shadow_enabled', self.shadow_enabled)
            self.shadow_angle = config.get('shadow_angle', self.shadow_angle)
            
            # Charger les couleurs et migrer l'ancien format si nécessaire
            loaded_colors = config.get('action_zone_colors', self.action_zone_colors)
            self.action_zone_colors = {}
            
            for action, color_value in loaded_colors.items():
                if isinstance(color_value, str):
                    # Ancien format : nom de couleur -> convertir en RGB
                    if color_value in self.color_palette:
                        self.action_zone_colors[action] = self.color_palette[color_value]
                        print(f"[Config] Migration: {action} '{color_value}' -> {self.color_palette[color_value]}")
                    else:
                        # Couleur inconnue, utiliser la valeur par défaut
                        default_colors = {
                            "copy": (255, 150, 100),
                            "term": (100, 255, 150),
                            "exec": (100, 150, 255)
                        }
                        self.action_zone_colors[action] = default_colors.get(action, (255, 255, 255))
                elif isinstance(color_value, list):
                    # Nouveau format : liste RGB -> convertir en tuple
                    self.action_zone_colors[action] = tuple(color_value)
                else:
                    # Déjà un tuple
                    self.action_zone_colors[action] = color_value
            
            print(f"[Config] Configuration chargée: {config}")
        except Exception as e:
            print(f"[Erreur] Impossible de charger la configuration: {e}")

    def save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        config = {
            'central_neon': self.central_neon,
            'zone_basic_opacity': self.zone_basic_opacity,
            'zone_hover_opacity': self.zone_hover_opacity,
            'show_central_icon': self.show_central_icon,
            'nb_icons_menu': self.nb_icons_menu,
            'auto_apply_icon': self.auto_apply_icon,
            'action_zone_colors': self.action_zone_colors,
            'menu_opacity': self.menu_opacity,
            'menu_background_color': self.menu_background_color,
            'neon_color': self.neon_color,
            'neon_speed': self.neon_speed,
            'shadow_offset': self.shadow_offset,
            'shadow_color': self.shadow_color,
            'shadow_enabled': self.shadow_enabled,
            'shadow_angle': self.shadow_angle
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            # print(f"[Config] Configuration sauvegardée: {config}")
        except Exception as e:
            print(f"[Erreur] Impossible de sauvegarder la configuration: {e}")

    # ===== GESTION DES CLIPS STOCKÉS =====
    def load_stored_clips(self):
        """Charge les clips stockés depuis le fichier JSON"""
        if not os.path.exists(self.stored_clips_file):
            return []
        
        try:
            with open(self.stored_clips_file, 'r', encoding='utf-8') as f:
                clips = json.load(f)
            print(f"[Stored Clips] {len(clips)} clips chargés")
            return clips
        except Exception as e:
            print(f"[Erreur] Impossible de charger les clips stockés: {e}")
            return []

    def save_stored_clips(self, clips):
        """Sauvegarde les clips stockés dans le fichier JSON"""
        try:
            with open(self.stored_clips_file, 'w', encoding='utf-8') as f:
                json.dump(clips, f, indent=4, ensure_ascii=False)
            print(f"[Stored Clips] {len(clips)} clips sauvegardés")
        except Exception as e:
            print(f"[Erreur] Impossible de sauvegarder les clips stockés: {e}")

    def add_stored_clip(self, alias, action, string, html_string=None):
        """Ajoute un clip au stockage"""
        clips = self.load_stored_clips()
        new_clip = {
            'alias': alias,
            'action': action,
            'string': string
        }
        # Ajouter le HTML seulement s'il est fourni
        if html_string:
            new_clip['html_string'] = html_string
        clips.append(new_clip)
        self.save_stored_clips(clips)
        return clips

    def remove_stored_clip(self, alias):
        """Supprime un clip du stockage"""
        clips = self.load_stored_clips()
        clips = [clip for clip in clips if clip.get('alias') != alias]
        self.save_stored_clips(clips)
        return clips

    def eventFilter(self, watched, event):
        """Gère les événements de hover et de clic sur les widgets du dialogue"""
        if event.type() == QEvent.Type.Enter:
            # Vérifier les icônes d'action (avec tooltip_text)
            if watched in self.dialog_emoji_labels:
                tooltip_text = watched.property("tooltip_text")
                if tooltip_text and self.dialog_help_label:
                    self.dialog_help_label.setText(tooltip_text)
                    self.dialog_help_label.setVisible(True)
                    if hasattr(self, 'dialog_help_browser') and self.dialog_help_browser:
                        self.dialog_help_browser.setVisible(False)
            # Vérifier les autres widgets (avec help_text)
            else:
                help_text = watched.property("help_text")
                html_string = watched.property("html_string")
                
                if help_text:
                    # Déterminer si c'est multiligne
                    line_count = help_text.count('\n') + 1
                    is_multiline = line_count > 1
                    
                    if is_multiline and hasattr(self, 'dialog_help_browser') and self.dialog_help_browser:
                        # Multilignes → utiliser le QTextBrowser
                        if html_string:
                            self.dialog_help_browser.setHtml(html_string)
                        else:
                            self.dialog_help_browser.setPlainText(help_text)
                        self.dialog_help_browser.setVisible(True)
                        if self.dialog_help_label:
                            self.dialog_help_label.setVisible(False)
                    elif self.dialog_help_label:
                        # Une seule ligne → utiliser le label simple (avec HTML si disponible)
                        if html_string:
                            # Activer le rendu HTML et afficher le HTML
                            self.dialog_help_label.setTextFormat(Qt.TextFormat.RichText)
                            self.dialog_help_label.setText(html_string)
                        else:
                            # Texte simple
                            self.dialog_help_label.setTextFormat(Qt.TextFormat.PlainText)
                            self.dialog_help_label.setText(help_text)
                        self.dialog_help_label.setVisible(True)
                        if hasattr(self, 'dialog_help_browser') and self.dialog_help_browser:
                            self.dialog_help_browser.setVisible(False)
        elif event.type() == QEvent.Type.Leave:
            # Vider et cacher les widgets d'aide
            if self.dialog_help_label:
                self.dialog_help_label.setTextFormat(Qt.TextFormat.PlainText)
                self.dialog_help_label.setText("")
                self.dialog_help_label.setVisible(True)
            if hasattr(self, 'dialog_help_browser') and self.dialog_help_browser:
                self.dialog_help_browser.clear()
                self.dialog_help_browser.setVisible(False)
        elif event.type() == QEvent.Type.MouseButtonPress:
            # Gérer les clics sur les emojis pour changer le slider
            if watched in self.dialog_emoji_labels and self.dialog_slider:
                slider_value = watched.property("slider_value")
                if slider_value is not None:
                    self.dialog_slider.setValue(slider_value)
            if watched in self.nb_icons_config_labels and self.nb_icons_dialog_slider:
                slider_value = watched.property("slider_value")
                if slider_value is not None:
                    self.nb_icons_dialog_slider.setValue(slider_value)
        
        return super().eventFilter(watched, event)

    def get_action_from_json(self, alias):
        """Lit l'action d'un clip depuis le fichier JSON"""
        try:
            if os.path.exists(self.clip_notes_file_json):
                with open(self.clip_notes_file_json, 'r', encoding='utf-8') as f:
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

    def get_clip_data_from_json(self, alias):
        """
        Lit toutes les données d'un clip depuis le fichier JSON.
        
        Returns:
            tuple: (slider_value, html_string ou None)
        """
        try:
            if os.path.exists(self.clip_notes_file_json):
                with open(self.clip_notes_file_json, 'r', encoding='utf-8') as f:
                    clips = json.load(f)
                    for clip in clips:
                        if clip.get('alias') == alias:
                            action = clip.get('action', 'copy')
                            action_to_slider = {
                                'copy': 0,
                                'term': 1,
                                'exec': 2
                            }
                            slider_value = action_to_slider.get(action, 0)
                            html_string = clip.get('html_string', None)
                            return (slider_value, html_string)
        except Exception as e:
            print(f"Erreur lecture JSON: {e}")
        return (0, None)

    def refresh_menu(self):
        """Rafraîchit le menu en mettant à jour les boutons existants"""
        if not self.current_popup:
            return
        
        # Réinitialiser le state
        self.current_popup.set_central_text("")
        self.current_popup.set_neon_color(self.neon_color)
        self.current_popup.toggle_neon(self.central_neon)

        # Reconstruire buttons_sub depuis actions_map_sub avec tri
        self.buttons_sub = []
        x, y = self.x, self.y
    
        # ===== OPTIMISATION : charger le JSON une seule fois =====
        json_data = load_clip_notes_data(self.clip_notes_file_json)
        
        self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        populate_actions_map_from_data(json_data, self.actions_map_sub, execute_command)
        # Séparer les boutons spéciaux des autres
        clips_to_sort = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON (données déjà chargées)
        json_order = get_json_order_from_data(json_data)
        
        # Trier seulement les clips (pas les boutons spéciaux)
        sorted_clips = sort_actions_map(clips_to_sort, json_order)
        
        # Ajouter d'abord les boutons spéciaux dans l'ordre fixe
        for name in special_buttons:
            if name in self.actions_map_sub:
                action_data, value, action = self.actions_map_sub[name]
                tooltip = value.replace(r'\n', '\n')
                self.buttons_sub.append((name, self.make_handler_sub(name, value, self.x, self.y), tooltip, action))
        
        # Puis ajouter les clips triés (avec le HTML pour les tooltips)
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            # Récupérer le HTML du clip (données déjà chargées)
            _, clip_html = get_clip_data_from_data(json_data, name)
            self.buttons_sub.append((name, self.make_handler_sub(name, value, self.x, self.y), tooltip, action, clip_html))
        
        # Construire clips_by_link dans le même ordre que buttons_sub
        clips_by_link = []
        # D'abord les boutons spéciaux (toujours 1)
        for name in special_buttons:
            if name in self.actions_map_sub:
                clips_by_link.append(1)
        # Puis les clips triés
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)
        
        # CRITIQUE: Propager nb_icons_menu et autres paramètres au popup AVANT update_buttons
        # Sinon l'escamotage des icônes fixes ne correspondra pas à la nouvelle configuration
        self.current_popup.nb_icons_menu = self.nb_icons_menu
        self.current_popup.action_zone_colors = self.action_zone_colors
        self.current_popup.show_central_icon = self.show_central_icon
        self.current_popup.menu_background_color = self.menu_background_color
        self.current_popup.zone_basic_opacity = self.zone_basic_opacity
        self.current_popup.zone_hover_opacity = self.zone_hover_opacity
        self.current_popup.shadow_offset = self.shadow_offset
        self.current_popup.shadow_color = self.shadow_color
        self.current_popup.shadow_enabled = self.shadow_enabled
        self.current_popup.shadow_angle = self.shadow_angle
        
        # Mettre à jour les boutons du menu existant
        self.current_popup.update_buttons(self.buttons_sub)
        # Mettre à jour clips_by_link pour les badges de groupe
        self.current_popup.update_clips_by_link(clips_by_link)
        # Réappliquer l'opacité configurée
        self.current_popup.set_widget_opacity(self.menu_opacity / 100.0)
        # Réappliquer le néon central configuré
        self.current_popup.toggle_neon(self.central_neon)
        if self.central_neon:
            # Redémarrer le timer avec la nouvelle vitesse
            self.current_popup.timer.stop()
            self.current_popup.timer.start(self.neon_speed)
        # CRITIQUE: Forcer le mouse tracking après le refresh
        self.current_popup.setMouseTracking(True)

    def update_clip(self, x, y, context = "from_radial"):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y

        # Activer le mode modification seulement si c'est depuis le menu radial
        if context == "from_radial":
            self.update_mode = True
        
        # Filtrer les clips (sans les boutons d'action)
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON pour le tri personnalisé
        json_order = get_json_order(self.clip_notes_file_json)
        
        # Trier les clips en respectant l'ordre du JSON
        sorted_clips = sort_actions_map(clips_only, json_order)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            # Lire l'action ET le HTML depuis le JSON pour ce clip
            clip_slider_value, clip_html = self.get_clip_data_from_json(name)
            tooltip = value.replace(r'\n', '\n')
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_edit(name, value, x, y, clip_slider_value, clip_html),
                    tooltip,
                    action,
                    clip_html  # 5ème élément : HTML pour le tooltip
                )
            )
        clips_by_link = []
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("🔧")
            self.current_popup.update_clips_by_link(clips_by_link)
            self.current_popup.set_neon_color("jaune")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)

    def make_handler_edit(self, name, value, x, y, slider_value, html_string=None):
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            
            from utils import is_group
            # Vérifier si c'est un groupe
            if is_group(self.clip_notes_file_json, name):
                self.show_group_edit_dialog(name, x, y)
            else:
                self.edit_clip(name, value, x, y, slider_value, html_string=html_string)
        return handler

    def delete_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode suppression
        self.delete_mode = True
        # Filtrer les clips (sans les boutons d'action)
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON pour le tri personnalisé
        json_order = get_json_order(self.clip_notes_file_json)
        
        # Trier les clips en respectant l'ordre du JSON
        sorted_clips = sort_actions_map(clips_only, json_order)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            # Récupérer le HTML pour le tooltip
            _, clip_html = self.get_clip_data_from_json(name)
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_delete(name, value, x, y),
                    tooltip,
                    action,
                    clip_html  # 5ème élément : HTML pour le tooltip
                )
            )
        clips_by_link = []
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("➖")
            self.current_popup.update_clips_by_link(clips_by_link)
            self.current_popup.set_neon_color("rouge")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)

    def reorder_clip_mode(self, x, y):
        """Active le mode réordonnancement par drag & drop sur le cercle"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Activer le mode réordonnancement
        self.reorder_mode = True
        
        # IMPORTANT: Recharger actions_map_sub depuis le JSON pour avoir les actions à jour
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        
        # Recréer actions_map_sub avec les boutons spéciaux
        self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
        
        # Recharger les clips depuis le JSON (avec leurs nouvelles actions)
        populate_actions_map_from_file(self.clip_notes_file_json, self.actions_map_sub, execute_command)
        
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON pour le tri personnalisé
        json_order = get_json_order(self.clip_notes_file_json)
        
        # Trier les clips en respectant l'ordre du JSON
        sorted_clips = sort_actions_map(clips_only, json_order)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            # Récupérer le HTML pour le tooltip
            _, clip_html = self.get_clip_data_from_json(name)
            self.buttons_sub.append(
                (
                    name, 
                    lambda: None,  # Pas de callback car on utilise le drag & drop
                    tooltip,
                    action,
                    clip_html  # 5ème élément : HTML pour le tooltip
                )
            )
        
        # Construire clips_by_link dans le même ordre que buttons_sub (seulement les clips triés)
        clips_by_link = []
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.update_clips_by_link(clips_by_link)
            self.current_popup.set_central_text("↔️")
            self.current_popup.set_neon_color("cyan")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)
            # Activer le mode réordonnancement sur le RadialMenu
            self.current_popup.reorder_mode = True
            # Afficher un message d'aide
            self.current_popup.tooltip_window.show_message("Glissez un clip pour le déplacer", 3000)
            self.current_popup.update_tooltip_position()

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
        content.setStyleSheet(self.dialog_style)

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
            from utils import is_group, delete_group_from_json
            
            # Vérifier si c'est un groupe
            if is_group(self.clip_notes_file_json, name):
                # Supprimer le groupe et tous ses clips
                delete_group_from_json(self.clip_notes_file_json, name)
            else:
                # Supprimer un clip normal
                delete_from_json(self.clip_notes_file_json, name)
                # Supprimer l'ancien thumbnail s'il existe
                if os.path.exists(name):
                    if "/usr" not in name and "/share" not in name:
                        os.remove(name)
            
            self.actions_map_sub.pop(name, None)
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
                
                # Vérifier si c'est un groupe
                if isinstance(func_data, tuple) and len(func_data) == 3:
                    func, args, kwargs = func_data
                    
                    # Si c'est un groupe, ouvrir le sous-menu du groupe
                    if kwargs.get('is_group'):
                        children = args  # args contient la liste des enfants
                        self.show_group_submenu(name, children, x, y)
                        return
                    
                    # Sinon, exécuter la fonction normalement
                    func(*args, **kwargs)
                    special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
                    if name not in special_buttons:
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
                            self.current_popup.update_tooltip_position()
                            # Fermer après 1 seconde
                            QTimer.singleShot(300, self.close_popup)
                        else:
                            # Fermer immédiatement si pas de message
                            self.close_popup()
                else:
                    print(f"Aucune fonction associée à '{name}'")
        return handler_sub
    
    def show_group_submenu(self, group_alias, children, x, y):
        """Affiche un sous-menu pour un groupe de clips"""
        
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Construire les boutons pour chaque enfant du groupe
        # Format attendu par HoverSubMenu: (label, callback, tooltip)
        submenu_buttons = []
        for child in children:
            child_alias = child.get('alias', '')
            child_string = child.get('string', '')
            child_action = child.get('action', 'copy')
            
            # Créer le handler selon le mode actif
            if self.update_mode:
                handler = self.make_group_child_edit_handler(group_alias, child_alias, child_string, child_action, x, y)
            elif self.delete_mode:
                handler = self.make_group_child_delete_handler(group_alias, child_alias, child_string, x, y)
            elif self.store_mode:
                handler = self.make_group_child_store_handler(group_alias, child_alias, child_string, child_action, x, y)
            else:
                handler = self.make_group_child_handler(child_alias, child_string, child_action, group_alias)
            
            tooltip = child_string.replace(r'\n', '\n')
            # Format: (label, callback, tooltip)
            submenu_buttons.append((child_alias, handler, tooltip))
        
        # Fermer l'ancien sous-menu s'il existe
        if self.current_popup and self.current_popup.hover_submenu:
            try:
                self.current_popup.hover_submenu.close()
            except RuntimeError:
                pass
        
        # Créer le sous-menu avec les bons paramètres
        # Signature: __init__(self, center_x, center_y, buttons, parent_menu=None, app_instance=None)
        submenu = HoverSubMenu(
            x, y,
            submenu_buttons,
            parent_menu=self.current_popup,
            app_instance=self
        )
        
        # Stocker la référence au groupe
        submenu.group_alias = group_alias
        submenu.is_group_submenu = True
        
        if self.current_popup:
            self.current_popup.hover_submenu = submenu
        
        submenu.show()
    
    def make_group_child_edit_handler(self, group_alias, child_alias, child_string, child_action, x, y):
        """Handler pour éditer un clip enfant de groupe"""
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x_pos, y_pos = self.tracker.last_x, self.tracker.last_y
            else:
                x_pos, y_pos = x, y
            self.edit_group_child_clip(group_alias, child_alias, child_string, child_action, x_pos, y_pos)
        return handler
    
    def make_group_child_delete_handler(self, group_alias, child_alias, child_string, x, y):
        """Handler pour supprimer un clip enfant de groupe"""
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x_pos, y_pos = self.tracker.last_x, self.tracker.last_y
            else:
                x_pos, y_pos = x, y
            self.delete_group_child_clip(group_alias, child_alias, child_string, x_pos, y_pos)
        return handler
    
    def make_group_child_store_handler(self, group_alias, child_alias, child_string, child_action, x, y):
        """Handler pour stocker un clip enfant de groupe"""
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x_pos, y_pos = self.tracker.last_x, self.tracker.last_y
            else:
                x_pos, y_pos = x, y
            self.store_group_child_clip(group_alias, child_alias, child_string, child_action, x_pos, y_pos)
        return handler
    
    def make_group_child_handler(self, alias, string, action, group_alias):
        """Crée un handler pour un clip enfant d'un groupe"""
        def handler():
            from utils import paperclip_copy, execute_terminal, execute_command
            
            # Exécuter l'action du clip
            if action == "copy":
                paperclip_copy(string)
                message = f'"{string}" copié'
            elif action == "term":
                execute_terminal(string)
                message = f'"{string}" exécuté dans un terminal'
            elif action == "exec":
                execute_command(string)
                message = f'"{string}" lancé'
            else:
                message = None
            
            # Afficher le message et fermer
            if message and self.current_popup:
                self.current_popup.tooltip_window.show_message(message, 1000)
                self.current_popup.update_tooltip_position()
                QTimer.singleShot(300, self.close_popup)
            else:
                self.close_popup()
        
        return handler
    
    def show_group_edit_dialog(self, group_alias, x, y):
        """Affiche une fenêtre d'édition pour un groupe"""
        from utils import get_group_children, update_group_alias, remove_clip_from_group, add_clip_to_group, is_emoji, image_pixmap, emoji_pixmap
        from ui import AutoScrollListWidget, EmojiSelector
        
        # Récupérer les enfants du groupe
        children = get_group_children(self.clip_notes_file_json, group_alias)
        if children is None:
            return
        
        # Variable pour stocker le chemin d'image temporaire
        dialog_temp_image_path = None
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("📁 Modifier le groupe")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Appliquer une palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        dialog.setPalette(palette)
        
        dialog.setFixedSize(550, 550)
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x - dialog.width() // 2, y - dialog.height() // 2)
        
        content = QWidget()
        content.setStyleSheet(self.dialog_style)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # === Section icône du groupe ===
        icon_section = QVBoxLayout()
        icon_section.setSpacing(8)
        
        icon_header = QHBoxLayout()
        icon_label = QLabel("Icône du groupe:")
        icon_label.setStyleSheet("color: white; font-weight: bold;")
        icon_header.addWidget(icon_label)
        icon_header.addStretch()
        icon_section.addLayout(icon_header)
        
        # Layout pour l'icône et les boutons
        icon_row = QHBoxLayout()
        icon_row.setSpacing(10)
        
        # Aperçu de l'icône actuelle
        icon_preview = QLabel()
        icon_preview.setFixedSize(60, 60)
        icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_preview.setStyleSheet("""
            QLabel {
                border: 2px solid rgba(255, 255, 255, 30);
                border-radius: 30px;
                background-color: rgba(0, 0, 0, 50);
            }
        """)
        
        def update_icon_preview(alias):
            """Met à jour l'aperçu de l'icône"""
            if "/" in alias:
                pixmap = image_pixmap(alias, 50)
            elif is_emoji(alias):
                pixmap = emoji_pixmap(alias, 40)
            else:
                from utils import text_pixmap
                pixmap = text_pixmap(alias, 30)
            icon_preview.setPixmap(pixmap)
        
        update_icon_preview(group_alias)
        icon_row.addWidget(icon_preview)
        
        # Input pour l'icône (texte/emoji)
        icon_input = QLineEdit(group_alias if "/" not in group_alias else "")
        icon_input.setMaxLength(10)
        icon_input.setFixedWidth(80)
        icon_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 6px;
                padding: 6px;
                color: white;
                font-size: 18px;
            }
        """)
        icon_input.setPlaceholderText("📁")
        
        # Connecter pour mettre à jour l'aperçu
        def on_icon_text_changed(text):
            nonlocal dialog_temp_image_path
            if text and "/" not in text:
                dialog_temp_image_path = None  # Reset image si on tape du texte
                update_icon_preview(text)
        icon_input.textChanged.connect(on_icon_text_changed)
        
        icon_row.addWidget(icon_input)
        # Layout horizontal pour les boutons emoji et image
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
                
        # Bouton Emoji
        emoji_button = QPushButton("😀")
        emoji_button.setFixedSize(40, 40)
        emoji_button.setProperty("help_text", "Attribuer un emoji")
        emoji_button.installEventFilter(self)
        
        def open_emoji_selector():
            path = self.emojis_file
            if not os.path.exists(path):
                print(f"Fichier introuvable : {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                emojis = [line.strip() for line in f if line.strip()]
            selector = EmojiSelector(emojis, parent=dialog)

            def on_emoji_selected(emoji):
                # Remplacer tout le texte par l'emoji sélectionné
                icon_input.setFocus()
                icon_input.setText(emoji)
                icon_input.setCursorPosition(len(emoji))
                # update_icon_preview(emoji)
                selector.accept()

            selector.emoji_selected = on_emoji_selected
            # if selector.exec() == QDialog.DialogCode.Accepted and selector.selected_emoji:
            #     icon_input.setText(selector.selected_emoji)
            selector.exec()
        
        emoji_button.clicked.connect(open_emoji_selector)
        icon_row.addWidget(emoji_button)
        
        # Bouton Image
        image_button = QPushButton("🖼️")
        image_button.setFixedSize(40, 40)
        image_button.setProperty("help_text", "Attribuer une image ( 🟩 : icône trouvée )")
        image_button.installEventFilter(self)
        
        def open_image_selector():
            nonlocal dialog_temp_image_path
            start_dir = get_pictures_directory()
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Choisir une image",
                start_dir,
                "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Tous les fichiers (*)"
            )
            
            if file_path:
                # L'utilisateur a choisi manuellement, désactiver la détection auto
                # auto_icon_applied[0] = False
                # last_auto_icon_path[0] = None
                # manual_override[0] = True  # Protéger le choix manuel
                
                # Stocker le chemin temporairement (ne pas créer le thumbnail maintenant)
                self.dialog_temp_image_path = file_path
                
                # Mettre seulement le nom de fichier (sans chemin) dans name_input
                file_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(file_name)[0]
                icon_input.setText(name_without_ext)
                
                # Afficher l'aperçu de l'image
                # if self.dialog_image_preview:
                #     pixmap = QPixmap(file_path)
            if file_path:
                dialog_temp_image_path = file_path
                icon_input.setText("")  # Vider le champ texte
                # Afficher l'aperçu
                pixmap = QPixmap(file_path).scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_preview.setPixmap(pixmap)
        
        image_button.clicked.connect(open_image_selector)
        # Checkbox pour auto-appliquer l'icône détectée
        auto_apply_checkbox = QCheckBox("Icône auto")
        auto_apply_checkbox.setChecked(self.auto_apply_icon)
        auto_apply_checkbox.setProperty("help_text", "Appliquer automatiquement l'icône détectée")
        auto_apply_checkbox.installEventFilter(self)
        auto_apply_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: rgba(100, 200, 100, 150);
                border: 1px solid rgba(100, 255, 100, 200);
                border-radius: 3px;
            }
        """)
        
        # Répartition : Emoji et Image prennent chacun 2 parts, Auto prend 1 part
        icon_row.addWidget(emoji_button, 2)
        icon_row.addWidget(image_button, 2)
        icon_row.addWidget(auto_apply_checkbox, 1, Qt.AlignmentFlag.AlignCenter)
        
        # search_input = QLineEdit()
        # icon_row.addWidget(image_button, 2)
        # value_input = QTextEdit()
        # value_input.setMinimumHeight(80)
        # value_input.setProperty("help_text", "Valeur")
        # value_input.installEventFilter(self)

        # auto_icon_layout.addWidget(auto_checkbox)
        # auto_icon_layout.addWidget(search_input)
        # icon_row.addLayout(auto_icon_layout)
        
        icon_row.addStretch()
        icon_section.addLayout(buttons_row)
        icon_section.addLayout(icon_row)
        layout.addLayout(icon_section)
        
        # === Tooltip label ===
        tooltip_label = QLabel("")
        tooltip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tooltip_label.setStyleSheet("color: #aaa; font-size: 12px; padding: 4px; min-height: 40px;")
        tooltip_label.setWordWrap(True)
        layout.addWidget(tooltip_label)
        
        # === Deux listes côte à côte ===
        lists_layout = QHBoxLayout()
        
        # Fonction helper pour créer un item avec icône
        def create_list_item(alias, string):
            """Crée un QListWidgetItem avec icône appropriée"""
            # Afficher alias ou icône
            if "/" in alias:
                display_text = f"[IMG] - {string[:25]}..."
            else:
                display_text = f"{alias} - {string[:25]}..."
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, alias)
            item.setData(Qt.ItemDataRole.UserRole + 1, string)  # Stocker la string pour le tooltip
            
            # Ajouter une icône
            if "/" in alias:
                icon = QIcon(image_pixmap(alias, 24))
            elif is_emoji(alias):
                icon = QIcon(emoji_pixmap(alias, 20))
            else:
                from utils import text_pixmap
                icon = QIcon(text_pixmap(alias, 16))
            item.setIcon(icon)
            
            return item
        
        # Liste des clips dans le groupe
        group_layout = QVBoxLayout()
        group_label = QLabel("Clips dans le groupe:")
        group_label.setStyleSheet("color: white; font-weight: bold;")
        group_list = AutoScrollListWidget()
        group_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        group_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        group_list.setIconSize(QSize(24, 24))
        group_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 6px;
                color: white;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 20);
            }
            QListWidget::item:selected {
                background-color: rgba(100, 150, 255, 100);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        
        # Remplir la liste du groupe
        for child in children:
            item = create_list_item(child.get('alias', ''), child.get('string', ''))
            group_list.addItem(item)
        
        # Connecter le survol pour le tooltip
        def on_group_item_hover(item):
            if item:
                string = item.data(Qt.ItemDataRole.UserRole + 1)
                tooltip_label.setText(string.replace('\\n', '\n') if string else "")
            else:
                tooltip_label.setText("")
        
        group_list.itemEntered.connect(on_group_item_hover)
        group_list.setMouseTracking(True)
        
        group_layout.addWidget(group_label)
        group_layout.addWidget(group_list)
        lists_layout.addLayout(group_layout)
        
        # Boutons de transfert
        transfer_layout = QVBoxLayout()
        transfer_layout.addStretch()
        
        btn_to_available = QPushButton("→")
        btn_to_available.setFixedSize(40, 40)
        btn_to_available.setToolTip("Retirer du groupe")
        
        btn_to_group = QPushButton("←")
        btn_to_group.setFixedSize(40, 40)
        btn_to_group.setToolTip("Ajouter au groupe")
        
        transfer_layout.addWidget(btn_to_available)
        transfer_layout.addWidget(btn_to_group)
        transfer_layout.addStretch()
        lists_layout.addLayout(transfer_layout)
        
        # Liste des clips disponibles (hors du groupe)
        available_layout = QVBoxLayout()
        available_label = QLabel("Clips disponibles:")
        available_label.setStyleSheet("color: white; font-weight: bold;")
        available_list = AutoScrollListWidget()
        available_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        available_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        available_list.setIconSize(QSize(24, 24))
        available_list.setStyleSheet(group_list.styleSheet())
        available_list.setMouseTracking(True)
        
        # Connecter le survol pour le tooltip
        def on_available_item_hover(item):
            if item:
                string = item.data(Qt.ItemDataRole.UserRole + 1)
                tooltip_label.setText(string.replace('\\n', '\n') if string else "")
            else:
                tooltip_label.setText("")
        
        available_list.itemEntered.connect(on_available_item_hover)
        
        # Remplir la liste des clips disponibles
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        children_aliases = [c.get('alias') for c in children]
        
        for name, (action_data, value, action) in self.actions_map_sub.items():
            if name not in special_buttons and name != group_alias:
                # Vérifier si c'est un groupe ou un clip dans un groupe
                func_data = action_data
                if isinstance(func_data, tuple) and len(func_data) == 3:
                    _, _, kwargs = func_data
                    if kwargs.get('is_group'):
                        continue  # Ne pas lister les autres groupes
                
                if name not in children_aliases:
                    item = create_list_item(name, value)
                    available_list.addItem(item)
        
        available_layout.addWidget(available_label)
        available_layout.addWidget(available_list)
        lists_layout.addLayout(available_layout)
        
        layout.addLayout(lists_layout)
        
        # === Fonctions de transfert ===
        def transfer_to_available():
            """Retire le clip sélectionné du groupe"""
            current_item = group_list.currentItem()
            if current_item:
                group_list.takeItem(group_list.row(current_item))
                available_list.addItem(current_item)
        
        def transfer_to_group():
            """Ajoute le clip sélectionné au groupe"""
            current_item = available_list.currentItem()
            if current_item:
                available_list.takeItem(available_list.row(current_item))
                group_list.addItem(current_item)
        
        btn_to_available.clicked.connect(transfer_to_available)
        btn_to_group.clicked.connect(transfer_to_group)
        
        # === Boutons de validation ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(32)
        cancel_button.clicked.connect(dialog.reject)
        
        save_button = QPushButton("Enregistrer")
        save_button.setFixedHeight(32)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 200, 100, 150);
                border: 1px solid rgba(150, 255, 150, 200);
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(120, 220, 120, 200);
            }
        """)
        
        def save_changes():
            nonlocal dialog_temp_image_path
            from utils import update_group_alias, remove_clip_from_group, add_clip_to_group, get_group_children, is_group
            
            # Déterminer le nouvel alias
            if dialog_temp_image_path:
                # Créer un thumbnail pour l'image
                new_alias = create_thumbnail(dialog_temp_image_path, self.thumbnails_dir)
                if not new_alias:
                    new_alias = group_alias  # Fallback
            else:
                new_alias = icon_input.text().strip() or group_alias
            
            current_alias = group_alias
            
            # Mettre à jour l'alias si changé
            if new_alias and new_alias != group_alias:
                update_group_alias(self.clip_notes_file_json, group_alias, new_alias)
                current_alias = new_alias
            
            # Récupérer les clips actuels dans le groupe (depuis le JSON)
            current_children = get_group_children(self.clip_notes_file_json, current_alias)
            current_aliases = [c.get('alias') for c in current_children] if current_children else []
            
            # Récupérer les clips de la liste UI
            new_aliases = []
            for i in range(group_list.count()):
                item = group_list.item(i)
                new_aliases.append(item.data(Qt.ItemDataRole.UserRole))
            
            # Trouver les clips à retirer
            to_remove = [a for a in current_aliases if a not in new_aliases]
            # Trouver les clips à ajouter
            to_add = [a for a in new_aliases if a not in current_aliases]
            
            # Retirer les clips (vérifier si le groupe existe encore après chaque retrait)
            for alias in to_remove:
                # Vérifier si le groupe existe encore (il peut avoir été dissous)
                if not is_group(self.clip_notes_file_json, current_alias):
                    break  # Le groupe a été dissous, arrêter les retraits
                remove_clip_from_group(self.clip_notes_file_json, current_alias, alias)
            
            # Ajouter les clips (seulement si le groupe existe encore)
            for alias in to_add:
                if is_group(self.clip_notes_file_json, current_alias):
                    add_clip_to_group(self.clip_notes_file_json, current_alias, alias)
            
            dialog.accept()
            
            # Recharger actions_map_sub depuis le JSON
            special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
            self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
            populate_actions_map_from_file(self.clip_notes_file_json, self.actions_map_sub, execute_command)
            
            # Rafraîchir le menu en restant en mode update
            self.update_clip(x, y, context="keep_mode")
        
        save_button.clicked.connect(save_changes)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(save_button)
        layout.addLayout(buttons_layout)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        dialog.exec()
        
        # Réactiver le mouse tracking
        if self.current_popup:
            self.current_popup.setMouseTracking(True)
    
    def edit_group_child_clip(self, group_alias, child_alias, child_string, child_action, x, y):
        """Édite un clip qui appartient à un groupe"""
        from utils import get_group_children, update_group_child
        
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Récupérer les données complètes du clip enfant
        children = get_group_children(self.clip_notes_file_json, group_alias)
        child_data = None
        for c in children or []:
            if c.get('alias') == child_alias:
                child_data = c
                break
        
        if child_data is None:
            return
        
        # Récupérer le HTML si présent
        child_html = child_data.get('html', None)
        
        # Mapper l'action vers la valeur du slider
        action_to_slider = {"copy": 0, "term": 1, "exec": 2}
        slider_value = action_to_slider.get(child_action, 0)
        
        def handle_submit(dialog, name_input, value_input, slider):
            new_name = name_input.text().strip()
            new_value = value_input.toPlainText().strip().replace('\n', '\\n')
            
            # Capturer le HTML et vérifier s'il contient du formatting riche
            new_html = value_input.toHtml()
            new_html_to_save = new_html if has_rich_formatting(new_html) else None
            
            if new_name and new_value:
                new_slider_value = slider.value()
                action_map = {0: "copy", 1: "term", 2: "exec"}
                new_action = action_map.get(new_slider_value, "copy")
                
                # Si une nouvelle image a été sélectionnée, créer le thumbnail
                if self.dialog_temp_image_path:
                    thumbnail_path = create_thumbnail(self.dialog_temp_image_path, self.thumbnails_dir)
                    if thumbnail_path:
                        new_name = thumbnail_path
                    else:
                        return
                
                # Mettre à jour le clip dans le groupe
                update_group_child(
                    self.clip_notes_file_json,
                    group_alias,
                    child_alias,
                    new_alias=new_name,
                    new_string=new_value,
                    new_action=new_action,
                    new_html=new_html_to_save
                )
                
                dialog.accept()
                
                # Recharger les données et rester en mode update
                special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
                self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
                populate_actions_map_from_file(self.clip_notes_file_json, self.actions_map_sub, execute_command)
                self.update_clip(x, y, context="keep_mode")
        
        self.create_clip_dialog(
            title="🔧 Modifier le clip",
            button_text="Modifier",
            x=x, y=y,
            initial_name=child_alias,
            initial_value=child_string.replace('\\n', '\n'),
            initial_slider_value=slider_value,
            initial_html=child_html,
            on_submit_callback=handle_submit
        )
    
    def delete_group_child_clip(self, group_alias, child_alias, child_string, x, y):
        """Supprime un clip qui appartient à un groupe"""
        from utils import remove_clip_from_group
        
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("➖ Supprimer")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        dialog.setPalette(palette)
        
        dialog.setFixedSize(350, 180)
        dialog.move(x - dialog.width() // 2, y - dialog.height() // 2)
        
        content = QWidget()
        content.setStyleSheet(self.dialog_style)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        message_label = QLabel(f"Supprimer ce clip du groupe ?\n\n{child_alias}")
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
            # Retirer le clip du groupe (la fonction gère la dissolution si nécessaire)
            remove_clip_from_group(self.clip_notes_file_json, group_alias, child_alias, "delete_mode")
            
            # Supprimer le thumbnail s'il existe
            if "/" in child_alias and os.path.exists(child_alias):
                if "/usr" not in child_alias and "/share" not in child_alias:
                    try:
                        os.remove(child_alias)
                    except:
                        pass
            
            dialog.accept()
            
            # Recharger les données et rester en mode delete
            special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
            self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
            populate_actions_map_from_file(self.clip_notes_file_json, self.actions_map_sub, execute_command)
            self.delete_clip(x, y)
        
        delete_button.clicked.connect(confirm_delete)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(delete_button)
        layout.addLayout(buttons_layout)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        dialog.exec()
        
        if self.current_popup:
            self.current_popup.setMouseTracking(True)
    
    # def store_group_child_clip(self, group_alias, child_alias, child_string, child_action, x, y):
    #     """Stocke un clip qui appartient à un groupe"""
    #     from utils import remove_clip_from_group, get_group_children
        
    #     if self.tracker:
    #         self.tracker.update_pos()
    #         x, y = self.tracker.last_x, self.tracker.last_y
        
    #     # Récupérer les données complètes du clip enfant (incluant HTML)
    #     children = get_group_children(self.clip_notes_file_json, group_alias)
    #     child_html = None
    #     for c in children or []:
    #         if c.get('alias') == child_alias:
    #             child_html = c.get('html', None)
    #             break
        
    #     # Ajouter le clip au stockage
    #     self.add_stored_clip(child_alias, child_action, child_string, child_html)
        
    #     # Retirer le clip du groupe
    #     remove_clip_from_group(self.clip_notes_file_json, group_alias, child_alias , "storage_mode")
        
    #     # Recharger les données et rester en mode store
    #     special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
    #     self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
    #     populate_actions_map_from_file(self.clip_notes_file_json, self.actions_map_sub, execute_command)
        
    #     # Afficher un message
    #     if self.current_popup:
    #         self.current_popup.tooltip_window.show_message(f"✓ {child_alias} stocké", 1000)
        
        # self.store_clip_mode(x, y)
        
    def store_group_child_clip(self, group_alias, child_alias, child_string, child_action, x, y):
        """Stocke un clip qui appartient à un groupe"""
        # from utils import store_clip_from_group

        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y

        # Extraire ET retirer le clip du groupe (logique atomique)
        clip = store_clip_from_group(
            self.clip_notes_file_json,
            group_alias,
            child_alias
        )

        if not clip:
            return

        # Ajouter le clip au stockage (HTML inclus)
        self.add_stored_clip(
            clip.get('alias'),
            child_action,
            child_string,
            clip.get('html')
        )

        # Recharger les données et rester en mode store
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
        populate_actions_map_from_file(
            self.clip_notes_file_json,
            self.actions_map_sub,
            execute_command
        )
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
        self.store_clip_mode(x, y)
        # Afficher un message
        if self.current_popup:
            self.current_popup.tooltip_window.show_message(
                f"✓ {child_alias} stocké", 1000
            )

    def close_popup(self):
        """Méthode helper pour fermer le popup"""
        if self.tracker:
            self.tracker.close()
        if self.current_popup:
            self.current_popup.close()

    def create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
                           initial_slider_value=0, initial_html=None, placeholder="", on_submit_callback=None, on_close_callback=None):
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
        
        dialog.setFixedSize(500, 800)

        content = QWidget()
        content.setStyleSheet(self.dialog_style)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: none;
                border-radius: 16px;
                color: rgba(255, 255, 255, 150);
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 80, 80, 180);
                color: white;
            }
        """)
        close_btn.clicked.connect(dialog.reject)
        top_bar.addWidget(close_btn)
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
        image_button.setProperty("help_text", "Attribuer une image ( 🟩 : icône trouvée )")
        image_button.installEventFilter(self)
        
        # Checkbox pour auto-appliquer l'icône détectée
        auto_apply_checkbox = QCheckBox("Icône auto")
        auto_apply_checkbox.setChecked(self.auto_apply_icon)
        auto_apply_checkbox.setProperty("help_text", "Appliquer automatiquement l'icône détectée")
        auto_apply_checkbox.installEventFilter(self)
        auto_apply_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: rgba(100, 200, 100, 150);
                border: 1px solid rgba(100, 255, 100, 200);
                border-radius: 3px;
            }
        """)
        
        # Répartition : Emoji et Image prennent chacun 2 parts, Auto prend 1 part
        buttons_row.addWidget(emoji_button, 2)
        buttons_row.addWidget(image_button, 2)
        buttons_row.addWidget(auto_apply_checkbox, 1, Qt.AlignmentFlag.AlignCenter)

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
        self.dialog_emoji_labels = []
        self.dialog_slider = None  # Référence au slider pour les clics sur emojis
        
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
            self.dialog_emoji_labels.append(label)
            
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
        self.dialog_slider = slider  # Stocker pour les clics sur emojis
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
        if initial_html:
            # Si on a du HTML riche, l'utiliser pour conserver le formatting
            value_input.setHtml(initial_html)
        elif initial_value:
            value_input.setText(initial_value.replace(r'\n', '\n'))

        submit_button = QPushButton(button_text)
        submit_button.setFixedHeight(32)
        submit_button.setProperty("help_text", "Valider")
        submit_button.installEventFilter(self)
        
        # Label d'aide pour afficher les descriptions des icônes
        help_label = QLabel("")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setStyleSheet("color: white; font-size: 14px; padding: 4px; font-weight: bold;")
        help_label.setMinimumHeight(20)
        self.dialog_help_label = help_label  # Stocker pour l'event filter

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
        self.dialog_image_preview = image_preview
        
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
        self.dialog_remove_image_button = remove_image_button
        
        # Variable pour tracker si l'icône a été set automatiquement (doit être défini avant remove_image)
        auto_icon_applied = [False]  # Liste pour pouvoir modifier dans les closures
        last_auto_icon_path = [None]  # Tracker le dernier chemin d'icône appliqué
        manual_override = [False]  # True si l'utilisateur a choisi manuellement via FileDialog
        
        def remove_image():
            """Supprime l'aperçu de l'image et vide le champ nom"""
            self.dialog_temp_image_path = None
            auto_icon_applied[0] = False  # Réinitialiser le flag
            last_auto_icon_path[0] = None  # Réinitialiser le chemin
            manual_override[0] = False  # Réactiver la détection auto
            if self.dialog_image_preview:
                self.dialog_image_preview.setVisible(False)
                self.dialog_image_preview.clear()
            if self.dialog_remove_image_button:
                self.dialog_remove_image_button.setVisible(False)
            name_input.clear()
        
        remove_image_button.clicked.connect(remove_image)
        
        # Détecter les modifications manuelles du champ nom pour cacher l'image
        def on_name_changed(text):
            """Cache l'aperçu si l'utilisateur modifie le texte manuellement"""
            # Si on a une image temporaire et que le texte ne correspond plus au nom attendu
            if self.dialog_temp_image_path:
                expected_name = os.path.splitext(os.path.basename(self.dialog_temp_image_path))[0]
                if text != expected_name:
                    # L'utilisateur a modifié le texte, effacer l'aperçu
                    self.dialog_temp_image_path = None
                    if self.dialog_image_preview:
                        self.dialog_image_preview.setVisible(False)
                        self.dialog_image_preview.clear()
                    if self.dialog_remove_image_button:
                        self.dialog_remove_image_button.setVisible(False)
            # Si on édite une image existante et que le texte change
            elif initial_name_stored and "/" in initial_name_stored and text != initial_name_stored:
                # L'utilisateur a modifié le chemin, effacer l'aperçu
                if self.dialog_image_preview:
                    self.dialog_image_preview.setVisible(False)
                    self.dialog_image_preview.clear()
                if self.dialog_remove_image_button:
                    self.dialog_remove_image_button.setVisible(False)
        
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
        
        def apply_icon_to_dialog(icon_path):
            """Applique l'icône trouvée au dialogue (preview + chemin)"""
            self.dialog_temp_image_path = icon_path
            
            # Mettre le chemin de l'icône dans name_input
            name_input.setText(icon_path)
            
            # Afficher l'aperçu
            if self.dialog_image_preview:
                pixmap = QPixmap(icon_path)
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
                    
                    x = (100 - scaled_pixmap.width()) // 2
                    y = (100 - scaled_pixmap.height()) // 2
                    painter.drawPixmap(x, y, scaled_pixmap)
                    painter.end()
                    
                    self.dialog_image_preview.setPixmap(rounded)
                    self.dialog_image_preview.setVisible(True)
                    
                    if self.dialog_remove_image_button:
                        self.dialog_remove_image_button.setVisible(True)
                    
                    print(f"Icône d'application utilisée: {icon_path}")
        def find_app_icon(app_name):
            """Cherche l'icône d'une application installée"""
            if not app_name:
                return None
            
            # Nettoyer le nom de l'application (prendre le premier mot)
            app_name = app_name.strip().split()[0] if app_name.strip() else ""
            app_name = os.path.basename(app_name)
            
            if not app_name or len(app_name) < 2:
                return None
            
            # Commande qui priorise les grandes icônes (512 > 256 > 128 > etc.)
            cmd = f'''APP="{app_name}"; (
                find /usr/share/icons -path "*/512x512/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/icons -path "*/256x256/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/icons -path "*/128x128/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/icons -path "*/96x96/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/icons -path "*/64x64/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/icons -path "*/48x48/*" -iname "*$APP*.png" 2>/dev/null
                find /usr/share/pixmaps -iname "*$APP*.png" 2>/dev/null
                find /snap/$APP/current/meta/gui -iname "*.png" 2>/dev/null
                find /var/lib/flatpak ~/.local/share/flatpak -path "*$APP*/icons/*" -iname "*.png" 2>/dev/null
            )'''
            
            try:
                result = subprocess.run(
                    ['bash', '-c', cmd + ' | head -n1'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                icon_path = result.stdout.strip()
                
                # Si vide, pas d'icône trouvée
                if not icon_path:
                    return None
                
                return icon_path
            except Exception as e:
                print(f"Erreur lors de la recherche d'icône: {e}")
                return None
        
        # === Détection en temps réel d'icône d'application ===
        # Styles pour le bouton image
        image_button_style_normal = """
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
        image_button_style_highlight = """
            QPushButton {
                background-color: rgba(100, 200, 100, 50);
                border: 2px solid rgba(100, 255, 100, 200);
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(100, 255, 100, 100);
            }
        """
        image_button.setStyleSheet(image_button_style_normal)
        
        # Timer pour debounce (éviter trop de requêtes bash)
        icon_check_timer = QTimer()
        icon_check_timer.setSingleShot(True)
        
        def check_for_app_icon():
            """Vérifie si une icône existe et met à jour le bouton + miniature en temps réel"""
            # Si l'utilisateur a choisi manuellement, ne pas interférer
            if manual_override[0]:
                return
            
            command_text = value_input.toPlainText().strip()
            if command_text:
                icon_path = find_app_icon(command_text)
                if icon_path:
                    image_button.setStyleSheet(image_button_style_highlight)
                    # Si le toggle auto-apply est désactivé, ne pas appliquer l'icône
                    if not auto_apply_checkbox.isChecked():
                        return
                    # Set ou mettre à jour la miniature si l'icône a changé
                    if icon_path != last_auto_icon_path[0]:
                        apply_icon_to_dialog(icon_path)
                        auto_icon_applied[0] = True
                        last_auto_icon_path[0] = icon_path
                    return
            
            # Aucune icône trouvée - réinitialiser le style du bouton
            image_button.setStyleSheet(image_button_style_normal)
            
            # Si une icône avait été set automatiquement ET que le toggle est activé, la virer
            # (Si le toggle est off, on ne touche pas à la miniature)
            if auto_icon_applied[0] and auto_apply_checkbox.isChecked():
                auto_icon_applied[0] = False
                last_auto_icon_path[0] = None
                self.dialog_temp_image_path = None
                if self.dialog_image_preview:
                    self.dialog_image_preview.setVisible(False)
                    self.dialog_image_preview.clear()
                if self.dialog_remove_image_button:
                    self.dialog_remove_image_button.setVisible(False)
                name_input.clear()
        
        def on_value_text_changed():
            """Déclenche la vérification avec un délai (debounce)"""
            icon_check_timer.stop()
            icon_check_timer.start(200)  # 200ms de délai
        
        icon_check_timer.timeout.connect(check_for_app_icon)
        value_input.textChanged.connect(on_value_text_changed)
        
        # Connexion du toggle auto-apply (après définition de check_for_app_icon)
        def on_auto_apply_toggled(checked):
            self.auto_apply_icon = checked
            self.save_config()
            # Relancer la détection si on active
            if checked:
                check_for_app_icon()
        
        auto_apply_checkbox.toggled.connect(on_auto_apply_toggled)
        
        # Vérifier immédiatement si une icône existe pour la valeur initiale (mode modification)
        if initial_value:
            check_for_app_icon()
        
        def show_icon_proposal_dialog(icon_path):
            """
            Affiche un dialogue proposant d'utiliser l'icône trouvée.
            Retourne: "use" si accepté, "choose" si veut choisir autre, "cancel" si fermé
            """
            proposal_dialog = QDialog(dialog)
            proposal_dialog.setWindowTitle("🖼️ Icône détectée")
            proposal_dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
            proposal_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            proposal_dialog.setFixedSize(300, 280)
            
            # Variable pour tracker le choix
            user_choice = ["cancel"]  # Par défaut, cancel (croix ou Escape)
            
            # Palette sombre
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
            proposal_dialog.setPalette(palette)
            
            p_layout = QVBoxLayout(proposal_dialog)
            p_layout.setContentsMargins(20, 20, 20, 20)
            p_layout.setSpacing(15)
            
            # Message
            message = QLabel("Une icône a été trouvée\npour cette application :")
            message.setStyleSheet("color: white; font-size: 13px;")
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            p_layout.addWidget(message)
            
            # Aperçu de l'icône
            icon_preview = QLabel()
            icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_preview.setFixedSize(80, 80)
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(70, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_preview.setPixmap(scaled)
            p_layout.addWidget(icon_preview, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # Boutons
            btn_layout = QHBoxLayout()
            
            def on_choose():
                user_choice[0] = "choose"
                proposal_dialog.reject()
            
            def on_use():
                user_choice[0] = "use"
                proposal_dialog.accept()
            
            no_btn = QPushButton("Non, choisir")
            no_btn.setFixedHeight(35)
            no_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(100, 100, 100, 100);
                    border: 1px solid rgba(150, 150, 150, 150);
                    border-radius: 6px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(150, 150, 150, 150);
                }
            """)
            no_btn.clicked.connect(on_choose)
            
            yes_btn = QPushButton("✓ Utiliser")
            yes_btn.setFixedHeight(35)
            yes_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(100, 200, 100, 100);
                    border: 1px solid rgba(100, 255, 100, 150);
                    border-radius: 6px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(100, 255, 100, 150);
                }
            """)
            yes_btn.clicked.connect(on_use)
            
            btn_layout.addWidget(no_btn)
            btn_layout.addWidget(yes_btn)
            p_layout.addLayout(btn_layout)
            
            proposal_dialog.exec()
            return user_choice[0]
        

        
        def open_image_selector():
            """Ouvre un sélecteur de fichier pour choisir une image"""
            
            # Si aucune miniature n'est déjà visible, proposer l'icône détectée
            if not (self.dialog_image_preview and self.dialog_image_preview.isVisible()):
                # Vérifier si value_input contient une commande d'application
                command_text = value_input.toPlainText().strip()
                icon_path = find_app_icon(command_text) if command_text else None
                
                # Si une icône valide est trouvée, proposer à l'utilisateur
                if icon_path:
                    choice = show_icon_proposal_dialog(icon_path)
                    if choice == "use":
                        apply_icon_to_dialog(icon_path)
                        auto_icon_applied[0] = True
                        last_auto_icon_path[0] = icon_path
                        return
                    elif choice == "cancel":
                        # Croix ou Escape : ne rien faire
                        return
                    # choice == "choose" : continuer vers le sélecteur de fichiers
            
            # Comportement normal : ouvrir le sélecteur de fichiers
            start_dir = get_pictures_directory()
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                "Choisir une image",
                start_dir,
                "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;Tous les fichiers (*)"
            )
            
            if file_path:
                # L'utilisateur a choisi manuellement, désactiver la détection auto
                auto_icon_applied[0] = False
                last_auto_icon_path[0] = None
                manual_override[0] = True  # Protéger le choix manuel
                
                # Stocker le chemin temporairement (ne pas créer le thumbnail maintenant)
                self.dialog_temp_image_path = file_path
                
                # Mettre seulement le nom de fichier (sans chemin) dans name_input
                file_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(file_name)[0]
                name_input.setText(name_without_ext)
                
                # Afficher l'aperçu de l'image
                if self.dialog_image_preview:
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
                        
                        self.dialog_image_preview.setPixmap(rounded)
                        self.dialog_image_preview.setVisible(True)
                        
                        # Rendre visible le bouton de suppression
                        if self.dialog_remove_image_button:
                            self.dialog_remove_image_button.setVisible(True)
                        
                        print(f"Image sélectionnée: {file_path}")
                    else:
                        print("Erreur lors du chargement de l'image")

        def open_emoji_selector():
            path = self.emojis_file
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
        result = dialog.exec()
        
        # Si le dialogue a été fermé/annulé (pas accepté) et qu'un callback de fermeture est défini
        if result == QDialog.DialogCode.Rejected and on_close_callback:
            on_close_callback()
        
        # CRITIQUE: Nettoyer les variables du dialogue
        self.dialog_temp_image_path = None
        self.dialog_image_preview = None
        self.dialog_remove_image_button = None
        
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
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        # Filtrer les clips (sans les boutons d'action)
        clips_only = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON pour le tri personnalisé
        json_order = get_json_order(self.clip_notes_file_json)
        
        # Trier les clips en respectant l'ordre du JSON
        sorted_clips = sort_actions_map(clips_only, json_order)
        
        self.buttons_sub = []
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            # Récupérer le HTML pour le tooltip
            _, clip_html = self.get_clip_data_from_json(name)
            self.buttons_sub.append(
                (
                    name, 
                    self.make_handler_store(name, value, action, x, y),
                    tooltip,
                    action,
                    clip_html  # 5ème élément : HTML pour le tooltip
                )
            )
        clips_by_link = []
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text("💾")
            self.current_popup.update_clips_by_link(clips_by_link)
            self.current_popup.set_neon_color("vert")
            self.current_popup.toggle_neon(True)
            self.current_popup.timer.start(50)
    
    def make_handler_store(self, name, value, action, x, y):
        """Crée un handler pour stocker un clip ou un groupe"""
        def handler():
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            
            from utils import is_group, get_group_children, delete_group_from_json
            
            # Vérifier si c'est un groupe
            if is_group(self.clip_notes_file_json, name):
                # Stocker tous les clips du groupe
                children = get_group_children(self.clip_notes_file_json, name)
                if children:
                    for child in children:
                        child_alias = child.get('alias', '')
                        child_action = child.get('action', 'copy')
                        child_string = child.get('string', '')
                        child_html = child.get('html')
                        self.add_stored_clip(child_alias, child_action, child_string, child_html)
                
                # Supprimer le groupe
                delete_group_from_json(self.clip_notes_file_json, name)
                self.actions_map_sub.pop(name, None)
                
                # Afficher une confirmation
                if self.current_popup:
                    self.current_popup.set_central_text("✓")
                    QTimer.singleShot(500, lambda: self.current_popup.set_central_text("💾"))
            else:
                # Récupérer le HTML depuis le fichier JSON avant de stocker
                _, html_string = self.get_clip_data_from_json(name)
                
                # Stocker le clip avec le HTML s'il existe
                self.add_stored_clip(name, action if action else "copy", value, html_string)
                
                # Supprimer le clip du menu radial
                self.actions_map_sub.pop(name, None)
                delete_from_json(self.clip_notes_file_json, name)
                
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
        # Menu à 4 icones
        if self.nb_icons_menu == 5:
            self.buttons_sub = [
                ("📋", lambda: self.show_stored_clips_dialog(x, y), "Clips stockés", None),
                ("🗑️", lambda: self.delete_clip(x, y), "Supprimer", None),
                ("💾", lambda: self.store_clip_mode(x, y), "Stocker", None)
            ]
            central_icon = "➖"
        elif self.nb_icons_menu == 6:
            self.buttons_sub = [
                ("📋", lambda: self.show_stored_clips_dialog(x, y), "Clips stockés", None),
                ("🗑️", lambda: self.delete_clip(x, y), "Supprimer", None),
                ("💾", lambda: self.store_clip_mode(x, y), "Stocker", None)
            ]
            central_icon = "➖"
        elif self.nb_icons_menu == 7:
            self.buttons_sub = []
            central_icon = ""
        # Remplacer temporairement les boutons par les 2 options
        
        if self.current_popup:
            self.current_popup.update_buttons(self.buttons_sub)
            self.current_popup.set_central_text(central_icon)
    
    def show_stored_clips_dialog(self, x, y):
        """Affiche la fenêtre de dialogue avec la liste des clips stockés"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Charger les clips stockés
        stored_clips = self.load_stored_clips()
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("📋 Clips stockés")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setStyleSheet("""
                background-color: rgba(35, 35, 35, 255);
                border-radius: 6px;
        """)
        # Appliquer une palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(100, 100, 100))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        dialog.setPalette(palette)
        
        dialog.resize(750, 500)
        dialog.setMinimumSize(850, 650)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Zone de défilement pour la liste
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # scroll_content.setStyleSheet("background-color: rgb(100, 100, 100);")
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
            alias_header.setStyleSheet("font-weight: bold; color: white;")
            alias_header.setFixedWidth(50)
            
            action_header = QLabel("Action")
            action_header.setStyleSheet("font-weight: bold; color: white;")
            action_header.setFixedWidth(80)
            
            value_header = QLabel("Valeur")
            value_header.setStyleSheet("font-weight: bold; color: white;")
            
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
                    alias_label.setText(alias)
                    alias_label.setStyleSheet("color: white;")
                    alias_label.setWordWrap(True)
                    alias_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                              
                # Action "✂️", "💻", "🚀"
                actions_readable = {
                    "copy" : "copier",
                    "term" : "exécuter terminal",
                    "exec" : "exécuter",
                }

                actions_readable_tooltip = {
                    "copy" : "copie la valeur dans le presse-papier",
                    "term" : "exécute la valeur dans un terminal",
                    "exec" : "exécute la valeur hors terminal",
                }
                
                action_label = QLabel(actions_readable[clip_data.get('action', 'copy')])
                action_label.setFixedWidth(80)
                action_label.setProperty("help_text", actions_readable_tooltip[clip_data.get('action', 'copy')])
                action_label.installEventFilter(self)
                action_label.setStyleSheet("color: lightblue;")
                action_label.setWordWrap(True)
                
                # String (tronquée si trop longue)
                string = clip_data.get('string', '')
                html_string = clip_data.get('html_string', None)  # Récupérer le HTML s'il existe
                string_display = string[:50] + "..." if len(string) > 50 else string
                string_label = QLabel(string_display)
                # string_display_helper = string[:150] + "..." if len(string) > 150 else string
                help_text = string.replace(r"\n", "\n")
                string_label.setProperty("help_text", help_text)
                string_label.setProperty("html_string", html_string)  # Stocker le HTML pour le preview
                string_label.installEventFilter(self)
                string_label.setStyleSheet("color: white;")
                string_label.setWordWrap(True)
                
                # Convertir l'action en slider_value
                action = clip_data.get('action', 'copy')
                action_to_slider = {'copy': 0, 'term': 1, 'exec': 2}
                slider_value = action_to_slider.get(action, 0)
                
                # Bouton restaurer
                restore_btn = QPushButton("↩️")
                restore_btn.setFixedSize(30, 30)
                restore_btn.setProperty("help_text", "Restaurer")
                restore_btn.installEventFilter(self)
                restore_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(100, 200, 100, 100);
                        border: 1px solid rgba(100, 255, 100, 150);
                        border-radius: 10px;
                    }
                    QPushButton:hover {
                        background-color: rgba(100, 255, 100, 150);
                    }
                """)
                restore_btn.clicked.connect(lambda checked, a=alias, cd=clip_data: self.restore_clip_to_menu(a, cd, dialog, x, y))
                
                # Bouton Editer
                edit_btn = QPushButton("🔧")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setProperty("help_text", "Modifier")
                edit_btn.installEventFilter(self)
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 150, 100);
                        border: 1px solid rgba(255, 255, 150, 150);
                        border-radius: 10px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 150, 150);
                    }
                """)
                edit_btn.clicked.connect(lambda checked, a=alias, s=string, sv=slider_value, d=dialog, hs=html_string: self.edit_clip_from_storage(a, s, x, y, sv, d, hs))
                
                # Bouton supprimer
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setProperty("help_text", "Supprimer")
                delete_btn.installEventFilter(self)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 150, 100);
                        border: 1px solid rgba(255, 100, 100, 150);
                        border-radius: 10px;
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
                clip_layout.addWidget(edit_btn)
                clip_layout.addWidget(delete_btn)
                
                scroll_layout.addLayout(clip_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Conteneur pour le preview adaptatif (label pour 1 ligne, QTextBrowser pour multilignes)
        preview_container = QWidget()
        preview_container.setMinimumHeight(30)
        preview_container.setMaximumHeight(200)
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setContentsMargins(0, 0, 0, 0)
        preview_container_layout.setSpacing(0)
        
        # Label simple pour les textes courts (1 ligne)
        help_label = QLabel("")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_label.setStyleSheet("color: white; font-size: 14px; padding: 4px; font-weight: bold;")
        help_label.setMinimumHeight(30)
        preview_container_layout.addWidget(help_label)
        
        # QTextBrowser pour les textes multilignes avec HTML/linting
        help_browser = QTextBrowser()
        help_browser.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 6px;
                color: white;
                font-size: 12px;
                padding: 8px;
            }
        """)
        help_browser.setMinimumHeight(60)
        help_browser.setMaximumHeight(180)
        help_browser.setOpenExternalLinks(False)
        help_browser.setVisible(False)  # Caché par défaut
        preview_container_layout.addWidget(help_browser)
        
        layout.addWidget(preview_container)
        
        # Stocker les références pour l'event filter
        self.dialog_help_label = help_label
        self.dialog_help_browser = help_browser
        
        # Bouton Fermer
        close_button = QPushButton("Fermer")
        close_button.setFixedHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 100);
                color: white;
                border: 1px solid rgba(150, 150, 150, 150);
                border-radius: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(150, 150, 150, 150);
            }
        """)
        close_button.clicked.connect(dialog.accept)
        # close_button.setProperty("help_text", "Fermer")
        # close_button.installEventFilter(self)
        layout.addWidget(close_button)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addLayout(layout)
        
        # Réactiver le menu après fermeture du dialogue
        def reactivate_menu():
            if self.current_popup:
                self.current_popup.setMouseTracking(True)
                self.current_popup.activateWindow()
                self.current_popup.raise_()
                self.current_popup.update()
        
        dialog.finished.connect(reactivate_menu)
        
        dialog.exec()
    
    def delete_stored_clip_and_refresh(self, alias, dialog, x, y):
        """Affiche une confirmation avant de supprimer un clip stocké"""
        # Référence au dialogue principal pour mise à jour ultérieure
        main_dialog = dialog
        
        # Afficher la confirmation
        confirm_dialog = QDialog(self.tracker)
        confirm_dialog.setWindowTitle("🗑️ Supprimer")
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
        
        confirm_dialog.setFixedSize(350, 220)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Message
        display_name = alias if "/" not in alias else os.path.basename(alias)
        message = QLabel(f"Supprimer définitivement\n'{display_name}'\ndu stockage ?")
        message.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        cancel_button = QPushButton("Annuler")
        cancel_button.setFixedHeight(40)
        cancel_button.clicked.connect(confirm_dialog.reject)
        
        delete_button = QPushButton("🗑️ Supprimer")
        delete_button.setFixedHeight(40)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 70, 70, 150);
                border: 1px solid rgba(255, 100, 100, 200);
                border-radius: 15px;
                padding: 8px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 200);
            }
        """)
        
        def confirm_delete():
            # Supprimer le thumbnail s'il existe
            if os.path.exists(alias):
                if "/usr" not in alias and "/share" not in alias:
                    os.remove(alias)
            
            self.remove_stored_clip(alias)
            confirm_dialog.accept()
            
            # Afficher un message de confirmation
            if self.current_popup:
                self.current_popup.tooltip_window.show_message(f"✓ {display_name} supprimé", 1500)
                self.current_popup.update_tooltip_position()
            
            # Mettre à jour la liste dans le dialogue principal
            scroll = main_dialog.findChild(QScrollArea)
            if scroll:
                scroll_content = scroll.widget()
                if scroll_content:
                    scroll_layout = scroll_content.layout()
                    if scroll_layout:
                        # Parcourir les items pour trouver celui avec cet alias
                        for i in range(scroll_layout.count()):
                            item = scroll_layout.itemAt(i)
                            if item and item.layout():
                                item_layout = item.layout()
                                # Le premier widget est le QLabel avec l'alias
                                if item_layout.count() > 0:
                                    first_widget = item_layout.itemAt(0).widget()
                                    if isinstance(first_widget, QLabel) and first_widget.text() == alias:
                                        # Supprimer tous les widgets de ce layout
                                        while item_layout.count():
                                            child = item_layout.takeAt(0)
                                            if child.widget():
                                                child.widget().deleteLater()
                                        # Supprimer le layout lui-même
                                        scroll_layout.removeItem(item)
                                        break
            
            # Vérifier s'il reste des clips stockés
            stored_clips = self.load_stored_clips()
            if not stored_clips:
                # Plus de clips stockés, fermer le dialogue principal
                main_dialog.accept()
        
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
        html_string = clip_data.get('html_string', None)  # Récupérer le HTML s'il existe
        
        # Ajouter au menu radial (dans le fichier JSON) avec le HTML
        append_to_actions_file_json(self.clip_notes_file_json, alias, string, action, html_string)
        
        # Ajouter directement dans actions_map_sub pour mise à jour immédiate
        if action == "copy":
            self.actions_map_sub[alias] = [(paperclip_copy, [string], {}), string, action]
        elif action == "term":
            self.actions_map_sub[alias] = [(execute_terminal, [string], {}), string, action]
        elif action == "exec":
            self.actions_map_sub[alias] = [(execute_command, [string], {}), string, action]
        
        # Supprimer du stockage
        self.remove_stored_clip(alias)
        
        # Mettre à jour le menu radial
        self.refresh_menu()
        
        # Afficher un message de confirmation dans le tooltip
        display_name = alias if "/" not in alias else os.path.basename(alias)
        if self.current_popup:
            self.current_popup.tooltip_window.show_message(f"✓ {display_name} restauré", 1500)
            self.current_popup.update_tooltip_position()
        
        # Mettre à jour la liste dans le dialogue (retirer l'item restauré)
        # Chercher et supprimer le layout correspondant dans le scroll_content
        scroll = dialog.findChild(QScrollArea)
        if scroll:
            scroll_content = scroll.widget()
            if scroll_content:
                layout = scroll_content.layout()
                if layout:
                    # Parcourir les items pour trouver celui avec cet alias
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.layout():
                            item_layout = item.layout()
                            # Le premier widget est le QLabel avec l'alias
                            if item_layout.count() > 0:
                                first_widget = item_layout.itemAt(0).widget()
                                if isinstance(first_widget, QLabel) and first_widget.text() == alias:
                                    # Supprimer tous les widgets de ce layout
                                    while item_layout.count():
                                        child = item_layout.takeAt(0)
                                        if child.widget():
                                            child.widget().deleteLater()
                                    # Supprimer le layout lui-même
                                    layout.removeItem(item)
                                    break
        
        # Vérifier s'il reste des clips stockés
        stored_clips = self.load_stored_clips()
        if not stored_clips:
            # Plus de clips stockés, fermer le dialogue
            dialog.accept()
    
    def show_reorder_dialog(self, x, y):
        """Affiche la fenêtre de réordonnancement des clips par drag and drop"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("↔️ Ordonner")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Palette sombre
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        dialog.setPalette(palette)
        dialog.setStyleSheet("background-color: rgba(40, 40, 40, 150);")
        dialog.setFixedSize(500, 760)
        dialog.move(x - 250, y - 300)
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Titre
        title_label = QLabel("Glissez-déposez pour ordonner")
        title_label.setStyleSheet("color: white; font-size: 14px; font-style: italic;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Charger les clips depuis le JSON
        try:
            with open(self.clip_notes_file_json, 'r', encoding='utf-8') as f:
                all_clips = json.load(f)
        except Exception:
            all_clips = []
        
        # Séparer les clips par action
        clips_by_action = {"copy": [], "term": [], "exec": []}
        for clip in all_clips:
            action = clip.get('action', 'copy')
            if action in clips_by_action:
                clips_by_action[action].append(clip)
        
        # Scroll area pour contenir les 3 groupes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: rgba(60, 60, 60, 100);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 100, 100, 150);
                border-radius: 5px;
                min-height: 20px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # Dictionnaire pour stocker les QListWidgets
        list_widgets = {}
        
        # Infos sur les actions
        action_info = {
            "copy": ("✂️ Copier", "rgba(98, 160, 234, 80)", self.action_zone_colors.get("copy", (98, 160, 234))),
            "term": ("💻 Terminal", "rgba(248, 228, 92, 80)", self.action_zone_colors.get("term", (248, 228, 92))),
            "exec": ("🚀 Exécuter", "rgba(224, 27, 36, 80)", self.action_zone_colors.get("exec", (224, 27, 36)))
        }
        
        def create_list_widget(action, clips):
            """Crée un QListWidget avec drag and drop pour une action"""
            
            group_widget = QWidget()
            group_layout = QVBoxLayout(group_widget)
            group_layout.setContentsMargins(5, 5, 5, 5)
            group_layout.setSpacing(5)

            # Header du groupe
            title, bg_color, rgb_color = action_info[action]
            header = QLabel(f"{title} ({len(clips)})")
            r, g, b = rgb_color if isinstance(rgb_color, tuple) else (100, 100, 100)
            header.setStyleSheet(f"""
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 5px;
                background-color: rgba({r}, {g}, {b}, 100);
                border-radius: 5px;
            """)
            group_layout.addWidget(header)
            
            if not clips:
                empty_label = QLabel("Aucun clip")
                empty_label.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                group_layout.addWidget(empty_label)
                return group_widget, None
            
            # Liste avec drag and drop et auto-scroll
            list_widget = AutoScrollListWidget()
            list_widget.setStyle(WhiteDropIndicatorStyle())
            list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            list_widget.setIconSize(QSize(32, 32))  # Taille des icônes pour les images
            list_widget.setStyleSheet(f"""
                QListWidget {{
                    background-color: rgba(40, 40, 40, 150);
                    border: 1px solid rgba({r}, {g}, {b}, 100);
                    border-radius: 8px;
                    padding: 5px;
                }}
                QListWidget::item {{
                    background-color: rgba(60, 60, 60, 150);
                    border: 1px solid rgba(80, 80, 80, 100);
                    border-radius: 5px;
                    padding: 8px;
                    margin: 2px;
                    color: white;
                }}
                QListWidget::item:selected {{
                    background-color: rgba({r}, {g}, {b}, 150);
                    border: 1px solid rgba({r}, {g}, {b}, 200);
                }}
                QListWidget::item:hover {{
                    background-color: rgba(80, 80, 80, 150);
                }}
            """)
            
            # Ajouter les clips
            for clip in clips:
                alias = clip.get('alias', '')
                string = clip.get('string', '')
                
                # Ajouter un aperçu de la valeur
                value_preview = string[:40].replace('\n', ' ').replace(r'\n', ' ')
                if len(string) > 40:
                    value_preview += "..."
                
                # Créer l'item
                if "/" in alias and os.path.exists(alias):
                    # C'est un chemin d'image - afficher l'image comme icône
                    item = QListWidgetItem(f"  →  {value_preview}")
                    item.setIcon(QIcon(image_pixmap(alias, 32)))
                elif is_emoji(alias):
                    display_name = alias
                    item = QListWidgetItem(f"{display_name}  →  {value_preview}")
                else:
                    display_name = alias[:30] + "..." if len(alias) > 30 else alias
                    item = QListWidgetItem(f"{display_name}  →  {value_preview}")
                
                item.setData(Qt.ItemDataRole.UserRole, alias)  # Stocker l'alias complet
                list_widget.addItem(item)
            
            # Connecter le signal de changement d'ordre avec capture correcte des variables
            def make_order_handler(act, lw):
                def handler():
                    save_new_order(act, lw)
                return handler
            
            list_widget.model().rowsMoved.connect(make_order_handler(action, list_widget))
            
            list_widgets[action] = list_widget
            group_layout.addWidget(list_widget)
            
            return group_widget, list_widget
        
        def save_new_order(action, list_widget):
            """Sauvegarde le nouvel ordre dans le JSON"""
            new_order = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                alias = item.data(Qt.ItemDataRole.UserRole)
                new_order.append(alias)
            
            # Sauvegarder dans le JSON
            reorder_json_clips(self.clip_notes_file_json, action, new_order)
            
            # Rafraîchir le menu radial
            self.refresh_menu()
        
        # Créer les 3 groupes
        for action in ["copy", "term", "exec"]:
            group_widget, _ = create_list_widget(action, clips_by_action[action])
            scroll_layout.addWidget(group_widget)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Bouton Fermer
        close_btn = QPushButton("Fermer")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 150);
                border: 1px solid rgba(150, 150, 150, 200);
                border-radius: 15px;
                padding: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 200);
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        main_layout.addWidget(close_btn)
        
        dialog.exec()
    
    def show_config_dialog(self, x, y):
        """Affiche le dialogue de configuration avec aperçu en temps réel"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # === SAUVEGARDER L'ÉTAT INITIAL pour restauration si Annuler ===
        initial_state = {
            'menu_background_color': self.menu_background_color,
            'action_zone_colors': dict(self.action_zone_colors),
            'zone_basic_opacity': self.zone_basic_opacity,
            'zone_hover_opacity': self.zone_hover_opacity,
            'menu_opacity': self.menu_opacity,
            'nb_icons_menu': self.nb_icons_menu,
            'show_central_icon': self.show_central_icon,
            'central_neon': self.central_neon,
            'neon_color': self.neon_color,
            'neon_speed': self.neon_speed,
            'shadow_enabled': self.shadow_enabled,
            'shadow_offset': self.shadow_offset,
            'shadow_angle': self.shadow_angle,
            'shadow_color': self.shadow_color,
        }
        
        def apply_live():
            """Applique les changements en temps réel sur le menu"""
            if self.current_popup:
                self.current_popup.menu_background_color = self.menu_background_color
                self.current_popup.action_zone_colors = self.action_zone_colors
                self.current_popup.zone_basic_opacity = self.zone_basic_opacity
                self.current_popup.zone_hover_opacity = self.zone_hover_opacity
                self.current_popup.update_badge_colors()  # Mettre à jour les couleurs des badges
                self.current_popup.set_widget_opacity(self.menu_opacity / 100.0)
                self.current_popup.nb_icons_menu = self.nb_icons_menu
                self.current_popup.show_central_icon = self.show_central_icon
                self.current_popup.neon_color = self.neon_color
                self.current_popup.toggle_neon(self.central_neon)
                if self.central_neon:
                    self.current_popup.timer.stop()
                    self.current_popup.timer.start(self.neon_speed)
                self.current_popup.shadow_enabled = self.shadow_enabled
                self.current_popup.shadow_offset = self.shadow_offset
                self.current_popup.shadow_angle = self.shadow_angle
                self.current_popup.shadow_color = self.shadow_color
                self.current_popup.update()
        
        def restore_initial():
            """Restaure l'état initial"""
            self.menu_background_color = initial_state['menu_background_color']
            self.action_zone_colors = dict(initial_state['action_zone_colors'])
            self.zone_basic_opacity = initial_state['zone_basic_opacity']
            self.zone_hover_opacity = initial_state['zone_hover_opacity']
            self.menu_opacity = initial_state['menu_opacity']
            self.nb_icons_menu = initial_state['nb_icons_menu']
            self.show_central_icon = initial_state['show_central_icon']
            self.central_neon = initial_state['central_neon']
            self.neon_color = initial_state['neon_color']
            self.neon_speed = initial_state['neon_speed']
            self.shadow_enabled = initial_state['shadow_enabled']
            self.shadow_offset = initial_state['shadow_offset']
            self.shadow_angle = initial_state['shadow_angle']
            self.shadow_color = initial_state['shadow_color']
            apply_live()
        
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("⚙️ Configurer")
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
        
        dialog.setFixedSize(400, 980)
        
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x, y)
        
        content = QWidget()
        content.setStyleSheet(self.dialog_style)
        
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Couleurs des zones ---
        colors_label = QLabel("🎨 Couleurs")
        colors_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(colors_label)
               
        # Couleur du fond du menu
        menu_bg_color_layout = QHBoxLayout()
        menu_bg_color_label = QLabel("🔘 Général")
        # menu_bg_color_label.setStyleSheet("margin-top: 10px;")
        menu_bg_color_label.setFixedWidth(140)
        
        menu_bg_color_button = QPushButton()
        menu_bg_color_button.setFixedHeight(30)
        menu_bg_color_button.setFixedWidth(150)
        
        # Variable pour stocker la couleur du fond du menu
        selected_menu_bg_color = list(self.menu_background_color)
        
        def update_menu_bg_button():
            r, g, b = selected_menu_bg_color
            menu_bg_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
            """)
            # menu_bg_color_button.setText(f"RGB({r}, {g}, {b})")
        
        def pick_menu_bg_color():
            r, g, b = selected_menu_bg_color
            initial_color = QColor(r, g, b)
            color = QColorDialog.getColor(initial_color, dialog, "Couleur de fond du menu")
            if color.isValid():
                selected_menu_bg_color[0] = color.red()
                selected_menu_bg_color[1] = color.green()
                selected_menu_bg_color[2] = color.blue()
                update_menu_bg_button()
                # Appliquer en live
                self.menu_background_color = tuple(selected_menu_bg_color)
                apply_live()
        
        menu_bg_color_button.clicked.connect(pick_menu_bg_color)
        update_menu_bg_button()
        
        menu_bg_color_layout.addWidget(menu_bg_color_label)
        menu_bg_color_layout.addWidget(menu_bg_color_button)
        menu_bg_color_layout.setContentsMargins(20, 0, 0, 0)
        menu_bg_color_layout.addStretch()
        layout.addLayout(menu_bg_color_layout)

        colors_zones_label = QLabel("zones par actions")
        colors_zones_label.setStyleSheet("font-style: italic; color: white; margin-left: 35px;")
        layout.addWidget(colors_zones_label)

        # Variables pour stocker les couleurs sélectionnées
        selected_colors = {
            "copy": self.action_zone_colors["copy"],
            "term": self.action_zone_colors["term"],
            "exec": self.action_zone_colors["exec"]
        }
        
        def create_color_button(action_name, label_text, rgb):
            """Crée un bouton coloré qui ouvre un color picker"""
            layout_h = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(140)
            
            button = QPushButton()
            button.setFixedHeight(30)
            button.setFixedWidth(150)
            
            def update_button_color():
                r, g, b = selected_colors[action_name]
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({r}, {g}, {b});
                        border: 2px solid rgba(255, 255, 255, 100);
                        border-radius: 10px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid rgba(255, 255, 255, 200);
                    }}
                """)
            
            def pick_color():
                r, g, b = selected_colors[action_name]
                initial_color = QColor(r, g, b)
                color = QColorDialog.getColor(initial_color, dialog, f"Couleur pour {label_text}")
                if color.isValid():
                    selected_colors[action_name] = (color.red(), color.green(), color.blue())
                    update_button_color()
                    # Appliquer en live
                    self.action_zone_colors[action_name] = selected_colors[action_name]
                    apply_live()
            
            button.clicked.connect(pick_color)
            update_button_color()
            
            layout_h.addWidget(label)
            layout_h.addWidget(button)
            layout_h.setContentsMargins(20, 0, 0, 0)
            layout_h.addStretch()
            return layout_h
        
        # Boutons pour chaque action
        copy_layout = create_color_button("copy", "✂️ Copie", self.action_zone_colors["copy"])
        layout.addLayout(copy_layout)
        
        term_layout = create_color_button("term", "💻 Terminal", self.action_zone_colors["term"])
        layout.addLayout(term_layout)
        
        exec_layout = create_color_button("exec", "🚀 Exécution", self.action_zone_colors["exec"])
        layout.addLayout(exec_layout)

        # --- Opacités ---
        opacity_label = QLabel("🔆 Opacités")
        opacity_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(opacity_label)
        
        # Slider pour opacité du menu
        menu_opacity_layout = QVBoxLayout()
        menu_opacity_label = QLabel(f"Opacité générale ➤ <b>{self.menu_opacity}</b>")
        menu_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        menu_opacity_slider.setMinimum(0)
        menu_opacity_slider.setMaximum(100)
        menu_opacity_slider.setValue(self.menu_opacity)
        
        def on_menu_opacity_changed(v):
            menu_opacity_label.setText(f"Opacité générale ➤ <b>{v}</b>")
            self.menu_opacity = v
            apply_live()
        
        menu_opacity_slider.valueChanged.connect(on_menu_opacity_changed)
        menu_opacity_layout.addWidget(menu_opacity_label)
        menu_opacity_layout.addWidget(menu_opacity_slider)
        menu_opacity_layout.setContentsMargins(20, 0, 20, 0)
        layout.addLayout(menu_opacity_layout)
               
        # Slider pour opacité de base
        basic_opacity_layout = QVBoxLayout()
        basic_opacity_label = QLabel(f"Opacité des zones ➤ <b>{self.zone_basic_opacity}</b>")
        basic_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        basic_opacity_slider.setMinimum(0)
        basic_opacity_slider.setMaximum(100)
        basic_opacity_slider.setValue(self.zone_basic_opacity)
        
        def on_basic_opacity_changed(v):
            basic_opacity_label.setText(f"Opacité des zones ➤ <b>{v}</b>")
            self.zone_basic_opacity = v
            apply_live()
        
        basic_opacity_slider.valueChanged.connect(on_basic_opacity_changed)
        basic_opacity_layout.addWidget(basic_opacity_label)
        basic_opacity_layout.addWidget(basic_opacity_slider)
        basic_opacity_layout.setContentsMargins(20, 0, 20, 0)
        layout.addLayout(basic_opacity_layout)
        
        # Slider pour opacité au survol
        hover_opacity_layout = QVBoxLayout()
        hover_opacity_label = QLabel(f"Opacité des zones au survol ➤ <b>{self.zone_hover_opacity}</b>")
        hover_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        hover_opacity_slider.setMinimum(0)
        hover_opacity_slider.setMaximum(100)
        hover_opacity_slider.setValue(self.zone_hover_opacity)
        
        def on_hover_opacity_changed(v):
            hover_opacity_label.setText(f"Opacité des zones au survol ➤ <b>{v}</b>")
            self.zone_hover_opacity = v
            apply_live()
        
        hover_opacity_slider.valueChanged.connect(on_hover_opacity_changed)
        hover_opacity_layout.addWidget(hover_opacity_label)
        hover_opacity_layout.addWidget(hover_opacity_slider)
        hover_opacity_layout.setContentsMargins(20, 0, 20, 0)
        layout.addLayout(hover_opacity_layout)
        
        # --- Options ---
        options_label = QLabel("⚡ Options")
        options_label.setStyleSheet("font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(options_label)

        # Slider pour le nombre d'icones "fixes" du menu
        slider_container = QWidget()
        slider_label = QLabel("Nombre d'icones du menu")
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setContentsMargins(20, 0, 20, 0)
        slider_layout.setSpacing(2)

        emoji_labels_layout = QHBoxLayout()
        emoji_labels_layout.setContentsMargins(8, 0, 8, 0)
        emoji_labels_layout.setSpacing(0)
        
        min_buttons_number = 5
        max_buttons_number = 7

        emoji_labels = [str(i) for i in range(min_buttons_number, max_buttons_number + 1)]
        emoji_tooltips = [str(i) for i in range(min_buttons_number, max_buttons_number + 1)]
        
        # Stocker les labels pour l'event filter
        self.nb_icons_config_labels = []
        self.nb_icons_dialog_slider = None  # Référence au slider pour les clics sur emojis
        
        for i, emoji in enumerate(emoji_labels):
            if i > 0:
                emoji_labels_layout.addStretch()
            label = QLabel(emoji)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 20px;")
            label.setCursor(Qt.CursorShape.PointingHandCursor)  # Curseur pointeur
            
            # Stocker le tooltip et la valeur du slider pour ce label
            label.setProperty("tooltip_text", emoji_tooltips[i])
            # La valeur du slider est 4 ou 5, pas l'index 0 ou 1
            label.setProperty("slider_value", int(emoji))  # Utiliser la valeur réelle (4 ou 5)
            
            # Installer l'event filter pour détecter le hover et les clics
            label.installEventFilter(self)
            label.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
            self.nb_icons_config_labels.append(label)
            
            emoji_labels_layout.addWidget(label)
            if i < len(emoji_labels) - 1:
                emoji_labels_layout.addStretch()
        
        slider_layout.addWidget(slider_label)
        slider_layout.addLayout(emoji_labels_layout)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_buttons_number)
        slider.setMaximum(max_buttons_number)
        slider.setValue(self.nb_icons_menu)  # INITIALISER avec la bonne valeur
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setPageStep(1)
        slider.setProperty("help_text", "Associer une action")
        slider.installEventFilter(self)
        self.nb_icons_dialog_slider = slider  # Stocker pour les clics sur emojis
        
        def on_nb_icons_changed(v):
            self.nb_icons_menu = v
            # Reconstruire le menu avec le nouveau nombre d'icônes
            self.refresh_menu()
        
        slider.valueChanged.connect(on_nb_icons_changed)
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
        layout.addWidget(slider_container)
        
        # Checkbox pour l'icône centrale
        central_icon_checkbox = QCheckBox("Icône centrale au survol")
        central_icon_checkbox.setChecked(self.show_central_icon)
        central_icon_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                background-color: white;
                border: 1px solid black;
                width: 14px;
                height: 14px;
                margin-left: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff8c00;
            }
            """)
        
        def on_central_icon_changed(state):
            self.show_central_icon = (state == Qt.CheckState.Checked.value)
            apply_live()
        
        central_icon_checkbox.stateChanged.connect(on_central_icon_changed)
        layout.addWidget(central_icon_checkbox)
        
        # Checkbox pour le néon central
        neon_checkbox = QCheckBox("Néon central")
        neon_checkbox.setChecked(self.central_neon)
        neon_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                background-color: white;
                border: 1px solid black;
                width: 14px;
                height: 14px;
                margin-left: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff8c00;
            }
            """)
        
        def on_neon_changed(state):
            self.central_neon = (state == Qt.CheckState.Checked.value)
            apply_live()
        
        neon_checkbox.stateChanged.connect(on_neon_changed)
        layout.addWidget(neon_checkbox)

        # Couleur du néon
        neon_color_layout = QHBoxLayout()
        neon_color_label = QLabel("Couleur du néon")
        neon_color_label.setFixedWidth(140)
        
        neon_color_button = QPushButton()
        neon_color_button.setFixedHeight(30)
        neon_color_button.setFixedWidth(150)
        
        # Variable pour stocker la couleur du néon
        selected_neon_color = list(self.neon_color)
        
        def update_neon_button():
            r, g, b = selected_neon_color
            neon_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
            """)
            # neon_color_button.setText(f"RGB({r}, {g}, {b})")
        
        def pick_neon_color():
            r, g, b = selected_neon_color
            initial_color = QColor(r, g, b)
            color = QColorDialog.getColor(initial_color, dialog, "Couleur du néon")
            if color.isValid():
                selected_neon_color[0] = color.red()
                selected_neon_color[1] = color.green()
                selected_neon_color[2] = color.blue()
                update_neon_button()
                # Appliquer en live
                self.neon_color = tuple(selected_neon_color)
                apply_live()
        
        neon_color_button.clicked.connect(pick_neon_color)
        update_neon_button()
        
        neon_color_layout.addWidget(neon_color_label)
        neon_color_layout.addWidget(neon_color_button)
        neon_color_layout.setContentsMargins(45, 0, 60, 0)
        neon_color_layout.addStretch()
        layout.addLayout(neon_color_layout)
        
        # Slider pour la vitesse du néon
        neon_speed_layout = QVBoxLayout()
        neon_speed_label = QLabel(f"Vitesse du néon ➤ <b>{self.neon_speed}</b> ms")
        neon_speed_slider = QSlider(Qt.Orientation.Horizontal)
        # Bornes des vitesses
        neon_speed_slider.setMinimum(1)
        neon_speed_slider.setMaximum(200)
        neon_speed_slider.setValue(self.neon_speed)
        
        def on_neon_speed_changed(v):
            neon_speed_label.setText(f"Vitesse du néon ➤ <b>{v}</b> ms")
            self.neon_speed = v
            apply_live()
        
        neon_speed_slider.valueChanged.connect(on_neon_speed_changed)
        neon_speed_layout.addWidget(neon_speed_label)
        neon_speed_layout.addWidget(neon_speed_slider)
        neon_speed_layout.setContentsMargins(45, 0, 30, 0)
        layout.addLayout(neon_speed_layout)

        neon_widgets = (
            neon_color_label,
            neon_color_button,
            neon_speed_label,
            neon_speed_slider,
        )

        def update_neon_config_visibility():
            enabled = neon_checkbox.isChecked()
            for widget in neon_widgets:
                widget.setVisible(enabled)
            dialog.setFixedSize(400, 980 if enabled else 890)

        # Initialisation
        update_neon_config_visibility()

        # Connexion
        neon_checkbox.stateChanged.connect(update_neon_config_visibility)

        # --- Ombre ---
        # Checkbox pour activer l'ombre
        shadow_checkbox = QCheckBox("Ombre")
        shadow_checkbox.setChecked(self.shadow_enabled)
        shadow_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                margin-top: 10px;
            }
            QCheckBox::indicator {
                background-color: white;
                border: 1px solid black;
                width: 14px;
                height: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff8c00;
            }
            """)
        
        def on_shadow_enabled_changed(state):
            self.shadow_enabled = (state == Qt.CheckState.Checked.value)
            apply_live()
        
        shadow_checkbox.stateChanged.connect(on_shadow_enabled_changed)
        layout.addWidget(shadow_checkbox)
        
        # Slider pour le décalage de l'ombre
        shadow_offset_layout = QVBoxLayout()
        shadow_offset_label = QLabel(f"Décalage ➤ <b>{self.shadow_offset}</b> px")
        shadow_offset_slider = QSlider(Qt.Orientation.Horizontal)
        shadow_offset_slider.setMinimum(0)
        shadow_offset_slider.setMaximum(15)
        shadow_offset_slider.setValue(self.shadow_offset)
        
        def on_shadow_offset_changed(v):
            shadow_offset_label.setText(f"Décalage ➤ <b>{v}</b> px")
            self.shadow_offset = v
            apply_live()
        
        shadow_offset_slider.valueChanged.connect(on_shadow_offset_changed)
        shadow_offset_layout.addWidget(shadow_offset_label)
        shadow_offset_layout.addWidget(shadow_offset_slider)
        shadow_offset_layout.setContentsMargins(45, 0, 30, 0)
        layout.addLayout(shadow_offset_layout)
        
        # Slider pour l'angle de l'ombre
        shadow_angle_layout = QVBoxLayout()
        shadow_angle_label = QLabel(f"Angle ➤ <b>{self.shadow_angle}</b>°")
        shadow_angle_slider = QSlider(Qt.Orientation.Horizontal)
        shadow_angle_slider.setMinimum(0)
        shadow_angle_slider.setMaximum(360)
        shadow_angle_slider.setValue(self.shadow_angle)
        
        def on_shadow_angle_changed(v):
            shadow_angle_label.setText(f"Angle ➤ <b>{v}</b>°")
            self.shadow_angle = v
            apply_live()
        
        shadow_angle_slider.valueChanged.connect(on_shadow_angle_changed)
        shadow_angle_layout.addWidget(shadow_angle_label)
        shadow_angle_layout.addWidget(shadow_angle_slider)
        shadow_angle_layout.setContentsMargins(45, 0, 30, 0)
        layout.addLayout(shadow_angle_layout)
        
        # Couleur de l'ombre
        shadow_color_layout = QHBoxLayout()
        shadow_color_label = QLabel("Couleur")
        shadow_color_label.setFixedWidth(140)
        
        shadow_color_button = QPushButton()
        shadow_color_button.setFixedHeight(30)
        shadow_color_button.setFixedWidth(150)
        
        selected_shadow_color = list(self.shadow_color)
        
        def update_shadow_button():
            r, g, b = selected_shadow_color
            shadow_color_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({r}, {g}, {b});
                    border: 2px solid rgba(255, 255, 255, 100);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid rgba(255, 255, 255, 200);
                }}
            """)
        
        def pick_shadow_color():
            r, g, b = selected_shadow_color
            initial_color = QColor(r, g, b)
            color = QColorDialog.getColor(initial_color, dialog, "Couleur de l'ombre")
            if color.isValid():
                selected_shadow_color[0] = color.red()
                selected_shadow_color[1] = color.green()
                selected_shadow_color[2] = color.blue()
                update_shadow_button()
                # Appliquer en live
                self.shadow_color = tuple(selected_shadow_color)
                apply_live()
        
        shadow_color_button.clicked.connect(pick_shadow_color)
        update_shadow_button()
        
        shadow_color_layout.addWidget(shadow_color_label)
        shadow_color_layout.addWidget(shadow_color_button)
        shadow_color_layout.setContentsMargins(45, 0, 60, 0)
        shadow_color_layout.addStretch()
        layout.addLayout(shadow_color_layout)

        # Widgets de l'ombre à cacher/montrer
        shadow_widgets = (
            shadow_offset_label,
            shadow_offset_slider,
            shadow_angle_label,
            shadow_angle_slider,
            shadow_color_label,
            shadow_color_button,
        )

        def update_shadow_config_visibility():
            enabled = shadow_checkbox.isChecked()
            for widget in shadow_widgets:
                widget.setVisible(enabled)

        # Initialisation
        update_shadow_config_visibility()

        # Connexion
        shadow_checkbox.stateChanged.connect(update_shadow_config_visibility)

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
        
        def cancel_and_restore():
            """Annuler : restaurer l'état initial et fermer"""
            restore_initial()
            dialog.reject()
        
        cancel_button.clicked.connect(cancel_and_restore)
        
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
            # Les valeurs sont déjà dans self grâce au live preview
            # Il suffit de sauvegarder dans le fichier
            self.save_config()
            
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
        
        # Si le dialogue a été rejeté (annulé, X, Escape), restaurer l'état initial
        if dialog.result() != QDialog.DialogCode.Accepted:
            restore_initial()

    def show_shortcuts_dialog(self, x, y):
        """Affiche la fenêtre de configuration des raccourcis clavier"""
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Créer et afficher la fenêtre des raccourcis
        shortcuts_window = KeyboardShortcutsManager(self, self.current_popup, self.nb_icons_menu)
        
        # Centrer la fenêtre sur l'écran
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_x = (screen_geometry.width() - shortcuts_window.width()) // 2
            window_y = (screen_geometry.height() - shortcuts_window.height()) // 2
            shortcuts_window.move(window_x, window_y)
        else:
            shortcuts_window.move(x - shortcuts_window.width() // 2, y - shortcuts_window.height() // 2)
        
        shortcuts_window.exec()

    def new_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input, slider):
            name = name_input.text().strip()
            value = value_input.toPlainText().strip().replace('\n', '\\n')
            
            # Capturer le HTML et vérifier s'il contient du formatting riche
            html_content = value_input.toHtml()
            html_to_save = html_content if has_rich_formatting(html_content) else None
            
            if name and value:
                # Si une image a été sélectionnée, créer le thumbnail
                if self.dialog_temp_image_path:
                    thumbnail_path = create_thumbnail(self.dialog_temp_image_path, self.thumbnails_dir)
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
                
                # Sauvegarder avec le HTML si présent
                append_to_actions_file_json(self.clip_notes_file_json, name, value, action, html_to_save)
                
                dialog.accept()
                self.delete_mode = False
                
                # Au lieu de relaunch_window, on rafraîchit le menu
                self.refresh_menu()
            else:
                print("Les deux champs doivent être remplis")
        
        self.create_clip_dialog(
            title="➕ Ajouter",
            button_text="Ajouter",
            x=x, y=y,
            placeholder="Contenu (ex: lien ou texte)",
            on_submit_callback=handle_submit
        )

    def edit_clip_from_storage(self, name, value, x, y, slider_value, storage_dialog, html_string=None):
        """Édite un clip depuis le dialogue de stockage"""
        # Fermer le dialogue de stockage
        storage_dialog.accept()
        # Appeler edit_clip avec le contexte from_storage
        self.edit_clip(name, value, x, y, slider_value, context="from_storage", html_string=html_string)

    def edit_clip(self, name, value, x, y, slider_value, context = "from_radial", html_string=None):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input, slider):
            new_name = name_input.text().strip()
            new_value = value_input.toPlainText().strip().replace('\n', '\\n')
            
            # Capturer le HTML et vérifier s'il contient du formatting riche
            new_html = value_input.toHtml()
            new_html_to_save = new_html if has_rich_formatting(new_html) else None

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
                if self.dialog_temp_image_path:
                    thumbnail_path = create_thumbnail(self.dialog_temp_image_path, self.thumbnails_dir)
                    if thumbnail_path:
                        new_name = thumbnail_path  # Utiliser le chemin du thumbnail comme nom
                        print(f"Nouveau thumbnail créé: {thumbnail_path}")
                    else:
                        print("Erreur lors de la création du thumbnail")
                        return
                
                if new_name != old_name:
                    # Seulement si on vient du menu radial
                    if context == "from_radial":
                        self.actions_map_sub.pop(old_name, None)
                        # Supprimer l'ancien alias du JSON
                        delete_from_json(self.clip_notes_file_json, old_name)
                    
                    # Supprimer l'ancien thumbnail s'il existe (si c'est un chemin de fichier)
                    if "/" in old_name and os.path.exists(old_name):
                        try:
                            os.remove(old_name)
                            print(f"Ancien thumbnail supprimé: {old_name}")
                        except Exception as e:
                            print(f"Erreur lors de la suppression de l'ancien thumbnail: {e}")
                
                # Sauvegarder dans le bon fichier selon le contexte
                if context == "from_storage":
                    # Sauvegarder dans le fichier de stockage
                    # D'abord supprimer l'ancien clip du stockage
                    self.remove_stored_clip(old_name)
                    # Supprimer l'ancien thumbnail si le nom a changé
                    if new_name != old_name and "/" in old_name and os.path.exists(old_name):
                        try:
                            os.remove(old_name)
                            print(f"Ancien thumbnail supprimé: {old_name}")
                        except Exception as e:
                            print(f"Erreur lors de la suppression de l'ancien thumbnail: {e}")
                    # Ajouter le nouveau clip au stockage avec le HTML si présent
                    self.add_stored_clip(new_name, action, new_value, new_html_to_save)
                else:
                    # Seulement pour le menu radial : ajouter à actions_map_sub
                    if action == "copy":
                        self.actions_map_sub[new_name] = [(paperclip_copy, [new_value], {}), new_value, action]
                    elif action == "term":
                        self.actions_map_sub[new_name] = [(execute_terminal, [new_value], {}), new_value, action]
                    elif action == "exec":
                        self.actions_map_sub[new_name] = [(execute_command, [new_value], {}), new_value, action]
                    
                    # Sauvegarder dans le menu radial avec le HTML si présent
                    replace_or_append_json(self.clip_notes_file_json, new_name, new_value, action, new_html_to_save)
                
                dialog.accept()
                
                if context == "from_radial":
                    # Rester en mode modification au lieu de revenir au menu principal
                    self.update_clip(x, y, context)
                elif context == "from_storage":
                    # Rouvrir immédiatement la fenêtre de stockage
                    self.show_stored_clips_dialog(x, y)
            else:
                print("Les deux champs doivent être remplis")

        self.create_clip_dialog(
            title="🔧 Modifier",
            button_text="Modifier",
            x=x, y=y,
            initial_name=name,
            initial_value=value,
            initial_slider_value=slider_value,  # PASSER la valeur du slider
            initial_html=html_string,  # PASSER le HTML pour conserver le formatting
            on_submit_callback=handle_submit,
            on_close_callback=lambda: self.show_stored_clips_dialog(x, y) if context == "from_storage" else None
        )

    def show_window_at(self, x, y, wm_name):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        # Stocker les coordonnées pour refresh_menu
        self.x = x
        self.y = y
        
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except RuntimeError:
            pass
        self.current_popup = None

        self.buttons_sub = []
        
        # ===== OPTIMISATION : charger le JSON une seule fois =====
        json_data = load_clip_notes_data(self.clip_notes_file_json)
        
        # Définir les tooltips pour les boutons spéciaux
        self.actions_map_sub = self.buttons_actions_by_number[self.nb_icons_menu].copy()
        populate_actions_map_from_data(json_data, self.actions_map_sub, execute_command)
        # Séparer les boutons spéciaux des autres
        special_buttons = self.special_buttons_by_number[self.nb_icons_menu]
        clips_to_sort = {k: v for k, v in self.actions_map_sub.items() if k not in special_buttons}
        
        # Récupérer l'ordre du JSON pour le tri personnalisé (données déjà chargées)
        json_order = get_json_order_from_data(json_data)
        
        # Trier seulement les clips (pas les boutons spéciaux)
        sorted_clips = sort_actions_map(clips_to_sort, json_order)
        
        # Ajouter d'abord les boutons spéciaux dans l'ordre fixe
        for name in special_buttons:
            if name in self.actions_map_sub:
                action_data, value, action = self.actions_map_sub[name]
                tooltip = value.replace(r'\n', '\n')
                self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y), tooltip, action))
        
        # Puis ajouter les clips triés (avec le HTML pour les tooltips)
        for name, (action_data, value, action) in sorted_clips:
            tooltip = value.replace(r'\n', '\n')
            # Récupérer le HTML du clip (données déjà chargées)
            _, clip_html = get_clip_data_from_data(json_data, name)
            self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y), tooltip, action, clip_html))
        
        menu_dict=self.actions_map_sub
        clips_by_link = []

        # D'abord les boutons spéciaux (toujours 1)
        for name in special_buttons:
            if name in self.actions_map_sub:
                clips_by_link.append(1)
        
        # Puis les clips triés
        for name, (action_data, value, action) in sorted_clips:
            func, children, meta = action_data
            if isinstance(meta, dict) and meta.get("is_group"):
                clips_by_link.append(len(children))
            else:
                clips_by_link.append(1)

        self.current_popup = RadialMenu(x, y, self.buttons_sub, parent=self.tracker, sub=True, tracker=self.tracker, app_instance=self, neon_color=self.neon_color, action_zone_colors=self.action_zone_colors, nb_icons_menu=self.nb_icons_menu, show_central_icon=self.show_central_icon, menu_background_color=self.menu_background_color, zone_basic_opacity=self.zone_basic_opacity, zone_hover_opacity=self.zone_hover_opacity, clips_by_link=clips_by_link, shadow_offset=self.shadow_offset, shadow_color=self.shadow_color, shadow_enabled=self.shadow_enabled, shadow_angle=self.shadow_angle)
        self.current_popup.show()
        self.current_popup.animate_open()
        
        # Appliquer l'opacité configurée
        self.current_popup.set_widget_opacity(self.menu_opacity / 100.0)
        
        # Activer le néon bleu clignotant dès l'ouverture
        self.current_popup.toggle_neon(self.central_neon)
        self.current_popup.timer.start(self.neon_speed)

# if __name__ == "__main__":
#     SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#     LOCK_FILE = os.path.join(SCRIPT_DIR, ".clipnotes.lock")

#     def create_lock_file():
#         with open(LOCK_FILE, 'w') as f:
#             f.write(str(os.getpid()))

#     def remove_lock_file():
#         try:
#             if os.path.exists(LOCK_FILE):
#                 os.remove(LOCK_FILE)
#         except:
#             pass

#     create_lock_file()
    
#     def cleanup_handler(sig, frame):
#         remove_lock_file()
#         QApplication.quit()
#         sys.exit(0)
    
#     signal.signal(signal.SIGINT, cleanup_handler)
#     signal.signal(signal.SIGTERM, cleanup_handler)
    
#     app = QApplication(sys.argv)
    
#     global tracker
#     tracker = CursorTracker()
#     tracker.show()

#     max_wait = 0.3
#     elapsed = 0.0
#     while (tracker.last_x == 0 and tracker.last_y == 0) and elapsed < max_wait:
#         QApplication.processEvents()
#         time.sleep(0.1)
#         elapsed += 0.1
    
#     tracker.update_pos()
#     x, y = tracker.last_x, tracker.last_y
    
#     QApplication.processEvents()
    
#     main_app = ClipNotesWindow()
#     main_app.tracker = tracker

#     # Fenêtre de calibration du menu Radial
#     # calibration_window = CalibrationWindow(tracker, main_app)
#     # calibration_window.show()

#     main_app.show_window_at(x, y, "")

#     try:
#         sys.exit(app.exec())
#     finally:
#         remove_lock_file()



    # global tracker
    # tracker = CursorTracker()

    # main_app = ClipNotesWindow()
    # main_app.tracker = tracker

    # def on_first_move():
    #     """Appelé dès que la souris bouge sur l'overlay."""
    #     x, y = tracker.last_x, tracker.last_y
    #     tracker.hide_overlay()  # Cacher l'overlay
    #     main_app.show_window_at(x, y, "")

    # tracker.on_first_move_callback = on_first_move
    # tracker.show()

    # try:
    #     sys.exit(app.exec())
    # finally:
    #     remove_lock_file()










    
import sys, os, time, json, subprocess, signal

# APRÈS:
import sys, os, time, json, subprocess, signal, fcntl
LOCK_FILE = "/tmp/clipnotes.lock"
PID_FILE = "/tmp/clipnotes.pid"
lock_fd = None  # File descriptor global pour maintenir le lock


# ============================================================
# 3. AVANT "if __name__ == "__main__":" (ligne ~3848)
#    Ajouter ces fonctions de gestion du lock
# ============================================================

# ====== FONCTIONS DE GESTION DU LOCK ET PID ======

def acquire_lock():
    """
    Acquiert un lock exclusif sur le fichier.
    Retourne le file descriptor si succès, None sinon.
    """
    global lock_fd
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except (IOError, OSError):
        if lock_fd:
            lock_fd.close()
            lock_fd = None
        return None

def release_lock():
    """Libère le lock et supprime les fichiers."""
    global lock_fd
    try:
        if lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
            lock_fd = None
    except:
        pass
    
    # Nettoyer les fichiers
    for f in [LOCK_FILE, PID_FILE]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass

def write_pid():
    """Écrit le PID courant dans le fichier PID."""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print(f"Erreur écriture PID: {e}")

def get_running_pid():
    """Lit le PID de l'instance en cours depuis le fichier."""
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return None


if __name__ == "__main__":
    # Variable globale pour l'app Qt (nécessaire pour le handler de signal)
    qt_app = None
    
    def handle_close_signal(signum, frame):
        """Handler pour SIGUSR1 - fermeture propre de l'application."""
        release_lock()
        if qt_app:
            qt_app.quit()
        sys.exit(0)
    
    def cleanup_handler(signum, frame):
        """Handler pour SIGINT/SIGTERM."""
        release_lock()
        if qt_app:
            qt_app.quit()
        sys.exit(0)
    
    # Configurer les handlers de signaux
    signal.signal(signal.SIGUSR1, handle_close_signal)  # Signal de fermeture propre
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    # Tenter d'acquérir le lock
    if acquire_lock() is None:
        # Une instance existe déjà - envoyer SIGUSR1 et réessayer
        existing_pid = get_running_pid()
        if existing_pid:
            try:
                os.kill(existing_pid, signal.SIGUSR1)
                time.sleep(0.15)  # Attendre la fermeture
            except ProcessLookupError:
                pass  # Le process n'existe plus
        
        # Réessayer d'acquérir le lock
        if acquire_lock() is None:
            print("Impossible d'acquérir le lock après fermeture de l'instance précédente")
            sys.exit(1)
    
    # Écrire notre PID
    write_pid()
    
    # Créer l'application Qt
    qt_app = QApplication(sys.argv)
    
    global tracker
    tracker = CursorTracker()
    tracker.show()

    # Créer ClipNotesWindow PENDANT que le tracker s'initialise
    # (son __init__ charge config, colors.json, etc.)
    main_app = ClipNotesWindow()
    main_app.tracker = tracker

    max_wait = 0.25
    elapsed = 0.0
    while (tracker.last_x == 0 and tracker.last_y == 0) and elapsed < max_wait:
        QApplication.processEvents()
        time.sleep(0.05)
        elapsed += 0.05
    
    tracker.update_pos()
    x, y = tracker.last_x, tracker.last_y
    
    QApplication.processEvents()

    main_app.show_window_at(x, y, "")

    try:
        sys.exit(qt_app.exec())
    finally:
        release_lock()