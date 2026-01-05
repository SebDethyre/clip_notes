"""
Système de calibration pour CursorTracker
Affiche des cibles sur une grille et calcule automatiquement les corrections nécessaires
"""

from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor
import json
import sys


class CalibrationTarget(QWidget):
    """Fenêtre affichant une cible de calibration"""
    
    def __init__(self, grid_x, grid_y, screen_x, screen_y, grid_width, grid_height):
        super().__init__()
        self.grid_x = grid_x  # Position dans la grille (0.0 à 1.0)
        self.grid_y = grid_y
        self.screen_x = screen_x  # Position en pixels
        self.screen_y = screen_y
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.clicked = False
        self.click_x = 0
        self.click_y = 0
        
        # Fenêtre transparente qui couvre tout l'écran
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        self.setGeometry(geometry)
        
        self.setMouseTracking(True)
        self.show()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond semi-transparent
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
        # Dessiner la cible
        target_size = 40
        center = QPoint(self.screen_x, self.screen_y)
        
        # Cercles concentriques
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(center, target_size, target_size)
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawEllipse(center, target_size // 2, target_size // 2)
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        painter.drawEllipse(center, 5, 5)
        
        # Croix au centre
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        painter.drawLine(center.x() - 10, center.y(), center.x() + 10, center.y())
        painter.drawLine(center.x(), center.y() - 10, center.x(), center.y() + 10)
        
        # Instructions
        font = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        
        text = f"Cliquez sur la cible jaune\nPosition grille: ({self.grid_x:.2f}, {self.grid_y:.2f})\n\nAppuyez sur 'S' si la cible est hors écran"
        text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, text)
        painter.drawText(text_rect.adjusted(0, 20, 0, 20), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, text)
        
        # Info grille
        grid_info = f"Point {int(self.grid_x * self.grid_width)}/{self.grid_width} × {int(self.grid_y * self.grid_height)}/{self.grid_height}"
        painter.drawText(20, self.height() - 20, grid_info)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Enregistrer la position du clic
            self.click_x = event.pos().x()
            self.click_y = event.pos().y()
            self.clicked = True
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clicked = False
            self.close()
        elif event.key() == Qt.Key.Key_S:
            # Skip - cible hors écran
            self.clicked = False
            self.close()


