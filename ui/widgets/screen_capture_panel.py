from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ScreenCapturePanel(QWidget):
    screen_record_requested = pyqtSignal()
    screenshot_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._status_label = QLabel("Screen recording and capture will be wired in next.")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #4b5563;")

        title_label = QLabel("Screen Tools")
        title_label.setStyleSheet("font-size: 24px; font-weight: 700;")

        description_label = QLabel(
            "This mode is reserved for screen recording and screenshot capture."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #6b7280;")

        record_button = QPushButton("Record Screen")
        capture_button = QPushButton("Capture Screenshot")
        record_button.clicked.connect(self.screen_record_requested.emit)
        capture_button.clicked.connect(self.screenshot_requested.emit)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(record_button)
        layout.addWidget(capture_button)
        layout.addStretch(1)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)
