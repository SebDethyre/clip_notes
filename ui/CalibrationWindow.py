from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSlider
from PyQt6.QtWidgets import QLabel
# from utils import *

class CalibrationWindow(QWidget):
    """Prototype de fenêtre de calibration du menu radial"""
    def __init__(self, tracker, main_app):
        super().__init__()
        self.tracker = tracker
        self.main_app = main_app  # Référence à l'app principale
        
        self.setWindowTitle("Calibration Curseur Wayland")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # === SLIDER X GAUCHE ===
        x_left_layout = QHBoxLayout()
        x_left_label = QLabel("X Correction Gauche:")
        self.x_left_value = QLabel(str(tracker.x_correction_left))
        self.x_left_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_left_slider.setRange(-300, 300)
        self.x_left_slider.setValue(tracker.x_correction_left)
        self.x_left_slider.valueChanged.connect(self.update_x_left)
        
        x_left_layout.addWidget(x_left_label)
        x_left_layout.addWidget(self.x_left_slider)
        x_left_layout.addWidget(self.x_left_value)
        layout.addLayout(x_left_layout)
        
        # === SLIDER X DROITE ===
        x_right_layout = QHBoxLayout()
        x_right_label = QLabel("X Correction Droite:")
        self.x_right_value = QLabel(str(tracker.x_correction_right))
        self.x_right_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_right_slider.setRange(-300, 300)
        self.x_right_slider.setValue(tracker.x_correction_right)
        self.x_right_slider.valueChanged.connect(self.update_x_right)
        
        x_right_layout.addWidget(x_right_label)
        x_right_layout.addWidget(self.x_right_slider)
        x_right_layout.addWidget(self.x_right_value)
        layout.addLayout(x_right_layout)
        
        # === SLIDER Y HAUT ===
        y_top_layout = QHBoxLayout()
        y_top_label = QLabel("Y Correction Haut:")
        self.y_top_value = QLabel(str(tracker.y_correction_top))
        self.y_top_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_top_slider.setRange(-300, 300)
        self.y_top_slider.setValue(tracker.y_correction_top)
        self.y_top_slider.valueChanged.connect(self.update_y_top)
        
        y_top_layout.addWidget(y_top_label)
        y_top_layout.addWidget(self.y_top_slider)
        y_top_layout.addWidget(self.y_top_value)
        layout.addLayout(y_top_layout)
        
        # === SLIDER Y BAS ===
        y_bottom_layout = QHBoxLayout()
        y_bottom_label = QLabel("Y Correction Bas:")
        self.y_bottom_value = QLabel(str(tracker.y_correction_bottom))
        self.y_bottom_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_bottom_slider.setRange(-300, 300)
        self.y_bottom_slider.setValue(tracker.y_correction_bottom)
        self.y_bottom_slider.valueChanged.connect(self.update_y_bottom)
        
        y_bottom_layout.addWidget(y_bottom_label)
        y_bottom_layout.addWidget(self.y_bottom_slider)
        y_bottom_layout.addWidget(self.y_bottom_value)
        layout.addLayout(y_bottom_layout)
        
        # === BOUTON AFFICHER VALEURS ===
        print_button = QPushButton("Afficher valeurs actuelles")
        print_button.clicked.connect(self.print_values)
        layout.addWidget(print_button)
        
        # === INFO ===
        info_label = QLabel("Le menu se relance automatiquement à chaque changement")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def refresh_menu(self):
        """Relance le menu à la position actuelle du curseur"""
        self.tracker.update_pos()
        x, y = self.tracker.last_x, self.tracker.last_y
        self.main_app.show_window_at(x, y, "")
    
    def update_x_left(self, value):
        self.tracker.x_correction_left = value
        self.x_left_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_x_right(self, value):
        self.tracker.x_correction_right = value
        self.x_right_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_y_top(self, value):
        self.tracker.y_correction_top = value
        self.y_top_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def update_y_bottom(self, value):
        self.tracker.y_correction_bottom = value
        self.y_bottom_value.setText(str(value))
        self.refresh_menu()  # Relancer le menu
    
    def print_values(self):
        print("\n=== VALEURS DE CALIBRATION ===")
        print(f"self.x_correction_left = {self.tracker.x_correction_left}")
        print(f"self.x_correction_right = {self.tracker.x_correction_right}")
        print(f"self.y_correction_top = {self.tracker.y_correction_top}")
        print(f"self.y_correction_bottom = {self.tracker.y_correction_bottom}")
        print("==============================\n")