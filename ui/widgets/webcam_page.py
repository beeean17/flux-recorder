from __future__ import annotations

from collections import deque
from pathlib import Path
from platform import system
from time import perf_counter

import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.recording_state import IDLE, PAUSED, RECORDING, STARTING, RecordingState
from ui.widgets.camera_view import CameraView

FRAME_INTERVAL_WINDOW = 120
MIN_RECORDING_FPS = 5.0
MAX_RECORDING_FPS = 60.0
DEFAULT_CAMERA_FPS = 30.0
COMMON_CAMERA_FPS = (15.0, 23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)
MAX_CAMERA_SCAN_INDEX = 5


class WebcamPage(QWidget):
    back_requested = pyqtSignal()
    browse_save_path_requested = pyqtSignal()
    recording_saved = pyqtSignal(str)
    snapshot_saved = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._recording_state: RecordingState = IDLE
        self._camera_view = CameraView()
        self._camera_view.setMinimumSize(900, 620)
        self._camera_view.setStyleSheet("background: #000000; border: none;")

        self._save_directory = Path.home()
        self._cv2 = None
        self._camera_capture = None
        self._camera_index = 0
        self._available_camera_indices: list[int] = []
        self._is_populating_video_devices = False
        self._preview_timer: QTimer | None = None
        self._recorder = None
        self._pending_recording_path: Path | None = None
        self._frame_intervals: deque[float] = deque(maxlen=FRAME_INTERVAL_WINDOW)
        self._last_frame_timestamp: float | None = None
        self._video_device_combo: QComboBox | None = None

        self._preview_stats_badge = QLabel("Live preview")
        self._preview_stats_badge.setStyleSheet(self._badge_style("#0f172a", "#94a3b8"))

        self._recording_badge = QLabel("REC")
        self._recording_badge.setStyleSheet(self._badge_style("#dc2626", "white", bold=True))
        self._recording_badge.hide()

        self._flash_overlay = QFrame()
        self._flash_overlay.setStyleSheet("background: rgba(255, 255, 255, 0.85); border: none;")
        self._flash_overlay.hide()

        self._save_path_input = QLineEdit()
        self._save_path_input.setReadOnly(True)
        self._save_path_input.setStyleSheet(
            """
            QLineEdit {
                background: #020617;
                color: #64748b;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 11px;
            }
            """
        )

        self._status_label = QLabel("Preview mode")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #64748b; font-size: 12px;")

        self._recent_capture_name = QLabel("No capture yet")
        self._recent_capture_name.setStyleSheet("color: #cbd5e1; font-size: 13px;")

        self._recent_capture_thumb = QLabel("IMG")
        self._recent_capture_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_capture_thumb.setFixedSize(52, 52)
        self._recent_capture_thumb.setStyleSheet(
            """
            QLabel {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }
            """
        )

        self._photo_button = self._build_capture_button("PHOTO", "#ffffff", "#0f172a", large=False)
        self._record_button = self._build_capture_button("REC", "#dc2626", "white", large=True)
        self._pause_button = QPushButton("Pause")
        self._pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_button.setFixedHeight(40)
        self._pause_button.setStyleSheet(
            """
            QPushButton {
                background: #111827;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: #475569;
                color: white;
            }
            QPushButton:disabled {
                color: #475569;
                border-color: #1e293b;
            }
            """
        )
        self._pause_button.clicked.connect(self.pause_recording)
        self._photo_button.clicked.connect(self.capture_photo)
        self._record_button.clicked.connect(self._on_record_button_clicked)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(self._build_main_area(), 1)
        root_layout.addWidget(self._build_footer())
        self.setLayout(root_layout)
        self.setStyleSheet("background: #0f172a;")
        self.set_save_path(self._save_directory)
        self.set_recording_state(IDLE)

    @property
    def recording_state(self) -> RecordingState:
        return self._recording_state

    def start_preview(self) -> None:
        try:
            import cv2
            from core.recorder import Recorder
        except ModuleNotFoundError as exc:
            self.set_status(f"Webcam backend is unavailable. Missing dependency: {exc.name}")
            return

        if self._cv2 is None:
            self._cv2 = cv2
        if self._recorder is None:
            self._recorder = Recorder()
        if self._preview_timer is None:
            self._preview_timer = QTimer(self)
            self._preview_timer.timeout.connect(self._poll_frame)

        self._available_camera_indices = self._discover_camera_devices()
        self._sync_video_device_combo()

        if not self._available_camera_indices:
            self._release_camera()
            self._camera_view.setText("No camera devices detected.")
            self.set_status("No camera devices detected.")
            return

        if self._camera_index not in self._available_camera_indices:
            self._camera_index = self._available_camera_indices[0]
            self._sync_video_device_combo()

        if not self._open_camera(self._camera_index):
            self._camera_view.setText(f"Unable to open camera {self._camera_index}.")
            self.set_status(f"Unable to open camera device {self._camera_index}.")
            return

        self.set_status(f"Preview mode: camera {self._camera_index}")

    def stop_preview(self) -> None:
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer.deleteLater()
        self._preview_timer = None

        if self._recorder is not None:
            saved_path = self._recorder.stop()
            if saved_path is not None and self._recording_state != IDLE:
                self._handle_saved_recording(saved_path)
        self._recorder = None

        self._release_camera()
        self._cv2 = None
        self._pending_recording_path = None
        self._last_frame_timestamp = None
        self._frame_intervals.clear()
        self._available_camera_indices = []
        self._sync_video_device_combo()
        self.set_recording_state(IDLE)

    def start_or_resume_recording(self) -> None:
        if self._camera_capture is None or self._recorder is None:
            self.set_status("Camera preview is unavailable. Check webcam access.")
            return

        if self._recording_state == PAUSED:
            output_path = self._recorder.output_path
            self.set_recording_state(RECORDING)
            self.set_status(f"Recording to {output_path}" if output_path is not None else "Recording resumed.")
            return

        if self._recording_state != IDLE:
            return

        self._pending_recording_path = self._build_recording_path()
        self.set_recording_state(STARTING)
        self.set_status(f"Preparing recording: {self._pending_recording_path.name}")

    def pause_recording(self) -> None:
        if self._recording_state != RECORDING or self._recorder is None:
            return

        output_path = self._recorder.output_path
        self.set_recording_state(PAUSED)
        self.set_status(f"Recording paused: {output_path}" if output_path is not None else "Recording paused.")

    def stop_recording(self) -> None:
        if self._recording_state == IDLE or self._recorder is None:
            return

        was_starting = self._pending_recording_path is not None and not self._recorder.is_recording
        self._pending_recording_path = None
        saved_path = self._recorder.stop()
        if saved_path is not None:
            self._handle_saved_recording(saved_path)
        elif was_starting:
            self.set_recording_state(IDLE)
            self.set_status("Recording cancelled.")
        else:
            self.set_recording_state(IDLE)
            self.set_status("Recording stopped.")

    def capture_photo(self) -> None:
        output_path = self._build_snapshot_path()
        if not self._camera_view.save_snapshot(output_path):
            self.set_status("Snapshot unavailable. Wait for the camera preview.")
            return

        self.flash_capture()
        self.set_recent_capture(output_path.name)
        self.set_status(f"Saved photo to {output_path}")
        self.snapshot_saved.emit(str(output_path))

    def update_frame(self, frame_rgb: np.ndarray) -> None:
        self._camera_view.update_frame(frame_rgb)
        height, width, _ = frame_rgb.shape
        self._preview_stats_badge.setText(f"{width} x {height} live")

    def set_recording_state(self, state: RecordingState) -> None:
        self._recording_state = state
        is_starting = state == STARTING
        is_recording = state == RECORDING
        is_paused = state == PAUSED

        self._pause_button.setEnabled(is_recording)
        self._record_button.setEnabled(not is_starting)
        self._recording_badge.setVisible(is_recording or is_paused)
        if is_recording:
            self._recording_badge.setText("REC")
            self._record_button.setText("STOP")
            self._record_button.setStyleSheet(self._capture_button_style("#dc2626", "white", large=True))
        elif is_paused:
            self._recording_badge.setText("PAUSED")
            self._record_button.setText("RESUME")
            self._record_button.setStyleSheet(self._capture_button_style("#2563eb", "white", large=True))
        elif is_starting:
            self._record_button.setText("WAIT")
            self._record_button.setStyleSheet(self._capture_button_style("#475569", "#e2e8f0", large=True))
        else:
            self._record_button.setText("REC")
            self._recording_badge.hide()
            self._record_button.setStyleSheet(self._capture_button_style("#dc2626", "white", large=True))

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_save_path(self, path: Path) -> None:
        self._save_directory = path
        self._save_path_input.setText(str(path))

    def set_recent_capture(self, filename: str) -> None:
        self._recent_capture_name.setText(filename)
        extension = Path(filename).suffix.lower().removeprefix(".") or "FILE"
        self._recent_capture_thumb.setText(extension[:4].upper())

    def flash_capture(self) -> None:
        self._flash_overlay.show()
        self._flash_overlay.raise_()
        QTimer.singleShot(120, self._flash_overlay.hide)

    def _build_main_area(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_settings_sidebar())
        layout.addWidget(self._build_preview_panel(), 1)
        return layout

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet("background: #000000; border-left: 1px solid #1e293b; border-bottom: 1px solid #1e293b;")

        stack = QWidget()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        grid.addWidget(self._camera_view, 0, 0)

        overlay = QWidget()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(18, 18, 18, 18)
        overlay_layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)
        top_row.addWidget(self._preview_stats_badge, 0, Qt.AlignmentFlag.AlignLeft)
        top_row.addWidget(self._recording_badge, 0, Qt.AlignmentFlag.AlignLeft)
        top_row.addStretch(1)

        overlay_layout.addLayout(top_row)
        overlay_layout.addStretch(1)
        overlay.setLayout(overlay_layout)

        grid.addWidget(overlay, 0, 0)
        grid.addWidget(self._flash_overlay, 0, 0)
        stack.setLayout(grid)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(stack, 1)
        panel.setLayout(layout)
        return panel

    def _build_settings_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background: #0f172a;")

        back_button = QPushButton("Back to Menu")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setStyleSheet(
            """
            QPushButton {
                background: #111827;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: #334155;
            }
            """
        )

        header_title = QLabel("Camera Settings")
        header_title.setStyleSheet("color: white; font-size: 20px; font-weight: 700;")
        header_subtitle = QLabel("Configure device and quality")
        header_subtitle.setStyleSheet("color: #64748b; font-size: 12px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(20)
        layout.addWidget(back_button, 0)
        layout.addWidget(header_title)
        layout.addWidget(header_subtitle)
        layout.addWidget(self._build_video_device_group())
        layout.addWidget(self._build_select_group("Resolution", ["1920 x 1080 (16:9)", "1280 x 720 (16:9)", "640 x 480 (4:3)"]))
        layout.addWidget(self._build_select_group("Frame Rate", ["60 FPS", "30 FPS", "24 FPS"]))
        layout.addWidget(self._build_select_group("Microphone", ["Default - System Mic", "Yeti Stereo Microphone", "Webcam Internal Mic", "None (Mute)"]))

        vu_meter = QFrame()
        vu_meter.setStyleSheet("background: #1e293b; border-radius: 7px;")
        vu_layout = QHBoxLayout()
        vu_layout.setContentsMargins(3, 3, 3, 3)
        vu_layout.setSpacing(3)
        for width, color in ((70, "#22c55e"), (52, "#22c55e"), (110, "#334155")):
            bar = QFrame()
            bar.setFixedHeight(8)
            bar.setFixedWidth(width)
            bar.setStyleSheet(f"background: {color}; border-radius: 4px;")
            vu_layout.addWidget(bar)
        vu_meter.setLayout(vu_layout)
        layout.addWidget(vu_meter)

        storage_title = QLabel("Save Path")
        storage_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        browse_button = QPushButton("Browse")
        browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_button.clicked.connect(self.browse_save_path_requested.emit)
        browse_button.setFixedWidth(76)
        browse_button.setStyleSheet(
            """
            QPushButton {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px 0;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334155;
            }
            """
        )

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(8)
        path_row.addWidget(self._save_path_input, 1)
        path_row.addWidget(browse_button)

        layout.addStretch(1)
        layout.addWidget(storage_title)
        layout.addLayout(path_row)
        layout.addWidget(self._status_label)
        sidebar.setLayout(layout)
        return sidebar

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFixedHeight(104)
        footer.setStyleSheet("background: #020617; border-top: 1px solid #1e293b;")

        recent_title = QLabel("Recent Capture")
        recent_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase;")

        recent_text_layout = QVBoxLayout()
        recent_text_layout.setContentsMargins(0, 0, 0, 0)
        recent_text_layout.setSpacing(2)
        recent_text_layout.addWidget(recent_title)
        recent_text_layout.addWidget(self._recent_capture_name)

        recent_layout = QHBoxLayout()
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(12)
        recent_layout.addWidget(self._recent_capture_thumb)
        recent_layout.addLayout(recent_text_layout)
        recent_layout.addStretch(1)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(18)
        controls_layout.addWidget(self._photo_button)
        controls_layout.addWidget(self._record_button)
        controls_layout.addWidget(self._pause_button)

        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        for label in ("Flash", "Grid", "Settings"):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(38)
            button.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    color: #94a3b8;
                    border: 1px solid #1e293b;
                    border-radius: 10px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    color: white;
                    border-color: #334155;
                }
                """
            )
            right_layout.addWidget(button)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(22)
        layout.addLayout(recent_layout, 1)
        layout.addLayout(controls_layout)
        layout.addStretch(1)
        layout.addLayout(right_layout)
        footer.setLayout(layout)
        return footer

    def _build_select_group(self, label: str, options: list[str]) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        text_label = QLabel(label)
        text_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase;")

        combo = QComboBox()
        combo.addItems(options)
        combo.setStyleSheet(self._combo_style())

        layout.addWidget(text_label)
        layout.addWidget(combo)
        wrapper.setLayout(layout)
        return wrapper

    def _build_video_device_group(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        text_label = QLabel("Video Device")
        text_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase;")

        self._video_device_combo = QComboBox()
        self._video_device_combo.setStyleSheet(self._combo_style())
        self._video_device_combo.currentIndexChanged.connect(self._on_video_device_changed)

        layout.addWidget(text_label)
        layout.addWidget(self._video_device_combo)
        wrapper.setLayout(layout)
        self._sync_video_device_combo()
        return wrapper

    def _build_capture_button(self, label: str, background: str, color: str, large: bool) -> QPushButton:
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(90 if large else 72, 90 if large else 72)
        button.setStyleSheet(self._capture_button_style(background, color, large))
        return button

    def _capture_button_style(self, background: str, color: str, large: bool) -> str:
        size = "18px" if large else "12px"
        radius = "45px" if large else "36px"
        return (
            "QPushButton {"
            f"background: {background};"
            f"color: {color};"
            "border: 4px solid #020617;"
            f"border-radius: {radius};"
            f"font-size: {size};"
            "font-weight: 800;"
            "}"
            "QPushButton:hover {"
            "border-color: #0f172a;"
            "}"
        )

    def _badge_style(self, background: str, color: str, bold: bool = False) -> str:
        weight = "700" if bold else "600"
        return (
            "QLabel {"
            f"background: {background};"
            f"color: {color};"
            "border: 1px solid rgba(148, 163, 184, 0.25);"
            "border-radius: 8px;"
            "padding: 6px 10px;"
            "font-size: 11px;"
            f"font-weight: {weight};"
            "}"
        )

    def _combo_style(self) -> str:
        return (
            "QComboBox {"
            "background: #1e293b;"
            "color: #e2e8f0;"
            "border: 1px solid #334155;"
            "border-radius: 10px;"
            "padding: 10px 12px;"
            "font-size: 13px;"
            "}"
            "QComboBox::drop-down {"
            "border: none;"
            "width: 24px;"
            "}"
        )

    def _on_record_button_clicked(self) -> None:
        if self._recording_state in (IDLE, PAUSED):
            self.start_or_resume_recording()
        elif self._recording_state == RECORDING:
            self.stop_recording()

    def _on_video_device_changed(self, _combo_index: int) -> None:
        if self._is_populating_video_devices or self._video_device_combo is None:
            return

        selected_index = self._video_device_combo.currentData()
        if not isinstance(selected_index, int) or selected_index < 0:
            return

        previous_index = self._camera_index
        if selected_index == self._camera_index and self._camera_capture is not None:
            return

        if self._recording_state != IDLE:
            self.set_status("Stop recording before switching cameras.")
            self._sync_video_device_combo()
            return

        self._camera_index = selected_index
        if not self._open_camera(selected_index):
            self._camera_index = previous_index
            self._sync_video_device_combo()
            self.set_status(f"Unable to open camera device {selected_index}.")
            return

        self.set_status(f"Preview mode: camera {selected_index}")

    def _poll_frame(self) -> None:
        if self._camera_capture is None or self._cv2 is None:
            return

        ok, frame_bgr = self._camera_capture.read()
        if not ok or frame_bgr is None:
            self.set_status("Failed to read a frame from the camera.")
            self._release_camera()
            return

        height, width = frame_bgr.shape[:2]
        size = (width, height)
        fallback_fps = self._camera_fps()

        now = perf_counter()
        if self._last_frame_timestamp is not None:
            interval = now - self._last_frame_timestamp
            if interval > 0:
                self._frame_intervals.append(interval)
        self._last_frame_timestamp = now

        if self._pending_recording_path is not None and self._recorder is not None:
            recording_fps = self._estimated_capture_fps(fallback_fps)
            try:
                self._recorder.start(
                    output_path=self._pending_recording_path,
                    fps=recording_fps,
                    size=size,
                )
            except RuntimeError as exc:
                self._pending_recording_path = None
                self.set_status(str(exc))
                self.set_recording_state(IDLE)
                return

            output_path = self._pending_recording_path
            self._pending_recording_path = None
            self.set_recording_state(RECORDING)
            self.set_status(f"Recording to {output_path}")

        if self._recording_state == RECORDING and self._recorder is not None:
            self._recorder.write(frame_bgr)

        frame_rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        self.update_frame(frame_rgb)

    def _discover_camera_devices(self) -> list[int]:
        if self._cv2 is None:
            return []

        available_indices: list[int] = []
        for device_index in range(MAX_CAMERA_SCAN_INDEX + 1):
            capture = self._create_video_capture(device_index)
            if capture is None:
                continue

            try:
                if not capture.isOpened():
                    continue
                ok, frame_bgr = capture.read()
                if ok and frame_bgr is not None:
                    available_indices.append(device_index)
            finally:
                capture.release()

        return available_indices

    def _create_video_capture(self, device_index: int):
        if self._cv2 is None:
            return None

        backend = self._preferred_capture_backend()
        if backend is None:
            return self._cv2.VideoCapture(device_index)
        return self._cv2.VideoCapture(device_index, backend)

    def _preferred_capture_backend(self):
        if self._cv2 is None:
            return None

        platform_name = system()
        if platform_name == "Darwin":
            return getattr(self._cv2, "CAP_AVFOUNDATION", None)
        if platform_name == "Windows":
            return getattr(self._cv2, "CAP_DSHOW", None)
        return None

    def _open_camera(self, device_index: int) -> bool:
        self._release_camera()

        capture = self._create_video_capture(device_index)
        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            return False

        self._camera_capture = capture
        self._camera_index = device_index
        self._last_frame_timestamp = None
        self._frame_intervals.clear()

        if self._preview_timer is not None and not self._preview_timer.isActive():
            self._preview_timer.start(16)
        return True

    def _release_camera(self) -> None:
        if self._preview_timer is not None and self._preview_timer.isActive():
            self._preview_timer.stop()
        if self._camera_capture is not None:
            self._camera_capture.release()
        self._camera_capture = None

    def _sync_video_device_combo(self) -> None:
        if self._video_device_combo is None:
            return

        self._is_populating_video_devices = True
        self._video_device_combo.clear()

        if not self._available_camera_indices:
            self._video_device_combo.addItem("No camera detected", -1)
            self._video_device_combo.setEnabled(False)
        else:
            for device_index in self._available_camera_indices:
                self._video_device_combo.addItem(f"Camera {device_index}", device_index)
            self._video_device_combo.setEnabled(True)

            selected_position = self._video_device_combo.findData(self._camera_index)
            if selected_position < 0:
                selected_position = 0
            self._video_device_combo.setCurrentIndex(selected_position)

        self._is_populating_video_devices = False

    def _handle_saved_recording(self, saved_path: Path) -> None:
        self.set_recent_capture(saved_path.name)
        self.set_recording_state(IDLE)
        self.set_status(f"Saved recording to {saved_path}")
        self.recording_saved.emit(str(saved_path))

    def _build_recording_path(self) -> Path:
        return self._save_directory / f"recording_{self._timestamp_string()}.avi"

    def _build_snapshot_path(self) -> Path:
        return self._save_directory / f"snapshot_{self._timestamp_string()}.png"

    def _timestamp_string(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _estimated_capture_fps(self, fallback_fps: float) -> float:
        if not self._frame_intervals:
            return fallback_fps

        sorted_intervals = sorted(self._frame_intervals)
        trim = max(1, len(sorted_intervals) // 10) if len(sorted_intervals) >= 10 else 0
        stable_intervals = sorted_intervals[trim:-trim] if trim else sorted_intervals
        average_interval = sum(stable_intervals) / len(stable_intervals)
        if average_interval <= 0:
            return fallback_fps

        measured_fps = 1.0 / average_interval
        return max(MIN_RECORDING_FPS, min(MAX_RECORDING_FPS, round(measured_fps, 2)))

    def _camera_fps(self) -> float:
        if self._camera_capture is None or self._cv2 is None:
            return DEFAULT_CAMERA_FPS

        fps = float(self._camera_capture.get(self._cv2.CAP_PROP_FPS))
        return self._normalize_fps(fps)

    def _normalize_fps(self, fps: float) -> float:
        if fps <= 0 or fps > 120:
            return DEFAULT_CAMERA_FPS

        nearest_common_fps = min(COMMON_CAMERA_FPS, key=lambda candidate: abs(candidate - fps))
        if abs(nearest_common_fps - fps) / nearest_common_fps <= 0.12:
            return nearest_common_fps

        return round(fps, 2)
