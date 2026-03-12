from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from core.converter import SUPPORTED_FORMATS


class ControlBar(QWidget):
    record_requested = pyqtSignal()
    convert_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._record_button = QPushButton("Start Recording (Space)")
        self._convert_button = QPushButton("Convert")
        self._format_combo = QComboBox()
        self._status_label = QLabel("Preview mode")

        self._format_combo.addItems(SUPPORTED_FORMATS)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._record_button)
        layout.addWidget(QLabel("Output format"))
        layout.addWidget(self._format_combo)
        layout.addWidget(self._convert_button)
        layout.addStretch(1)
        layout.addWidget(self._status_label, stretch=1)
        self.setLayout(layout)

        self._record_button.clicked.connect(self.record_requested.emit)
        self._convert_button.clicked.connect(self._emit_convert_requested)

    def set_recording(self, is_recording: bool) -> None:
        if is_recording:
            self._record_button.setText("Stop Recording (Space)")
            self._status_label.setText("Recording...")
        else:
            self._record_button.setText("Start Recording (Space)")

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_conversion_enabled(self, enabled: bool) -> None:
        self._convert_button.setEnabled(enabled)
        self._format_combo.setEnabled(enabled)

    def _emit_convert_requested(self) -> None:
        self.convert_requested.emit(self._format_combo.currentText())