class CalibrationWindow(QWidget):
    """Fenêtre principale de calibration"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calibration du CursorTracker")
        self.setGeometry(100, 100, 500, 400)
        
        # Paramètres de la grille
        self.grid_width = 4  # Nombre de colonnes
        self.grid_height = 4  # Nombre de lignes
        
        screen = QApplication.primaryScreen()
        geometry = screen.geometry()
        self.screen_width = geometry.width()
        self.screen_height = geometry.height()
        
        # Résultats de calibration
        self.calibration_data = []
        self.current_point = 0
        
        # Interface
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Titre
        title = QLabel("🎯 Calibration du suivi de curseur")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Cette calibration va afficher des cibles sur votre écran.\n"
            "Cliquez précisément sur le centre jaune de chaque cible.\n"
            f"Grille: {self.grid_width}×{self.grid_height} = {self.grid_width * self.grid_height} points\n\n"
            "Appuyez sur 'Démarrer' pour commencer."
        )
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Sélection de la taille de grille
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("Taille de grille:"))
        
        self.grid_buttons = []
        for size in [(3, 3), (4, 4), (5, 5), (6, 6)]:
            btn = QPushButton(f"{size[0]}×{size[1]}")
            btn.clicked.connect(lambda checked, s=size: self.set_grid_size(s))
            grid_layout.addWidget(btn)
            self.grid_buttons.append(btn)
        
        layout.addLayout(grid_layout)
        
        # Barre de progression
        self.progress_label = QLabel("Prêt")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.progress_label)
        
        # Boutons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Démarrer la calibration")
        self.start_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(50)
        self.start_btn.clicked.connect(self.start_calibration)
        button_layout.addWidget(self.start_btn)
        
        self.save_btn = QPushButton("💾 Sauvegarder")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_calibration)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Résultats
        self.results_label = QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.results_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_grid_size(self, size):
        self.grid_width, self.grid_height = size
        self.update_ui()
    
    def update_ui(self):
        total = self.grid_width * self.grid_height
        for btn in self.grid_buttons:
            btn.setEnabled(True)
        self.results_label.setText(f"Grille sélectionnée: {self.grid_width}×{self.grid_height} ({total} points)")
    
    def start_calibration(self):
        self.calibration_data = []
        self.current_point = 0
        self.start_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        for btn in self.grid_buttons:
            btn.setEnabled(False)
        
        self.show_next_target()
    
    def show_next_target(self):
        total_points = self.grid_width * self.grid_height
        
        if self.current_point >= total_points:
            self.finish_calibration()
            return
        
        # Calculer la position dans la grille
        col = self.current_point % self.grid_width
        row = self.current_point // self.grid_width
        
        grid_x = col / (self.grid_width - 1) if self.grid_width > 1 else 0.5
        grid_y = row / (self.grid_height - 1) if self.grid_height > 1 else 0.5
        
        screen_x = int(grid_x * self.screen_width)
        screen_y = int(grid_y * self.screen_height)
        
        self.progress_label.setText(f"Point {self.current_point + 1}/{total_points}")
        
        # Afficher la cible
        target = CalibrationTarget(grid_x, grid_y, screen_x, screen_y, 
                                   self.grid_width - 1, self.grid_height - 1)
        
        # Attendre que la cible soit fermée
        QTimer.singleShot(100, lambda: self.wait_for_target(target, grid_x, grid_y, screen_x, screen_y))
    
    def wait_for_target(self, target, grid_x, grid_y, screen_x, screen_y):
        if target.isVisible():
            # La cible est encore visible, attendre
            QTimer.singleShot(100, lambda: self.wait_for_target(target, grid_x, grid_y, screen_x, screen_y))
        else:
            # La cible a été fermée
            if target.clicked:
                # Calculer l'écart
                delta_x = screen_x - target.click_x
                delta_y = screen_y - target.click_y
                
                # Enregistrer
                self.calibration_data.append({
                    'grid_x': grid_x,
                    'grid_y': grid_y,
                    'screen_x': screen_x,
                    'screen_y': screen_y,
                    'click_x': target.click_x,
                    'click_y': target.click_y,
                    'correction_x': delta_x,
                    'correction_y': delta_y
                })
                print(f"✓ Point enregistré: ({screen_x}, {screen_y})")
            else:
                # Skip (touche S ou ESC)
                print(f"⊘ Point ignoré: ({screen_x}, {screen_y})")
            
            self.current_point += 1
            QTimer.singleShot(500, self.show_next_target)
    
    def finish_calibration(self):
        total_points = self.grid_width * self.grid_height
        recorded_points = len(self.calibration_data)
        skipped_points = total_points - recorded_points
        
        self.progress_label.setText("✅ Calibration terminée!")
        self.start_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        for btn in self.grid_buttons:
            btn.setEnabled(True)
        
        if recorded_points == 0:
            self.results_label.setText("Aucun point enregistré!")
            return
        
        # Analyser les résultats
        avg_error_x = sum(abs(d['correction_x']) for d in self.calibration_data) / len(self.calibration_data)
        avg_error_y = sum(abs(d['correction_y']) for d in self.calibration_data) / len(self.calibration_data)
        max_error_x = max(abs(d['correction_x']) for d in self.calibration_data)
        max_error_y = max(abs(d['correction_y']) for d in self.calibration_data)
        
        results = (
            f"📊 Résultats:\n"
            f"• Points enregistrés: {recorded_points}/{total_points}\n"
            f"• Points ignorés: {skipped_points}\n"
            f"• Erreur moyenne X: {avg_error_x:.1f} pixels\n"
            f"• Erreur moyenne Y: {avg_error_y:.1f} pixels\n"
            f"• Erreur max X: {max_error_x:.1f} pixels\n"
            f"• Erreur max Y: {max_error_y:.1f} pixels\n\n"
            f"Cliquez sur 'Sauvegarder' pour générer le code."
        )
        self.results_label.setText(results)
    
    def cancel_calibration(self):
        self.progress_label.setText("❌ Calibration annulée")
        self.start_btn.setEnabled(True)
        for btn in self.grid_buttons:
            btn.setEnabled(True)
    
    def save_calibration(self):
        if not self.calibration_data:
            return
        
        # Générer le code Python pour la grille de correction
        code = "# Grille de correction générée automatiquement\n"
        code += f"# Grille {self.grid_width}×{self.grid_height}\n"
        code += "self.correction_grid = [\n"
        
        for data in self.calibration_data:
            code += f"    ({data['grid_x']:.2f}, {data['grid_y']:.2f}, "
            code += f"{data['correction_x']:.0f}, {data['correction_y']:.0f}),\n"
        
        code += "]\n"
        
        # Sauvegarder dans un fichier
        with open('/home/claude/calibration_grid.py', 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Sauvegarder aussi en JSON pour analyse
        with open('/home/claude/calibration_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.calibration_data, f, indent=2)
        
        self.results_label.setText(
            self.results_label.text() + 
            "\n\n✅ Sauvegardé dans:\n• calibration_grid.py (code à copier)\n• calibration_data.json (données brutes)"
        )
        
        print("\n" + "="*60)
        print("CODE GÉNÉRÉ - Copiez ceci dans votre CursorTracker:")
        print("="*60)
        print(code)
        print("="*60)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalibrationWindow()
    window.show()
    sys.exit(app.exec())