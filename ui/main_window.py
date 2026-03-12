from __future__ import annotations

from pathlib import Path
from platform import system

import numpy as np
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.converter import build_output_path, convert
from core.recording_state import IDLE, PAUSED, RECORDING, RecordingState
from threads.camera_thread import CameraThread
from ui.widgets.camera_view import CameraView
from ui.widgets.control_bar import ControlBar


class ConverterThread(QThread):
    conversion_finished = pyqtSignal(object)
    conversion_failed = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, input_path: Path, output_path: Path) -> None:
        super().__init__()
        self._input_path = input_path
        self._output_path = output_path

    def run(self) -> None:
        self.status_changed.emit("Converting video...")
        try:
            converted_path = convert(self._input_path, self._output_path)
        except RuntimeError as exc:
            self.conversion_failed.emit(str(exc))
            return

        self.conversion_finished.emit(converted_path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._camera_view = CameraView()
        self._control_bar = ControlBar()
        self._camera_thread = CameraThread()
        self._converter_thread: ConverterThread | None = None
        self._recording_state: RecordingState = IDLE

        self.setWindowTitle("flux-recorder")
        self.resize(960, 720)

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._camera_view, stretch=1)
        layout.addWidget(self._control_bar)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self._control_bar.start_requested.connect(self.on_start_requested)
        self._control_bar.pause_requested.connect(self.on_pause_requested)
        self._control_bar.stop_requested.connect(self.on_stop_requested)
        self._control_bar.convert_requested.connect(self.on_convert_requested)

        self._camera_thread.frame_ready.connect(self.on_frame)
        self._camera_thread.camera_error.connect(self.on_camera_error)
        self._camera_thread.recording_changed.connect(self.on_recording_changed)
        self._camera_thread.start()

    def on_frame(self, frame_rgb: np.ndarray) -> None:
        self._camera_view.update_frame(frame_rgb)

    def on_start_requested(self) -> None:
        if self._recording_state == PAUSED:
            self._camera_thread.resume_recording()
            return
        if self._recording_state != IDLE:
            return

        output_path = self._build_recording_path()
        self._camera_thread.start_recording(output_path)

    def on_pause_requested(self) -> None:
        if self._recording_state == RECORDING:
            self._camera_thread.pause_recording()

    def on_stop_requested(self) -> None:
        if self._recording_state != IDLE:
            self._camera_thread.stop_recording()

    def on_recording_changed(self, state: RecordingState, message: str) -> None:
        self._recording_state = state
        self._camera_view.set_recording_indicator(state)
        self._control_bar.set_recording_state(state)
        default_message = "Preview mode" if state == IDLE else "Recording..."
        self._control_bar.set_status(message if message else default_message)

    def on_camera_error(self, message: str) -> None:
        self._recording_state = IDLE
        self._camera_view.set_recording_indicator(IDLE)
        self._control_bar.set_recording_state(IDLE)
        self._control_bar.set_status(message)
        QMessageBox.critical(self, "Camera Error", message)

    def on_convert_requested(self, target_format: str) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            return

        source_path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select a video to convert",
            str(self._default_video_directory()),
            "Video Files (*.mp4 *.avi *.mov *.mkv)",
        )
        if not source_path_str:
            self._control_bar.set_status("Conversion cancelled.")
            return

        input_path = Path(source_path_str)
        output_path = build_output_path(input_path, target_format)
        self._converter_thread = ConverterThread(input_path, output_path)
        self._converter_thread.status_changed.connect(self._control_bar.set_status)
        self._converter_thread.conversion_finished.connect(self.on_conversion_finished)
        self._converter_thread.conversion_failed.connect(self.on_conversion_failed)
        self._converter_thread.finished.connect(self.on_conversion_thread_finished)

        self._control_bar.set_conversion_enabled(False)
        self._converter_thread.start()

    def on_conversion_finished(self, output_path: Path) -> None:
        self._control_bar.set_status(f"Converted file saved to {output_path}")
        QMessageBox.information(self, "Conversion Complete", f"Saved converted file:\n{output_path}")

    def on_conversion_failed(self, message: str) -> None:
        self._control_bar.set_status("Conversion failed.")
        QMessageBox.critical(self, "Conversion Error", message)

    def on_conversion_thread_finished(self) -> None:
        self._control_bar.set_conversion_enabled(True)
        self._converter_thread = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            event.ignore()
            return

        if event.key() == Qt.Key.Key_Space:
            self.on_start_requested()
            event.accept()
            return
        if event.key() == Qt.Key.Key_P:
            self.on_pause_requested()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.on_stop_requested()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            self._converter_thread.wait()
        if self._camera_thread.isRunning():
            self._camera_thread.stop()
        event.accept()

    def _build_recording_path(self) -> Path:
        timestamp = self._timestamp_string()
        return self._default_video_directory() / f"recording_{timestamp}.avi"

    def _default_video_directory(self) -> Path:
        home = Path.home()
        return home / ("Videos" if system() == "Windows" else "Movies")

    def _timestamp_string(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")
