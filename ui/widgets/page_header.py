from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class PageHeader(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, title: str) -> None:
        super().__init__()
        back_button = QPushButton("Back to Menu (Esc)")
        back_button.clicked.connect(self.back_requested.emit)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 700;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(back_button)
        layout.addWidget(title_label)
        layout.addStretch(1)
        self.setLayout(layout)
