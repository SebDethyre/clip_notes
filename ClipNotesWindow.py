import sys
import math
import subprocess
import signal
import os
import getpass
from PyQt5.QtGui import QCursor
from PyQt5.QtGui import QPainter, QColor, QIcon, QRadialGradient, QFont
from PyQt5.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QRect, QEasingCurve, QVariantAnimation, QEvent
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMainWindow, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QDialog, QLineEdit, QMessageBox, QTextEdit, QToolTip

from utils import *                
from ui import EmojiSelector

# Constantes de configuration - détection automatique du répertoire
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIP_NOTES_FILE = os.path.join(SCRIPT_DIR, "clip_notes.txt")
EMOJIS_FILE = os.path.join(SCRIPT_DIR, "emojis.txt")

# Style CSS pour les dialogs
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
    """Crée un fichier lock avec le PID actuel."""
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_lock_file():
    """Supprime le fichier lock."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass
class RadialMenu(QWidget):
    def __init__(self, x, y, buttons, parent=None, sub= False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.sub = sub
        self.radius = 80
        self.btn_size = 55
        self.buttons = []

        self.diameter = 2 * (self.radius + self.btn_size)
        self.setGeometry(x - self.diameter // 2, y - self.diameter // 2, self.diameter, self.diameter)

        self._x = x
        self._y = y
        self._central_text = ""
        self._tooltips = {}


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation)
        # chaque 200 ms → ajustable
        # self.timer.start(200)

        # == Néon ==
        # sequence = [10, 20, 30, 40, 50, 40, 30, 20, 10]
        step = 2
        max_val = 50
        min_val = 0

        up = list(range(min_val, max_val + 1, step))            # 10 → 50 par +2
        down = list(range(max_val - step, min_val - 1, -step))  # 48 → 10
        sequence = up + down
        self.keyframes = sequence
        self._neon_radius = self.keyframes[0]  
        self.neon_enabled = False
        self._neon_opacity = 120
        self._neon_color = "cyan"

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
            # caché au départ
            btn.setVisible(False)
            btn.clicked.connect(self.make_click_handler(callback))
            if tooltip:
                btn.installEventFilter(self)
                self._tooltips[btn] = tooltip
            self.buttons.append(btn)
        self.animate_open()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Enter and watched in self._tooltips:
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

    def toggle_neon(self, enabled: bool):
        self.neon_enabled = enabled
        # force le repaint
        self.update()

    def advance_animation(self):
        self.set_neon_radius(self.keyframes[self.current_index])
        self.update()
        self.current_index = (self.current_index + 1) % len(self.keyframes)

    def make_click_handler(self, cb):
        return lambda: (cb(), self.close_with_animation())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()

        # Fond général discret
        painter.setBrush(QColor(50, 50, 50, 100))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.rect())

        # Halo néon uniquement si activé
        if self.neon_enabled:
            gradient = QRadialGradient(center, self._neon_radius)
            gradient.setColorAt(0.0, couleur_avec_opacite(self._neon_color, self._neon_opacity))  # intense au centre
            gradient.setColorAt(0.6, couleur_avec_opacite(self._neon_color, 40))                  # diffus au bord
            gradient.setColorAt(1.0, couleur_avec_opacite(self._neon_color, 0))                   # transparent à la périphérie

            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                center,
                self._neon_radius,
                self._neon_radius
            )

        # Texte ou emoji au centre
        content = self._central_text
        if is_emoji(content):
            emoji_pix = emoji_pixmap(content, size=32)
            center_x = center.x() - emoji_pix.width() // 2
            center_y = center.y() - emoji_pix.height() // 2
            painter.drawPixmap(center_x, center_y, emoji_pix)
        else:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Segoe UI", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, content)

    def mousePressEvent(self, event):
        if not any(btn.geometry().contains(event.pos()) for btn in self.buttons):
            self.close_with_animation()

    def reveal_buttons(self):
        for btn in self.buttons:
            btn.setVisible(True)

    def animate_open(self):
        self.setWindowOpacity(1)

        # rayon initial
        self._neon_radius = self.keyframes[0]
        # stoppe la pulsation pendant l'ouverture
        self.timer.stop()

        center = self.geometry().center()
        end_geometry = self.geometry()
        start_geometry = QRect(center.x(), center.y(), 0, 0)
        self.setGeometry(start_geometry)

        self.open_anim = QPropertyAnimation(self, b"geometry")
        self.open_anim.setDuration(300)
        self.open_anim.setStartValue(start_geometry)
        self.open_anim.setEndValue(end_geometry)
        self.open_anim.setEasingCurve(QEasingCurve.InBack)

        # Ajout d'une animation parallèle pour le rayon
        self.radius_anim = QVariantAnimation(self)
        self.radius_anim.setDuration(300)
        self.radius_anim.setStartValue(self.keyframes[0])
        # valeur moyenne
        self.radius_anim.setEndValue(self.keyframes[len(self.keyframes)//2])
        self.radius_anim.setEasingCurve(QEasingCurve.InBack)
        self.radius_anim.valueChanged.connect(self.set_neon_radius)

        def on_open_finished():
            self.reveal_buttons()
            self.timer.start(60)
        self.open_anim.finished.connect(on_open_finished)

        # Démarre les deux animations en parallèle
        self.radius_anim.start()
        self.open_anim.start()

    def close_with_animation(self):
        # Stoppe la pulsation pendant la fermeture
        self.timer.stop()

        start_geometry = self.geometry()
        center = start_geometry.center()
        end_geometry = QRect(center.x(), center.y(), 0, 0)

        # Animation géométrique (réduction)
        self.collapse_anim = QPropertyAnimation(self, b"geometry")
        self.collapse_anim.setDuration(300)
        self.collapse_anim.setStartValue(start_geometry)
        self.collapse_anim.setEndValue(end_geometry)
        self.collapse_anim.setEasingCurve(QEasingCurve.OutBack)

        # Animation du rayon néon (vers plus petit)
        self.collapse_radius_anim = QVariantAnimation(self)
        self.collapse_radius_anim.setDuration(300)
        self.collapse_radius_anim.setStartValue(self._neon_radius)
        # rayon initial (plus petit)
        self.collapse_radius_anim.setEndValue(self.keyframes[0])
        self.collapse_radius_anim.setEasingCurve(QEasingCurve.OutBack)
        self.collapse_radius_anim.valueChanged.connect(self.set_neon_radius)

        def on_close_finished():
            self.close()
        self.collapse_anim.finished.connect(on_close_finished)

        # Démarre les deux animations en parallèle
        self.collapse_radius_anim.start()
        self.collapse_anim.start()

    def mousePressEvent(self, event):
        if not any(child.geometry().contains(event.pos()) for child in self.findChildren(QPushButton)):
            self.close_with_animation()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setGeometry(0, 0, 1, 1)  # Invisible window

        self.current_popup = None
        self.actions_map_sub = {}
        self.buttons_sub = []
        self.new_popup = None
        self.popup_list = []

        self.delete_mode = False
        self.update_mode = False

    def relaunch_window(self, x, y):
        self.buttons_sub=[]
        app = App()
        app.show()

        populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub)
        for name, (action_data, value, lineno) in self.actions_map_sub.items():
            self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y, lineno), value.replace(r'\n', '\n')))

        self.current_popup = RadialMenu(x, y, self.buttons_sub, sub= False)
        self.current_popup.set_central_text("")

        if self.delete_mode:
            self.current_popup.toggle_neon(True)
            self.current_popup.set_neon_color("rouge")
            self.current_popup.set_central_text("🗑️")
        if self.update_mode:
            self.current_popup.toggle_neon(True)
            self.current_popup.set_neon_color("orange")
            self.current_popup.set_central_text("📝")

        self.current_popup.show()

    def delete_clip(self, x, y):
        self.delete_mode = True
        self.relaunch_window(x, y)

    def update_clip(self, x, y):
        self.update_mode = True
        self.relaunch_window(x, y)

    def make_handler_sub(self, name, value = "", x=None, y=None, lineno=0):
        def handler_sub():
            if self.delete_mode:
                # Création d'un QMessageBox standard
                unclearable_strings = ["🗑️", "📝", "➕", "🌿", "🎩", "🏛"]
                if name not in unclearable_strings:
                    box = QMessageBox(self)
                    box.setWindowTitle("Confirmer la suppression")
                    box.setText(f"<span style='color: white;'>Supprimer le clip '<b>{name}</b>' ?</span>")
                    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    box.setDefaultButton(QMessageBox.No)

                    # Appliquer un thème sombre et une semi-transparence
                    box.setStyleSheet("""
                        QMessageBox {
                            background-color: rgba(20, 20, 20, 180);
                            color: white;
                            font-size: 14px;
                        }
                        QPushButton {
                            background-color: #333;
                            color: white;
                            border: 1px solid #555;
                            padding: 6px 12px;
                            min-width: 80px;
                            border-radius: 5px;
                        }
                        QPushButton:hover {
                            background-color: #444;
                        }
                        QPushButton:pressed {
                            background-color: #222;
                        }
                    """)
                    # translucide
                    box.setWindowOpacity(0.50)

                    # Centrage
                    screen = QApplication.primaryScreen().availableGeometry()
                    box_geom = box.frameGeometry()
                    box_geom.moveCenter(screen.center())
                    box.move(box_geom.topLeft())

                    reply = box.exec_()
                    if reply == QMessageBox.Yes:
                        if name in self.actions_map_sub:
                            del self.actions_map_sub[name]
                            remove_from_actions_file(CLIP_NOTES_FILE, name)
                            self.current_popup.toggle_neon(False)
                            self.current_popup.set_central_text("")
                            self.current_popup.set_neon_color("cyan")
                    self.delete_mode = True
                    self.relaunch_window(x, y)
                else:
                    if name == "🗑️":
                        self.delete_mode = False
                    self.relaunch_window(x, y)

            elif self.update_mode:
                non_editable_strings = ["➕", "📝", "🗑️"]
                if name not in non_editable_strings:
                    self.update_mode = True
                    self.edit_clip(name, value, x, y, lineno)
                else:
                    if name == "📝":
                        self.update_mode = False
                        self.relaunch_window(x, y)
                    else:
                        self.relaunch_window(x, y)

            else:
                func_tuple = self.actions_map_sub.get(name)
                if func_tuple:
                    # Les autres données que le callback sont ignorées
                    func_data, _ , _ = func_tuple
                    func, args, kwargs = func_data
                    func(*args, **kwargs)
                else:
                    print(f"Aucune fonction associée à '{name}'")
        return handler_sub

    def _create_clip_dialog(self, title, button_text, x, y, initial_name="", initial_value="", 
                           placeholder="", on_submit_callback=None):
        """
        Fonction helper pour créer un dialog de clip (nouveau ou édition).
        
        Args:
            title: Titre du dialog
            button_text: Texte du bouton de soumission
            x, y: Position du dialog
            initial_name: Nom initial (vide pour nouveau clip)
            initial_value: Valeur initiale (vide pour nouveau clip)
            placeholder: Placeholder pour le champ de valeur
            on_submit_callback: Fonction callback pour la soumission
        """
        dialog = QDialog()
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.resize(300, 400)
        
        # Gestion de la position (centrage si x/y sont None)
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.center().x() - dialog.width() // 2
            y = screen.center().y() - dialog.height() // 2
        dialog.move(x, y)

        content = QWidget()
        content.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Top bar avec bouton de fermeture
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        layout.addLayout(top_bar)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Nom du clip")
        name_input.setMinimumHeight(30)
        name_input.setText(initial_name)

        emoji_button = QPushButton("😀 Emojis")
        emoji_button.setFixedHeight(30)

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
            selector.exec_()

        emoji_button.clicked.connect(open_emoji_selector)
        
        # Connecter le callback de soumission
        if on_submit_callback:
            submit_button.clicked.connect(
                lambda: on_submit_callback(dialog, name_input, value_input)
            )

        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(content)
        name_input.setFocus()
        dialog.exec_()
        
        return dialog

    def new_clip(self, x, y):
        def handle_submit(dialog, name_input, value_input):
            self.buttons_sub = []
            name = name_input.text().strip()
            value = value_input.toPlainText().strip().replace('\n', '\\n')
            if name and value:
                self.actions_map_sub[name] = (paperclip_copy, [value], {})
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
        global li
        li = lineno

        def handle_submit(dialog, name_input, value_input):
            new_name = name_input.text().strip()
            new_value = value_input.toPlainText().strip().replace('\n', '\\n')

            if new_name and new_value:
                # nom initial
                old_name = name
                if new_name != old_name:
                    # Suppression de l'ancienne entrée
                    self.actions_map_sub.pop(old_name, None)
                # Mise à jour ou ajout
                self.actions_map_sub[new_name] = (paperclip_copy, [new_value], {}, li)
                # Fichier
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

    # Active la fenêtre
    def show_window_at(self, x, y, wm_name):
        # Nettoyage sécurisé du popup existant
        try:
            if self.current_popup:
                self.current_popup.destroy()

        except RuntimeError:
            pass  # Si déjà détruit
        self.current_popup = None


        user = os.getenv("SUDO_USER") or getpass.getuser()
        home = os.path.expanduser(f"~{user}")
        display = os.getenv("DISPLAY", ":0")
        xauth = f"{home}/.Xauthority"

        new_popup = None
        self.buttons_sub = []
        # dictionnaire des actions
        self.actions_map_sub = {
            "➕": [(self.new_clip,    [x,y], {}), "", 0],
            "📝": [(self.update_clip, [x,y], {}), "", 0],
            "🗑️": [(self.delete_clip, [x,y], {}), "", 0],
        }
        populate_actions_map_from_file(CLIP_NOTES_FILE, self.actions_map_sub)

        for name, (action_data, value, lineno) in self.actions_map_sub.items():
            self.buttons_sub.append((name, self.make_handler_sub(name, value, x, y, lineno), value.replace(r'\n', '\n')))
        new_popup = RadialMenu(x, y, self.buttons_sub, sub = True)
        new_popup.show()
        
def signal_handler(sig, frame):
    print("Interruption détectée, fermeture.")
    QApplication.quit()
    sys.exit(0)

if __name__ == "__main__":
    # Juste créer le lock (le bash a déjà tué l'ancien)
    create_lock_file()
    
    # Configuration signal de fermeture
    def cleanup_handler(sig, frame):
        remove_lock_file()
        QApplication.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    # Lancer l'app
    app = QApplication(sys.argv)
    main_app = App()

    try:
        output = subprocess.check_output(["xdotool", "getmouselocation", "--shell"]).decode()
        parts = dict(line.split("=") for line in output.strip().splitlines())
        x, y = int(parts["X"]), int(parts["Y"])
    except Exception as e:
        pos = QCursor.pos()
        x, y = pos.x(), pos.y()

    main_app.show_window_at(x, y, "")

    try:
        sys.exit(app.exec_())
    finally:
        remove_lock_file()