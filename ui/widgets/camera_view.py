from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPaintEvent, QPainter, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel

from core.recording_state import IDLE, RecordingState


class CameraView(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._current_image: QImage | None = None
        self._recording_state: RecordingState = IDLE
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: #111; border-radius: 8px;")
        self.setText("Camera preview is starting...")

    def update_frame(self, frame_rgb: np.ndarray) -> None:
        height, width, channels = frame_rgb.shape
        bytes_per_line = channels * width
        image = QImage(
            frame_rgb.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()
        self._current_image = image
        self.update()

    def set_recording_indicator(self, state: RecordingState) -> None:
        self._recording_state = state
        self.update()

    def save_snapshot(self, path: str | Path) -> bool:
        if self._current_image is None:
            return False
        return self._current_image.save(str(path))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))

        if self._current_image is None:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
            return

        scaled = QPixmap.fromImage(self._current_image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
