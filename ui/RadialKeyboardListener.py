"""
RadialKeyboardListener - Gestion des événements clavier pour le menu radial
Charge et utilise les raccourcis depuis shortcuts.json
"""

import os
import json
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtGui import QKeySequence


class RadialKeyboardListener(QObject):
    """
    Écoute les événements clavier pour le menu radial.
    
    Fonctionnalités:
    - Navigation avec les flèches gauche/droite
    - Validation avec Entrée
    - Fermeture avec Escape
    - Raccourcis personnalisés depuis shortcuts.json
    - Touches 1-9 par défaut pour les clips
    """
    
    def __init__(self, radial_menu):
        super().__init__()
        self.radial_menu = radial_menu
        self.shortcuts = {}
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.shortcuts_file = os.path.join(self.script_dir, "shortcuts.json")
        self.load_shortcuts()
    
    def load_shortcuts(self):
        """Charge les raccourcis depuis shortcuts.json"""
        try:
            if os.path.exists(self.shortcuts_file):
                with open(self.shortcuts_file, 'r', encoding='utf-8') as f:
                    self.shortcuts = json.load(f)
        except Exception as e:
            print(f"Erreur chargement raccourcis: {e}")
            self.shortcuts = {}
    
    def build_shortcut_string(self, event):
        """
        Construit une chaîne de raccourci à partir d'un événement clavier.
        Format identique à celui utilisé dans KeyboardShortcutsManager.
        """
        key = event.key()
        parts = []
        
        # Ignorer les touches modificateurs seules
        modifier_keys = {
            Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
            Qt.Key.Key_Meta, Qt.Key.Key_AltGr
        }
        if key in modifier_keys:
            return None
        
        # Détecter les modificateurs avec distinction gauche/droite
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            scan = event.nativeScanCode()
            if scan == 37:
                parts.append("Ctrl_L")
            elif scan == 105:
                parts.append("Ctrl_R")
            else:
                parts.append("Ctrl")
        
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            scan = event.nativeScanCode()
            if scan == 64:
                parts.append("Alt_L")
            elif scan == 108:
                parts.append("AltGr")
            else:
                parts.append("Alt")
        
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            scan = event.nativeScanCode()
            if scan == 50:
                parts.append("Shift_L")
            elif scan == 62:
                parts.append("Shift_R")
            else:
                parts.append("Shift")
        
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            parts.append("Super")
        
        # Nom de la touche
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
        else:
            key_name = QKeySequence(key).toString()
        
        if key_name:
            parts.append(key_name)
        
        return " + ".join(parts) if parts else None
    
    def find_action_for_shortcut(self, shortcut_str):
        """
        Trouve l'action correspondant à un raccourci.
        Retourne (type, identifiant) ou None.
        """
        if not shortcut_str:
            return None
        
        # Recharger les raccourcis (au cas où ils ont changé)
        self.load_shortcuts()
        
        # Chercher dans les raccourcis personnalisés
        for key, saved_shortcut in self.shortcuts.items():
            if saved_shortcut == shortcut_str:
                if key.startswith("clip_"):
                    alias = key[5:]  # Enlever "clip_"
                    return ("clip_alias", alias)
                elif key.startswith("fixed_"):
                    button_label = key[6:]  # Enlever "fixed_"
                    return ("fixed_button", button_label)
        
        # Raccourcis par défaut : touches 1-9 pour les clips
        if len(shortcut_str) == 1 and shortcut_str.isdigit():
            digit = int(shortcut_str)
            if 1 <= digit <= 9:
                return ("clip_index", digit - 1)
        
        return None
    
    def trigger_clip_by_index(self, index):
        """Déclenche l'action du clip à l'index donné (0-8)"""
        if not self.radial_menu or not self.radial_menu.app_instance:
            return False
        
        app = self.radial_menu.app_instance
        nb_icons = app.nb_icons_menu
        special_buttons = self.radial_menu.special_buttons_by_numbers.get(nb_icons, [])
        
        # Trouver les boutons visibles qui sont des clips
        visible_clip_indices = []
        for i, btn in enumerate(self.radial_menu.buttons):
            if btn.isVisible():
                if i < len(self.radial_menu.button_labels):
                    label = self.radial_menu.button_labels[i]
                    if label not in special_buttons:
                        visible_clip_indices.append(i)
        
        if index < len(visible_clip_indices):
            clip_button_index = visible_clip_indices[index]
            btn = self.radial_menu.buttons[clip_button_index]
            
            self.radial_menu.focused_index = clip_button_index
            self.radial_menu.keyboard_used = True
            self.radial_menu.show_focused_button_info()
            self.radial_menu.update()
            
            btn.click()
            return True
        else:
            if hasattr(self.radial_menu, 'tooltip_window') and self.radial_menu.tooltip_window:
                self.radial_menu.tooltip_window.show_message(f"Pas de clip n°{index + 1}", 1500)
                self.radial_menu.update_tooltip_position()
            return False
    
    def trigger_clip_by_alias(self, alias):
        """Déclenche l'action du clip par son alias"""
        if not self.radial_menu:
            return False
        
        for i, btn in enumerate(self.radial_menu.buttons):
            if i < len(self.radial_menu.button_labels):
                if self.radial_menu.button_labels[i] == alias:
                    if btn.isVisible():
                        self.radial_menu.focused_index = i
                        self.radial_menu.keyboard_used = True
                        self.radial_menu.show_focused_button_info()
                        self.radial_menu.update()
                        btn.click()
                        return True
        return False
    
    def trigger_fixed_button(self, button_label):
        """Déclenche l'action d'un bouton fixe"""
        if not self.radial_menu:
            return False
        
        for i, btn in enumerate(self.radial_menu.buttons):
            if i < len(self.radial_menu.button_labels):
                if self.radial_menu.button_labels[i] == button_label:
                    if btn.isVisible():
                        self.radial_menu.focused_index = i
                        self.radial_menu.keyboard_used = True
                        self.radial_menu.show_focused_button_info()
                        self.radial_menu.update()
                        btn.click()
                        return True
        return False
    
    def eventFilter(self, watched, event):
        """Filtre les événements clavier"""
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            
            # Touches de navigation (prioritaires, non modifiables)
            if key == Qt.Key.Key_Left:
                if self.radial_menu.hover_submenu is not None:
                    try:
                        if self.radial_menu.hover_submenu.isVisible():
                            self.radial_menu.hover_submenu.handle_key_left()
                            return True
                    except RuntimeError:
                        self.radial_menu.hover_submenu = None
                self.radial_menu.handle_key_left()
                return True
            
            elif key == Qt.Key.Key_Right:
                if self.radial_menu.hover_submenu is not None:
                    try:
                        if self.radial_menu.hover_submenu.isVisible():
                            self.radial_menu.hover_submenu.handle_key_right()
                            return True
                    except RuntimeError:
                        self.radial_menu.hover_submenu = None
                self.radial_menu.handle_key_right()
                return True
            
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.radial_menu.hover_submenu is not None:
                    try:
                        if self.radial_menu.hover_submenu.isVisible():
                            self.radial_menu.hover_submenu.handle_key_enter()
                            return True
                    except RuntimeError:
                        self.radial_menu.hover_submenu = None
                self.radial_menu.handle_key_enter()
                return True
            
            elif key == Qt.Key.Key_Escape:
                if self.radial_menu.hover_submenu is not None:
                    try:
                        if self.radial_menu.hover_submenu.isVisible():
                            self.radial_menu.hover_submenu.handle_key_escape()
                            return True
                    except RuntimeError:
                        self.radial_menu.hover_submenu = None
                self.radial_menu.handle_key_escape()
                return True
            
            # Construire le raccourci et chercher l'action correspondante
            shortcut_str = self.build_shortcut_string(event)
            if shortcut_str:
                action = self.find_action_for_shortcut(shortcut_str)
                if action:
                    action_type, action_id = action
                    if action_type == "clip_index":
                        if self.trigger_clip_by_index(action_id):
                            return True
                    elif action_type == "clip_alias":
                        if self.trigger_clip_by_alias(action_id):
                            return True
                    elif action_type == "fixed_button":
                        if self.trigger_fixed_button(action_id):
                            return True
        
        return False