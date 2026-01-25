#!/usr/bin/env python3
"""
Outil de calibration visuelle pour Wayland.

Cliquez sur les cibles rouges. L'outil mesurera le décalage
entre la position attendue et la position rapportée par Qt.
"""

import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor
from PyQt6.QtWidgets import QApplication, QWidget


class CalibrationTool(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.screen_w = geo.width()
        self.screen_h = geo.height()
        self.setGeometry(geo)
        
        # Cibles aux 4 coins + centre
        margin = 100
        self.targets = [
            (margin, margin, "Haut-Gauche"),
            (self.screen_w - margin, margin, "Haut-Droite"),
            (self.screen_w // 2, self.screen_h // 2, "Centre"),
            (margin, self.screen_h - margin, "Bas-Gauche"),
            (self.screen_w - margin, self.screen_h - margin, "Bas-Droite"),
        ]
        
        self.current = 0
        self.measurements = []
        
        print("="*60)
        print("CALIBRATION DU CURSEUR")
        print("="*60)
        print(f"Écran: {self.screen_w}x{self.screen_h}")
        print("\nCliquez PRÉCISÉMENT sur le CENTRE de chaque cible rouge.")
        print("Appuyez sur Échap pour annuler.\n")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fond semi-transparent
        p.fillRect(self.rect(), QColor(0, 0, 0, 180))
        
        if self.current < len(self.targets):
            x, y, name = self.targets[self.current]
            
            # Cible : cercle + croix
            p.setPen(QPen(QColor(255, 0, 0), 3))
            p.drawEllipse(x - 20, y - 20, 40, 40)
            p.drawLine(x - 30, y, x + 30, y)
            p.drawLine(x, y - 30, x, y + 30)
            
            # Point central
            p.setBrush(QColor(255, 255, 0))
            p.drawEllipse(x - 3, y - 3, 6, 6)
            
            # Instructions
            p.setFont(QFont("Sans", 14))
            p.setPen(QColor(255, 255, 255))
            p.drawText(50, 50, f"Cible {self.current + 1}/{len(self.targets)}: {name}")
            p.drawText(50, 80, f"Position cible: ({x}, {y})")
            p.drawText(50, 110, "Cliquez sur le point jaune central")
        else:
            p.setFont(QFont("Sans", 16))
            p.setPen(QColor(0, 255, 0))
            p.drawText(50, 50, "Calibration terminée ! Voir le terminal.")

    def mousePressEvent(self, event):
        if self.current >= len(self.targets):
            self.close()
            return
        
        # Position attendue
        exp_x, exp_y, name = self.targets[self.current]
        
        # Position reçue via l'événement (relative à la fenêtre fullscreen)
        evt_x = int(event.position().x())
        evt_y = int(event.position().y())
        
        # Position via QCursor.pos()
        qpos = QCursor.pos()
        qc_x, qc_y = qpos.x(), qpos.y()
        
        # Calcul des décalages
        # Si on clique pile sur la cible, evt devrait = exp
        # Le décalage de QCursor = qc - evt (combien QCursor est décalé par rapport à la réalité)
        offset_qc_x = qc_x - evt_x
        offset_qc_y = qc_y - evt_y
        
        self.measurements.append({
            "name": name,
            "expected": (exp_x, exp_y),
            "event": (evt_x, evt_y),
            "qcursor": (qc_x, qc_y),
            "offset_qcursor": (offset_qc_x, offset_qc_y),
            "ratio_x": evt_x / self.screen_w,
            "ratio_y": evt_y / self.screen_h,
        })
        
        print(f"\n[{name}]")
        print(f"  Cible:     ({exp_x:4d}, {exp_y:4d})")
        print(f"  Clic réel: ({evt_x:4d}, {evt_y:4d})")
        print(f"  QCursor:   ({qc_x:4d}, {qc_y:4d})")
        print(f"  Décalage QCursor: ({offset_qc_x:+4d}, {offset_qc_y:+4d})")
        
        self.current += 1
        
        if self.current >= len(self.targets):
            self._analyze()
        
        self.update()

    def _analyze(self):
        """Analyse les mesures et propose des corrections."""
        print("\n" + "="*60)
        print("ANALYSE DES RÉSULTATS")
        print("="*60)
        
        # Décalages QCursor
        offsets_x = [m["offset_qcursor"][0] for m in self.measurements]
        offsets_y = [m["offset_qcursor"][1] for m in self.measurements]
        
        avg_x = sum(offsets_x) / len(offsets_x)
        avg_y = sum(offsets_y) / len(offsets_y)
        
        var_x = max(offsets_x) - min(offsets_x)
        var_y = max(offsets_y) - min(offsets_y)
        
        print(f"\nDécalage QCursor.pos() vs position réelle:")
        print(f"  X: min={min(offsets_x):+4d}, max={max(offsets_x):+4d}, moyenne={avg_x:+.1f}, variance={var_x}")
        print(f"  Y: min={min(offsets_y):+4d}, max={max(offsets_y):+4d}, moyenne={avg_y:+.1f}, variance={var_y}")
        
        # Décalage constant ou variable ?
        if var_x <= 10 and var_y <= 10:
            print("\n✓ Le décalage est CONSTANT.")
            print(f"\n>>> Pour corriger QCursor.pos(), utilisez un offset fixe:")
            print(f"    self.last_x = pos.x() - {int(round(avg_x))}")
            print(f"    self.last_y = pos.y() - {int(round(avg_y))}")
        else:
            print("\n⚠ Le décalage VARIE selon la position.")
            print("  → Une correction proportionnelle est nécessaire.")
            
            # Calculer les coefficients d'interpolation
            # On cherche: offset = a + b * ratio
            # Avec ratio = pos / screen_size
            
            # Pour X: mesures aux extrémités
            left_offset = self.measurements[0]["offset_qcursor"][0]  # Haut-Gauche
            right_offset = self.measurements[1]["offset_qcursor"][0]  # Haut-Droite
            
            # Pour Y:
            top_offset = self.measurements[0]["offset_qcursor"][1]  # Haut-Gauche
            bottom_offset = self.measurements[3]["offset_qcursor"][1]  # Bas-Gauche
            
            print(f"\n>>> Pour votre CursorTracker, utilisez ces corrections:")
            print(f"    # À gauche (x=0): offset = {-left_offset}")
            print(f"    # À droite (x=max): offset = {-right_offset}")
            print(f"    self.x_correction_left = {-left_offset}")
            print(f"    self.x_correction_right = {-right_offset}")
            print(f"")
            print(f"    # En haut (y=0): offset = {-top_offset}")
            print(f"    # En bas (y=max): offset = {-bottom_offset}")
            print(f"    self.y_correction_top = {-top_offset}")
            print(f"    self.y_correction_bottom = {-bottom_offset}")
        
        print("\n" + "="*60)
        print("Appuyez sur une touche pour fermer...")
        
        QTimer.singleShot(500, self.close)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            print("\nCalibration annulée.")
            self.close()


def main():
    app = QApplication(sys.argv)
    tool = CalibrationTool()
    tool.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()