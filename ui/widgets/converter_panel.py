from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from core.converter import SUPPORTED_FORMATS


class ConverterPanel(QWidget):
    convert_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._format_combo = QComboBox()
        self._convert_button = QPushButton("Choose File and Convert")
        self._status_label = QLabel("Ready to convert a media file.")

        self._format_combo.addItems(SUPPORTED_FORMATS)
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #4b5563;")

        title_label = QLabel("Convert Images and Videos")
        title_label.setStyleSheet("font-size: 24px; font-weight: 700;")

        description_label = QLabel(
            "Select a source file, then export it to the format shown below."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #6b7280;")

        self._convert_button.clicked.connect(self._emit_convert_requested)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(self._format_combo)
        layout.addWidget(self._convert_button)
        layout.addStretch(1)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_conversion_enabled(self, enabled: bool) -> None:
        self._format_combo.setEnabled(enabled)
        self._convert_button.setEnabled(enabled)

    def _emit_convert_requested(self) -> None:
        self.convert_requested.emit(self._format_combo.currentText())
