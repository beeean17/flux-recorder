from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from core.recording_state import IDLE, PAUSED, RECORDING, STARTING, RecordingState


class ControlBar(QWidget):
    start_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._start_button = QPushButton("Start Recording (Space)")
        self._pause_button = QPushButton("Pause Recording (P)")
        self._stop_button = QPushButton("Stop Recording (Enter)")
        self._status_label = QLabel("Preview mode")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._start_button)
        layout.addWidget(self._pause_button)
        layout.addWidget(self._stop_button)
        layout.addStretch(1)
        layout.addWidget(self._status_label, stretch=1)
        self.setLayout(layout)

        self._start_button.clicked.connect(self.start_requested.emit)
        self._pause_button.clicked.connect(self.pause_requested.emit)
        self._stop_button.clicked.connect(self.stop_requested.emit)
        self.set_recording_state(IDLE)

    def set_recording_state(self, state: RecordingState) -> None:
        is_idle = state == IDLE
        is_starting = state == STARTING
        is_recording = state == RECORDING
        is_paused = state == PAUSED

        self._start_button.setEnabled(is_idle or is_paused)
        self._start_button.setText("Resume Recording (Space)" if is_paused else "Start Recording (Space)")
        self._pause_button.setEnabled(is_recording)
        self._stop_button.setEnabled(not is_idle)

        if is_recording:
            self._status_label.setText("Recording...")
        elif is_paused:
            self._status_label.setText("Recording paused.")
        elif is_starting:
            self._status_label.setText("Preparing recording...")

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)
