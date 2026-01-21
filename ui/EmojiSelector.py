from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

from utils import *

class EmojiSelector(QDialog):
    def __init__(self, emoji_list, rows=10, cols=10, parent=None):
        super().__init__(parent)
        self.emoji_list = emoji_list
        self.selected_emoji = None
        self.rows = rows
        self.cols = cols
        self.per_page = rows * cols
        self.current_page = 0

        self.setWindowTitle("Sélecteur d'Emoji")
        self.resize(600, 530)

        # Facultatif : style frameless + fond transparent
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Zone de scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.grid = QGridLayout(self.scroll_widget)

        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        # Navigation
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("←")
        self.next_button = QPushButton("→")
        self.page_label = QLabel()

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.page_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)

        self.layout.addLayout(nav_layout)

        # Appliquer le style
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 180);
                border-radius: 12px;
                color: white;
            }
            QLineEdit, QTextEdit {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
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
        """)

        self.update_grid()

    def update_grid(self):
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        start = self.current_page * self.per_page
        end = start + self.per_page
        current_emojis = self.emoji_list[start:end]

        for idx, emoji in enumerate(current_emojis):
            row = idx // self.cols
            col = idx % self.cols
            pixmap = emoji_pixmap(emoji, size=32)
            icon = QIcon(pixmap)
            btn = QPushButton()
            btn.setIcon(icon)
            btn.setIconSize(pixmap.rect().size())
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda _, e=emoji: self.emoji_selected(e))
            self.grid.addWidget(btn, row, col)

        total_pages = ((len(self.emoji_list) - 1) // self.per_page) + 1
        self.page_label.setText(f"Page {self.current_page + 1} / {total_pages}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(end < len(self.emoji_list))

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_grid()

    def next_page(self):
        if (self.current_page + 1) * self.per_page < len(self.emoji_list):
            self.current_page += 1
            self.update_grid()

    def emoji_selected(self, emoji):
        print(f"Emoji sélectionné : {emoji}")
        self.selected_emoji = emoji
        self.accept()