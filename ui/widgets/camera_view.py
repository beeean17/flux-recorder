from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPaintEvent, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel


class CameraView(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._current_image: QImage | None = None
        self._show_recording_indicator = False
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
        self._refresh_pixmap()

    def set_recording_indicator(self, is_visible: bool) -> None:
        self._show_recording_indicator = is_visible
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_pixmap()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._show_recording_indicator:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        indicator_rect = QRect(self.width() - 110, 16, 94, 30)
        painter.setBrush(QColor("#d62828"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(indicator_rect.x() + 10, indicator_rect.center().y()), 6, 6)

        painter.setPen(QColor("#f8f9fa"))
        painter.drawText(indicator_rect.adjusted(22, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "REC")

    def _refresh_pixmap(self) -> None:
        if self._current_image is None:
            return

        scaled = QPixmap.fromImage(self._current_image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
