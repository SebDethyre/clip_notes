import sys
import math
import subprocess
import signal
import os
import getpass
from PyQt6.QtGui import QCursor
from PyQt6.QtGui import QPainter, QColor, QIcon, QRadialGradient, QFont
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QRect, QEasingCurve, QVariantAnimation, QEvent, QPointF
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QHBoxLayout, QSlider
from PyQt6.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextEdit, QToolTip, QLabel

from utils import *                
from ui import EmojiSelector

# Constantes de configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIP_NOTES_FILE = os.path.join(SCRIPT_DIR, "clip_notes.txt")
EMOJIS_FILE = os.path.join(SCRIPT_DIR, "emojis.txt")

DIALOG_STYLE = """
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

os.environ.pop("XDG_SESSION_TYPE", None)

LOCK_FILE = os.path.join(SCRIPT_DIR, ".clipnotes.lock")

def create_lock_file():
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_lock_file():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass

# === TRACKER POUR WAYLAND ===
class CursorTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.last_x = 0
        self.last_y = 0
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnBottomHint |
            Qt.WindowType.Tool
        )
        
        # Pas besoin de setWindowOpacity car WA_TranslucentBackground suffit
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_pos)
        self.timer.start(10)  # 10ms pour une réactivité accrue
        
    def update_pos(self):
        pos = QCursor.pos()
        self.last_x = pos.x()
        self.last_y = pos.y()
    
    def mousePressEvent(self, event):
        self.close()

class RadialMenu(QWidget):
    def __init__(self, x, y, buttons, parent=None, sub=False, tracker=None):
        # IMPORTANT : Utiliser le tracker comme parent pour Wayland
        super().__init__(tracker if tracker else parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.sub = sub
        self.tracker = tracker
        self.radius = 80
        self.btn_size = 55
        self.buttons = []

        self.diameter = 2 * (self.radius + self.btn_size)
        
        self._target_x = x - self.diameter // 2
        self._target_y = y - self.diameter // 2
        
        self.resize(self.diameter, self.diameter)
        self.move(self._target_x, self._target_y)

        self._x = x
        self._y = y
        self._central_text = ""
        self._tooltips = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)

        step = 2
        max_val = 50
        min_val = 0

        up = list(range(min_val, max_val + 1, step))
        down = list(range(max_val - step, min_val - 1, -step))
        sequence = up + down
        self.keyframes = sequence
        self._neon_radius = self.keyframes[0]  
        self.neon_enabled = False  # Par défaut désactivé
        self._neon_opacity = 120
        self._neon_color = "cyan"
        self._widget_opacity = 1.0  # Opacité personnalisée du widget

        self.current_index = 0
        angle_step = 360 / len(buttons)
        for i, button in enumerate(buttons):
            if len(button) == 2:
                label, callback = button
                tooltip = ""
            elif len(button) == 3:
                label, callback, tooltip = button
            angle = math.radians(i * angle_step)
            bx = self.diameter // 2 + self.radius * math.cos(angle) - self.btn_size // 2
            by = self.diameter // 2 + self.radius * math.sin(angle) - self.btn_size // 2

            btn = QPushButton("", self)
            if "/" in label:
                btn.setIcon(QIcon(image_pixmap(label, 32)))
            else: btn.setIcon(QIcon(emoji_pixmap(label, 32)))
            btn.setIconSize(QSize(32, 32))
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
            btn.clicked.connect(self.make_click_handler(callback))
            if tooltip:
                btn.installEventFilter(self)
                self._tooltips[btn] = tooltip
            self.buttons.append(btn)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Enter and watched in self._tooltips:
            QToolTip.showText(watched.mapToGlobal(watched.rect().center()), self._tooltips[watched], watched)
        return super().eventFilter(watched, event)

    def set_central_text(self, value):
        self._central_text = value
        self.update()

    def get_neon_radius(self):
        return self._neon_radius

    def set_neon_radius(self, value):
        self._neon_radius = value
        self.update()

    def get_neon_opacity(self):
        return self._neon_opacity

    def set_neon_opacity(self, value):
        self._neon_opacity = value
        self.update()

    def get_neon_color(self):
        return self._neon_color

    def set_neon_color(self, value):
        self._neon_color = value
        self.update()

    def get_widget_opacity(self):
        return self._widget_opacity

    def set_widget_opacity(self, value):
        self._widget_opacity = value
        # Appliquer l'opacité aux boutons aussi
        for btn in self.buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, {int(10 * value)});
                    border-radius: {self.btn_size // 2}px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, {int(100 * value)});
                }}
            """)
        self.update()

    def toggle_neon(self, enabled: bool):
        self.neon_enabled = enabled
        self.update()

    def advance_animation(self):
        self.set_neon_radius(self.keyframes[self.current_index])
        self.update()
        self.current_index = (self.current_index + 1) % len(self.keyframes)

    def make_click_handler(self, cb):
        def handler():
            cb()
            # Ne PAS fermer ici - chaque callback gère sa propre fermeture
        return handler

    def mousePressEvent(self, event):
        if not any(btn.geometry().contains(event.pos()) for btn in self.buttons):
            if self.tracker:
                self.tracker.close()
            self.close_with_animation()

    def reveal_buttons(self):
        for btn in self.buttons:
            btn.setVisible(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Appliquer l'opacité globale
        painter.setOpacity(self._widget_opacity)
        
        center = self.rect().center()

        painter.setBrush(QColor(50, 50, 50, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect())

        if self.neon_enabled:
            gradient = QRadialGradient(QPointF(center), self._neon_radius)
            gradient.setColorAt(0.0, couleur_avec_opacite(self._neon_color, self._neon_opacity))
            gradient.setColorAt(1.0, couleur_avec_opacite(self._neon_color, 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(center), self._neon_radius, self._neon_radius)

        if self._central_text:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 24)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._central_text)

    def animate_open(self):
        # Utiliser une propriété d'opacité personnalisée
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(0)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)

        def update_opacity(value):
            self.set_widget_opacity(value)
        
        self.anim.valueChanged.connect(update_opacity)
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def on_animation_finished(self):
        self.reveal_buttons()
        # NE PLUS activer le néon automatiquement ici
        # Le néon sera activé uniquement en mode édition/suppression
    
    def close_with_animation(self):
        self.neon_enabled = False
        
        # Utiliser une propriété d'opacité personnalisée
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        
        def update_opacity(value):
            self.set_widget_opacity(value)
        
        self.anim.valueChanged.connect(update_opacity)
        self.anim.finished.connect(self.close)
        self.anim.start()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tracker = None
        self.current_popup = None
        self.actions_map_sub = {}
        self.buttons_sub = []
        self.update_mode = False
        self.delete_mode = False

    def relaunch_window(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        if self.current_popup:
            try:
                self.current_popup.close()
            except RuntimeError:
                pass
            self.current_popup = None
        
        if not self.update_mode and not self.delete_mode:
            QTimer.singleShot(100, lambda: self.show_window_at(x, y, ""))
        else:
            self.show_window_at(x, y, "")
            self.update_mode = False
            self.delete_mode = False

    def update_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        self.buttons_sub = []
        for name, (action_data, value, lineno) in self.actions_map_sub.items():
            if name not in ["➕", "📝", "🗑️"]:
                self.buttons_sub.append(
                    (
                        name, 
                        self.make_handler_edit(name, value, x, y, lineno), 
                        value.replace(r'\n', '\n')
                    )
                )
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except RuntimeError:
            pass
        self.current_popup = RadialMenu(x, y, self.buttons_sub, sub=True, tracker=self.tracker)
        self.current_popup.set_central_text("📝")
        self.current_popup.set_neon_color("jaune")  # Couleur jaune pour l'édition
        self.current_popup.toggle_neon(True)  # Activer le néon en mode édition
        self.current_popup.timer.start(50)     # Démarrer l'animation du néon
        self.current_popup.show()
        self.current_popup.animate_open()

    def make_handler_edit(self, name, value, x, y, lineno):
        def handler():
            if lineno == 0:
                return
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            self.edit_clip(name, value, x, y, lineno)
        return handler

    def delete_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        self.buttons_sub = []
        for name, (action_data, value, lineno) in self.actions_map_sub.items():
            if name not in ["➕", "📝", "🗑️"]:
                self.buttons_sub.append(
                    (
                        name, 
                        self.make_handler_delete(name, value, x, y, lineno), 
                        value.replace(r'\n', '\n')
                    )
                )
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except RuntimeError:
            pass
        self.current_popup = RadialMenu(x, y, self.buttons_sub, sub=True, tracker=self.tracker)
        self.current_popup.set_central_text("🗑️")
        self.current_popup.set_neon_color("rouge")  # Couleur rouge pour la suppression
        self.current_popup.toggle_neon(True)  # Activer le néon en mode suppression
        self.current_popup.timer.start(50)     # Démarrer l'animation du néon
        self.current_popup.show()
        self.current_popup.animate_open()

    def make_handler_delete(self, name, value, x, y, lineno):
        def handler():
            if lineno == 0:
                return
            if self.tracker:
                self.tracker.update_pos()
                x, y = self.tracker.last_x, self.tracker.last_y
            
            # Créer une fenêtre de confirmation avec le tracker comme parent
            self.show_delete_confirmation(name, value, x, y, lineno)
        return handler

    def show_delete_confirmation(self, name, value, x, y, lineno):
        """Affiche une fenêtre de confirmation pour la suppression"""
        # IMPORTANT : Utiliser le tracker comme parent pour Wayland
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle("Confirmation de suppression")
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setFixedSize(350, 180)
        
        # Positionner près de la souris
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x - dialog.width() // 2, y - dialog.height() // 2)

        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Message de confirmation
        message_label = QLabel(f"Voulez-vous vraiment supprimer :\n\n{name}")
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: white; font-size: 14px;")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        # Boutons
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
            self.actions_map_sub.pop(name, None)
            delete_line_in_file(CLIP_NOTES_FILE, lineno)
            self.delete_mode = True
            dialog.accept()
            self.relaunch_window(x, y)
        
        delete_button.clicked.connect(confirm_delete)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(delete_button)
        layout.addLayout(buttons_layout)

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        
        dialog.exec()

    def make_handler_sub(self, name, value, x, y, lineno):
        def handler_sub():
            if name in self.actions_map_sub:
                func_data = self.actions_map_sub[name][0]
                if isinstance(func_data, tuple) and len(func_data) == 3:
                    func, args, kwargs = func_data
                    func(*args, **kwargs)
                    # Fermer le tracker ET le popup pour les clips normaux
                    if name not in ["➕", "📝", "🗑️"]:
                        if self.tracker:
                            self.tracker.close()
                        if self.current_popup:
                            self.current_popup.close()
                else:
                    print(f"Aucune fonction associée à '{name}'")
        return handler_sub

    # def _create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
    #                        placeholder="", on_submit_callback=None):
    #     # IMPORTANT : Utiliser le tracker comme parent pour Wayland
    #     dialog = QDialog(self.tracker)
    #     dialog.setWindowTitle(title)
    #     dialog.setWindowFlags(Qt.WindowType.Dialog)
    #     dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    #     dialog.resize(300, 400)
        
    #     if x is None or y is None:
    #         screen = QApplication.primaryScreen().geometry()
    #         x = screen.center().x() - dialog.width() // 2
    #         y = screen.center().y() - dialog.height() // 2
    #     dialog.move(x, y)

    #     content = QWidget()
    #     content.setStyleSheet(DIALOG_STYLE)

    #     layout = QVBoxLayout(content)
    #     layout.setContentsMargins(20, 20, 20, 20)
    #     layout.setSpacing(12)

    #     top_bar = QHBoxLayout()
    #     top_bar.addStretch()
    #     layout.addLayout(top_bar)

    #     name_input = QLineEdit()
    #     name_input.setPlaceholderText("Nom du clip")
    #     name_input.setMinimumHeight(30)
    #     name_input.setText(initial_name)

    #     emoji_button = QPushButton("😀 Emojis")
    #     emoji_button.setFixedHeight(30)

    #     value_input = QTextEdit()
    #     value_input.setMinimumHeight(80)
    #     if placeholder:
    #         value_input.setPlaceholderText(placeholder)
    #     if initial_value:
    #         value_input.setText(initial_value.replace(r'\n', '\n'))

    #     submit_button = QPushButton(button_text)
    #     submit_button.setFixedHeight(32)

    #     layout.addWidget(name_input)
    #     layout.addWidget(emoji_button)
    #     layout.addWidget(value_input)
    #     layout.addWidget(submit_button)

    #     def open_emoji_selector():
    #         path = EMOJIS_FILE
    #         if not os.path.exists(path):
    #             print(f"Fichier introuvable : {path}")
    #             return
    #         with open(path, "r", encoding="utf-8") as f:
    #             emojis = [line.strip() for line in f if line.strip()]
    #         selector = EmojiSelector(emojis, parent=dialog)

    #         def on_emoji_selected(emoji):
    #             cursor_pos = name_input.cursorPosition()
    #             current_text = name_input.text()
    #             new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
    #             name_input.setFocus()
    #             name_input.setText(new_text)
    #             name_input.setCursorPosition(cursor_pos + len(emoji))
    #             selector.accept()

    #         selector.emoji_selected = on_emoji_selected
    #         selector.exec()

    #     emoji_button.clicked.connect(open_emoji_selector)
        
    #     if on_submit_callback:
    #         submit_button.clicked.connect(
    #             lambda: on_submit_callback(dialog, name_input, value_input)
    #         )

    #     dialog_layout = QVBoxLayout(dialog)
    #     dialog_layout.setContentsMargins(0, 0, 0, 0)
    #     dialog_layout.addWidget(content)
    #     name_input.setFocus()
    #     dialog.exec()
        
    #     return dialog
    # def _create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
    #                        placeholder="", on_submit_callback=None):
    #     # IMPORTANT : Utiliser le tracker comme parent pour Wayland
    #     dialog = QDialog(self.tracker)
    #     dialog.setWindowTitle(title)
    #     dialog.setWindowFlags(Qt.WindowType.Dialog)
    #     dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    #     dialog.resize(300, 400)
        
    #     if x is None or y is None:
    #         screen = QApplication.primaryScreen().geometry()
    #         x = screen.center().x() - dialog.width() // 2
    #         y = screen.center().y() - dialog.height() // 2
    #     dialog.move(x, y)

    #     content = QWidget()
    #     content.setStyleSheet(DIALOG_STYLE)

    #     layout = QVBoxLayout(content)
    #     layout.setContentsMargins(20, 20, 20, 20)
    #     layout.setSpacing(12)

    #     top_bar = QHBoxLayout()
    #     top_bar.addStretch()
    #     layout.addLayout(top_bar)

    #     name_input = QLineEdit()
    #     name_input.setPlaceholderText("Nom du clip")
    #     name_input.setMinimumHeight(30)
    #     name_input.setText(initial_name)

    #     emoji_button = QPushButton("😀 Emojis")
    #     emoji_button.setFixedHeight(30)

    #     # Slider avec emojis
    #     slider_container = QWidget()
    #     slider_layout = QVBoxLayout(slider_container)
    #     slider_layout.setContentsMargins(0, 0, 0, 0)
    #     slider_layout.setSpacing(2)

    #     # Labels pour les emojis au-dessus
    #     emoji_labels_layout = QHBoxLayout()
    #     emoji_labels_layout.setContentsMargins(0, 0, 0, 0)
    #     emoji_labels = ["📋", "⚡", "🚀"]  # Modifiez selon vos besoins
    #     for emoji in emoji_labels:
    #         label = QLabel(emoji)
    #         label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #         label.setStyleSheet("font-size: 20px;")
    #         emoji_labels_layout.addWidget(label)
        
    #     slider_layout.addLayout(emoji_labels_layout)

    #     # Slider
    #     slider = QSlider(Qt.Orientation.Horizontal)
    #     slider.setMinimum(0)
    #     slider.setMaximum(2)
    #     slider.setValue(0)
    #     slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    #     slider.setTickInterval(1)
    #     slider.setSingleStep(1)
    #     slider.setPageStep(1)
    #     slider.setStyleSheet("""
    #         QSlider::groove:horizontal {
    #             height: 6px;
    #             background: #555;
    #             border-radius: 3px;
    #         }
    #         QSlider::handle:horizontal {
    #             background: #fff;
    #             border: 2px solid #888;
    #             width: 16px;
    #             margin: -6px 0;
    #             border-radius: 9px;
    #         }
    #     """)
    #     slider_layout.addWidget(slider)

    #     value_input = QTextEdit()
    #     value_input.setMinimumHeight(80)
    #     if placeholder:
    #         value_input.setPlaceholderText(placeholder)
    #     if initial_value:
    #         value_input.setText(initial_value.replace(r'\n', '\n'))

    #     submit_button = QPushButton(button_text)
    #     submit_button.setFixedHeight(32)

    #     layout.addWidget(name_input)
    #     layout.addWidget(emoji_button)
    #     layout.addWidget(slider_container)
    #     layout.addWidget(value_input)
    #     layout.addWidget(submit_button)

    #     def open_emoji_selector():
    #         path = EMOJIS_FILE
    #         if not os.path.exists(path):
    #             print(f"Fichier introuvable : {path}")
    #             return
    #         with open(path, "r", encoding="utf-8") as f:
    #             emojis = [line.strip() for line in f if line.strip()]
    #         selector = EmojiSelector(emojis, parent=dialog)

    #         def on_emoji_selected(emoji):
    #             cursor_pos = name_input.cursorPosition()
    #             current_text = name_input.text()
    #             new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
    #             name_input.setFocus()
    #             name_input.setText(new_text)
    #             name_input.setCursorPosition(cursor_pos + len(emoji))
    #             selector.accept()

    #         selector.emoji_selected = on_emoji_selected
    #         selector.exec()

    #     emoji_button.clicked.connect(open_emoji_selector)
        
    #     if on_submit_callback:
    #         submit_button.clicked.connect(
    #             lambda: on_submit_callback(dialog, name_input, value_input, slider)
    #         )

    #     dialog_layout = QVBoxLayout(dialog)
    #     dialog_layout.setContentsMargins(0, 0, 0, 0)
    #     dialog_layout.addWidget(content)
    #     name_input.setFocus()
    #     dialog.exec()
        
    #     return dialog









    def _create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
                           placeholder="", on_submit_callback=None):
        # IMPORTANT : Utiliser le tracker comme parent pour Wayland
        dialog = QDialog(self.tracker)
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(Qt.WindowType.Dialog)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.resize(300, 400)
        
        if x is None or y is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x, y)

        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        layout.addLayout(top_bar)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Nom du clip")
        name_input.setMinimumHeight(30)
        name_input.setText(initial_name)

        emoji_button = QPushButton("😀 Emojis")
        emoji_button.setFixedHeight(30)

        # Slider avec emojis
        slider_container = QWidget()
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(2)

        # Labels pour les emojis au-dessus
        emoji_labels_layout = QHBoxLayout()
        emoji_labels_layout.setContentsMargins(8, 0, 8, 0)
        emoji_labels_layout.setSpacing(0)
        emoji_labels = ["📋", "⚡", "🚀"]
        
        for i, emoji in enumerate(emoji_labels):
            if i > 0:
                emoji_labels_layout.addStretch()
            label = QLabel(emoji)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 20px;")
            emoji_labels_layout.addWidget(label)
            if i < len(emoji_labels) - 1:
                emoji_labels_layout.addStretch()
        
        slider_layout.addLayout(emoji_labels_layout)

        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(2)
        slider.setValue(0)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setPageStep(1)
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
        slider_layout.addWidget(slider)

        value_input = QTextEdit()
        value_input.setMinimumHeight(80)
        if placeholder:
            value_input.setPlaceholderText(placeholder)
        if initial_value:
            value_input.setText(initial_value.replace(r'\n', '\n'))

        submit_button = QPushButton(button_text)
        submit_button.setFixedHeight(32)

        layout.addWidget(name_input)
        layout.addWidget(emoji_button)
        layout.addWidget(slider_container)
        layout.addWidget(value_input)
        layout.addWidget(submit_button)

        def open_emoji_selector():
            path = EMOJIS_FILE
            if not os.path.exists(path):
                print(f"Fichier introuvable : {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                emojis = [line.strip() for line in f if line.strip()]
            selector = EmojiSelector(emojis, parent=dialog)

            def on_emoji_selected(emoji):
                cursor_pos = name_input.cursorPosition()
                current_text = name_input.text()
                new_text = current_text[:cursor_pos] + emoji + current_text[cursor_pos:]
                name_input.setFocus()
                name_input.setText(new_text)
                name_input.setCursorPosition(cursor_pos + len(emoji))
                selector.accept()

            selector.emoji_selected = on_emoji_selected
            selector.exec()

        emoji_button.clicked.connect(open_emoji_selector)
        
        if on_submit_callback:
            submit_button.clicked.connect(
                lambda: on_submit_callback(dialog, name_input, value_input, slider)
            )

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        name_input.setFocus()
        dialog.exec()
        
        return dialog

    def new_clip(self, x, y):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        def handle_submit(dialog, name_input, value_input):
            self.buttons_sub = []
            name = name_input.text().strip()
            value = value_input.toPlainText().strip().replace('\n', '\\n')
            if name and value:
                # self.actions_map_sub[name] = (paperclip_copy, [value], {})
                # self.actions_map_sub[name] = (execute_terminal, [value], {})
                self.actions_map_sub[name] = (execute_command, [value], {})
                append_to_actions_file(CLIP_NOTES_FILE, name, value)
                dialog.accept()
                self.delete_mode = False
            else:
                print("Les deux champs doivent être remplis")
        
        self._create_clip_dialog(
            title="Ajouter un clip",
            button_text="Ajouter",
            x=x, y=y,
            placeholder="Contenu (ex: lien ou texte)",
            on_submit_callback=handle_submit
        )
        self.relaunch_window(x, y)

    def edit_clip(self, name, value, x, y, lineno):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        global li
        li = lineno

        def handle_submit(dialog, name_input, value_input):
            new_name = name_input.text().strip()
            new_value = value_input.toPlainText().strip().replace('\n', '\\n')

            if new_name and new_value:
                old_name = name
                if new_name != old_name:
                    self.actions_map_sub.pop(old_name, None)
                # self.actions_map_sub[new_name] = (paperclip_copy, [new_value], {}, li)
                # self.actions_map_sub[new_name] = (execute_terminal, [new_value], {}, li)
                self.actions_map_sub[new_name] = (execute_command, [new_value], {}, li)
                replace_or_append_at_lineno(CLIP_NOTES_FILE, new_name, new_value, li)
                dialog.accept()
                self.update_mode = True
            else:
                print("Les deux champs doivent être remplis")

        self._create_clip_dialog(
            title="Éditer un clip",
            button_text="Modifier",
            x=x, y=y,
            initial_name=name,
            initial_value=value,
            on_submit_callback=handle_submit
        )
        self.relaunch_window(x, y)

    def show_window_at(self, x, y, wm_name):
        if self.tracker:
            self.tracker.update_pos()
            x, y = self.tracker.last_x, self.tracker.last_y
        
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except RuntimeError:
            pass
        self.current_popup = None

        self.buttons_sub = []
        self.actions_map_sub = {
            "➕": [(self.new_clip,    [x,y], {}), "", 0],
            "📝": [(self.update_clip, [x,y], {}), "", 0],
            "🗑️": [(self.delete_clip, [x,y], {}), "", 0],
        }
        # populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub, paperclip_copy)
        # populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub, execute_terminal)
        populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub, execute_command)

        for name, (action_data, value, lineno) in self.actions_map_sub.items():
            self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y, lineno), value.replace(r'\n', '\n')))
        self.current_popup = RadialMenu(x, y, self.buttons_sub, sub=True, tracker=self.tracker)
        self.current_popup.show()
        self.current_popup.animate_open()

if __name__ == "__main__":
    create_lock_file()
    
    def cleanup_handler(sig, frame):
        remove_lock_file()
        QApplication.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    app = QApplication(sys.argv)
    
    global tracker
    tracker = CursorTracker()
    tracker.show()
    
    import time
    max_wait = 0.2
    elapsed = 0.0
    while (tracker.last_x == 0 and tracker.last_y == 0) and elapsed < max_wait:
        QApplication.processEvents()
        time.sleep(0.01)
        elapsed += 0.01
    
    # Forcer une dernière mise à jour pour être précis
    tracker.update_pos()
    x, y = tracker.last_x, tracker.last_y
    
    QApplication.processEvents()
    
    main_app = App()
    main_app.tracker = tracker
    main_app.show_window_at(x, y, "")

    try:
        sys.exit(app.exec())
    finally:
        remove_lock_file()