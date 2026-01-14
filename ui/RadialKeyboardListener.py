from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QApplication

class RadialKeyboardListener(QObject):
    """Listener global pour intercepter les événements clavier"""
    def __init__(self, radial_menu):
        super().__init__()
        self.radial_menu = radial_menu

    def eventFilter(self, obj, event):
        # Seulement si le menu est visible
        # if not self.radial_menu.isVisible():
        #     return False
        
        # Ne pas traiter les événements si un dialogue est ouvert
        app = QApplication.instance()
        if app.activeModalWidget() or app.activePopupWidget():
            return False

        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            
            # Vérifier si un sous-menu hover est ouvert (et s'il existe encore)
            submenu = None
            if hasattr(self.radial_menu, '_hover_submenu') and self.radial_menu._hover_submenu is not None:
                try:
                    if self.radial_menu._hover_submenu.isVisible():
                        submenu = self.radial_menu._hover_submenu
                except RuntimeError:
                    # L'objet a été détruit
                    self.radial_menu._hover_submenu = None
            
            if submenu is not None:
                # Rediriger les événements vers le sous-menu
                if key == Qt.Key.Key_Right:
                    submenu._handle_key_right()
                    return True
                elif key == Qt.Key.Key_Left:
                    submenu._handle_key_left()
                    return True
                elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter or key == Qt.Key.Key_Down:
                    submenu._handle_key_enter()
                    return True
                elif key == Qt.Key.Key_Escape or key == Qt.Key.Key_Up:
                    submenu._handle_key_escape()
                    return True
            else:
                # Comportement normal pour le menu principal
                if key == Qt.Key.Key_Right:
                    self.radial_menu._handle_key_right()
                    return True
                elif key == Qt.Key.Key_Left:
                    self.radial_menu._handle_key_left()
                    return True
                elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter or key == Qt.Key.Key_Down:
                    self.radial_menu._handle_key_enter()
                    return True
                elif key == Qt.Key.Key_Escape or key == Qt.Key.Key_Up:
                    self.radial_menu._handle_key_escape()
                    return True

        return False
