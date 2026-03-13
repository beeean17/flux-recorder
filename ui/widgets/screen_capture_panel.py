from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.recording_state import IDLE, PAUSED, RECORDING, RecordingState


BASE = "#120f1d"
SIDEBAR = "#171325"
SURFACE = "#0b0913"
SURFACE_ALT = "#211a35"
ACCENT = "#8b5cf6"
TEXT_PRIMARY = "#f5f3ff"
TEXT_SECONDARY = "#a79bbb"
BORDER = "#34294b"
DEFAULT_CAPTURE_FPS = 30


class ScreenCapturePanel(QWidget):
    back_requested = pyqtSignal()
    browse_output_requested = pyqtSignal()
    recording_saved = pyqtSignal(str)
    snapshot_saved = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("screen_capture_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._save_directory = Path.home()
        self._cv2 = None
        self._recorder = None
        self._preview_timer: QTimer | None = None
        self._recording_state: RecordingState = IDLE
        self._current_frame_bgr: np.ndarray | None = None
        self._capture_mode = "full_screen"
        self._recording_started_at: float | None = None
        self._elapsed_before_pause = 0.0

        self._capture_tabs = QButtonGroup(self)
        self._capture_tabs.setExclusive(True)
        self._frame_rate_buttons = QButtonGroup(self)
        self._frame_rate_buttons.setExclusive(True)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self._status_label.setWordWrap(True)

        self._recent_capture_name = QLabel("No capture yet")
        self._recent_capture_name.setStyleSheet("color: #cbd5e1; font-size: 13px;")

        self._recent_capture_thumb = QLabel("CAP")
        self._recent_capture_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_capture_thumb.setFixedSize(52, 52)
        self._recent_capture_thumb.setStyleSheet(
            """
            QLabel {
                background: #241d38;
                color: #f5f3ff;
                border: 1px solid #3d3159;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }
            """
        )

        self._path_input = QLineEdit()
        self._path_input.setReadOnly(True)
        self._path_input.setStyleSheet(self._path_input_style())

        self._resolution_combo = QComboBox()
        self._resolution_combo.addItems(
            ["1920 x 1080 (1080p)", "1280 x 720 (720p)", "2560 x 1440 (2K)", "3840 x 2160 (4K)"]
        )
        self._resolution_combo.setStyleSheet(self._combo_style())

        self._system_audio_switch = self._build_switch(True)
        self._external_mic_switch = self._build_switch(False)

        self._timer_label = QLabel("00:00:00")
        self._timer_label.setStyleSheet(f"color: {ACCENT}; font-size: 24px; font-weight: 800;")

        self._record_button = QPushButton("Record")
        self._snapshot_button = QPushButton("Snapshot")
        self._pause_button = QPushButton("Pause")
        self._stop_button = QPushButton("Stop")

        self._record_button.clicked.connect(self.start_or_resume_recording)
        self._snapshot_button.clicked.connect(self.capture_snapshot)
        self._pause_button.clicked.connect(self.pause_recording)
        self._stop_button.clicked.connect(self.stop_recording)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._build_body(), 1)
        root.addWidget(self._build_footer())
        self.setLayout(root)
        self.setStyleSheet(
            f"""
            QWidget#screen_capture_panel {{
                background: {BASE};
            }}
            """
        )
        self.set_output_path(self._save_directory)
        self._set_recording_state(IDLE)

    @property
    def recording_state(self) -> RecordingState:
        return self._recording_state

    def start_preview(self) -> None:
        if self._cv2 is None or self._recorder is None:
            try:
                import cv2
                from core.recorder import Recorder
            except ModuleNotFoundError as exc:
                self.set_status(f"Screen capture backend is unavailable. Missing dependency: {exc.name}")
                return
            self._cv2 = cv2
            self._recorder = Recorder()

        if self._preview_timer is None:
            self._preview_timer = QTimer(self)
            self._preview_timer.timeout.connect(self._poll_frame)

        self._restart_preview_timer()
        self._poll_frame()
        self.set_status("Capture backend ready.")

    def stop_preview(self) -> None:
        if self._preview_timer is not None:
            self._preview_timer.stop()
            self._preview_timer.deleteLater()
        self._preview_timer = None

        if self._recorder is not None:
            saved_path = self._recorder.stop()
            if saved_path is not None and self._recording_state != IDLE:
                self.recording_saved.emit(str(saved_path))

        self._recorder = None
        self._cv2 = None
        self._current_frame_bgr = None
        self._recording_started_at = None
        self._elapsed_before_pause = 0.0
        self._update_duration_display(0.0)
        self._set_recording_state(IDLE)

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_output_path(self, path: Path) -> None:
        self._save_directory = path
        self._path_input.setText(str(path))

    def set_recent_capture(self, filename: str) -> None:
        self._recent_capture_name.setText(filename)
        extension = Path(filename).suffix.lower().removeprefix(".") or "FILE"
        self._recent_capture_thumb.setText(extension[:4].upper())

    def start_or_resume_recording(self) -> None:
        if self._preview_timer is None:
            self.start_preview()
        if self._cv2 is None or self._recorder is None:
            return

        if self._recording_state == PAUSED:
            self._recording_started_at = perf_counter()
            self._set_recording_state(RECORDING)
            self.set_status("Recording resumed.")
            return

        if self._recording_state == RECORDING:
            return

        frame_bgr = self._current_frame_bgr.copy() if self._current_frame_bgr is not None else self._grab_screen_frame()
        if frame_bgr is None:
            self.set_status("Unable to capture a screen frame.")
            return

        output_path = self._build_recording_path()
        height, width = frame_bgr.shape[:2]
        try:
            self._recorder.start(output_path=output_path, fps=float(self._selected_fps()), size=(width, height))
        except RuntimeError as exc:
            self.set_status(str(exc))
            return

        self._elapsed_before_pause = 0.0
        self._recording_started_at = perf_counter()
        self._set_recording_state(RECORDING)
        self.set_status(f"Recording to {output_path}")

    def pause_recording(self) -> None:
        if self._recording_state != RECORDING:
            return

        if self._recording_started_at is not None:
            self._elapsed_before_pause += perf_counter() - self._recording_started_at
        self._recording_started_at = None
        self._set_recording_state(PAUSED)
        self.set_status("Recording paused.")

    def stop_recording(self) -> None:
        if self._recording_state == IDLE or self._recorder is None:
            return

        if self._recording_state == RECORDING and self._recording_started_at is not None:
            self._elapsed_before_pause += perf_counter() - self._recording_started_at

        self._recording_started_at = None
        saved_path = self._recorder.stop()
        self._elapsed_before_pause = 0.0
        self._update_duration_display(0.0)
        self._set_recording_state(IDLE)

        if saved_path is not None:
            self.set_recent_capture(saved_path.name)
            self.set_status(f"Saved screen recording to {saved_path}")
            self.recording_saved.emit(str(saved_path))
        else:
            self.set_status("Recording stopped.")

    def capture_snapshot(self) -> None:
        if self._cv2 is None:
            self.start_preview()
        frame_bgr = self._current_frame_bgr.copy() if self._current_frame_bgr is not None else self._grab_screen_frame()
        if frame_bgr is None or self._cv2 is None:
            self.set_status("Unable to capture a snapshot.")
            return

        output_path = self._build_snapshot_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._cv2.imwrite(str(output_path), frame_bgr):
            self.set_status(f"Unable to save snapshot to {output_path}")
            return

        self.set_recent_capture(output_path.name)
        self.set_status(f"Saved snapshot to {output_path}")
        self.snapshot_saved.emit(str(output_path))

    def _build_body(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_main_canvas(), 1)
        layout.addWidget(self._build_sidebar())
        return layout

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet(f"background: {SIDEBAR};")

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(18)

        back_button = QPushButton("Back to Menu")
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel("Capture Settings")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Configure recording scope, quality, and output.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        layout.addWidget(back_button)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title("Capture Mode"))
        layout.addWidget(self._build_sidebar_capture_toggle())
        layout.addSpacing(8)
        layout.addWidget(self._build_section_title("Video Settings"))
        layout.addWidget(self._build_resolution_group())
        layout.addLayout(self._build_frame_rate_group())
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title("Audio Source"))
        layout.addLayout(self._build_audio_group())
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title("Output"))
        layout.addLayout(self._build_output_group())
        layout.addStretch(1)
        layout.addWidget(self._status_label)

        restore_button = QPushButton("Restore Defaults")
        restore_button.clicked.connect(self._restore_defaults)
        restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_button.setStyleSheet(self._sidebar_button_style())
        layout.addWidget(restore_button)

        sidebar.setLayout(layout)
        return sidebar

    def _build_main_canvas(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            f"background: {SURFACE}; border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};"
        )

        badge = QLabel("Screen capture controls")
        badge.setStyleSheet(self._badge_style("#1d1730", "#c4b5fd"))

        title = QLabel("This window configures off-window capture.")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel("The recording target is the desktop, a window, or a region outside this app.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        helper = QLabel("Use the right sidebar to choose mode, frame rate, audio toggles, and save path.")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(helper, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        frame.setLayout(layout)
        return frame

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFixedHeight(104)
        footer.setStyleSheet(f"background: #0d0a15; border-top: 1px solid {BORDER};")

        recent_title = QLabel("Recent Capture")
        recent_title.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: 700; text-transform: uppercase;")

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

        self._record_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._record_button.setStyleSheet(self._accent_button_style())
        self._snapshot_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._snapshot_button.setStyleSheet(self._sidebar_button_style())
        self._pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_button.setStyleSheet(self._footer_secondary_button_style())
        self._stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_button.setStyleSheet(self._footer_secondary_button_style())

        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)
        center_layout.addWidget(self._record_button)
        center_layout.addWidget(self._snapshot_button)

        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(self._timer_label)
        right_layout.addWidget(self._pause_button)
        right_layout.addWidget(self._stop_button)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(22)
        layout.addLayout(recent_layout, 1)
        layout.addLayout(center_layout)
        layout.addStretch(1)
        layout.addLayout(right_layout)
        footer.setLayout(layout)
        return footer

    def _build_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        return label

    def _build_mode_card(self, text: str, active: bool) -> QWidget:
        card = QFrame()
        background = "rgba(139, 92, 246, 0.14)" if active else SURFACE_ALT
        border_color = ACCENT if active else BORDER
        card.setStyleSheet(
            f"background: {background}; border: 1px solid {border_color}; border-radius: 14px;"
        )

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background: {ACCENT if active else '#5c5473'}; border-radius: 5px; border: none;"
        )

        title = QLabel(text)
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        subtitle = QLabel("Ready" if active else "Available")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        layout = QHBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_layout, 1)
        card.setLayout(layout)
        return card

    def _build_sidebar_capture_toggle(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            f"background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 14px;"
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        for label, mode_name, checked in (
            ("Full Screen", "full_screen", True),
            ("Window", "window", False),
            ("Custom", "region", False),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(checked)
            button.setProperty("captureMode", mode_name)
            button.clicked.connect(self._on_capture_mode_changed)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(44)
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {TEXT_SECONDARY};
                    border: 1px solid transparent;
                    border-radius: 10px;
                    padding: 10px 8px;
                    text-align: center;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    color: {TEXT_PRIMARY};
                    border-color: {BORDER};
                }}
                QPushButton:checked {{
                    background: rgba(139, 92, 246, 0.20);
                    color: {TEXT_PRIMARY};
                    border-color: {ACCENT};
                }}
                """
            )
            self._capture_tabs.addButton(button)
            layout.addWidget(button, 1)

        container.setLayout(layout)
        return container

    def _build_resolution_group(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        caption = QLabel("Resolution")
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        self._resolution_combo.currentTextChanged.connect(lambda _text: self.set_status("Resolution updated."))
        layout.addWidget(caption)
        layout.addWidget(self._resolution_combo)
        wrapper.setLayout(layout)
        return wrapper

    def _build_frame_rate_group(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        caption = QLabel("Frame Rate")
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(caption)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for label, checked in (("30", True), ("60", False), ("120", False)):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(checked)
            button.clicked.connect(self._on_frame_rate_changed)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {SURFACE_ALT};
                    color: {TEXT_PRIMARY};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                    padding: 10px 0;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    border-color: {ACCENT};
                }}
                QPushButton:checked {{
                    background: rgba(139, 92, 246, 0.18);
                    color: {ACCENT};
                    border-color: {ACCENT};
                }}
                """
            )
            self._frame_rate_buttons.addButton(button)
            row.addWidget(button)

        layout.addLayout(row)
        return layout

    def _build_audio_group(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(self._build_switch_row("System Audio", self._system_audio_switch))
        layout.addLayout(self._build_switch_row("External Mic", self._external_mic_switch))
        return layout

    def _build_switch_row(self, text: str, switch: QCheckBox) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        label = QLabel(text)
        label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        switch.toggled.connect(lambda checked, name=text: self._on_audio_toggle(name, checked))
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(switch)
        return layout

    def _build_output_group(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        caption = QLabel("Save Path")
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self.browse_output_requested.emit)
        edit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_button.setFixedWidth(68)
        edit_button.setStyleSheet(self._accent_button_style(compact=True))

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._path_input, 1)
        row.addWidget(edit_button)

        layout.addWidget(caption)
        layout.addLayout(row)
        return layout

    def _poll_frame(self) -> None:
        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
            self.set_status("Unable to capture the screen preview.")
            return

        self._current_frame_bgr = frame_bgr

        if self._recording_state == RECORDING and self._recorder is not None:
            self._recorder.write(frame_bgr)
            elapsed = self._elapsed_before_pause
            if self._recording_started_at is not None:
                elapsed += perf_counter() - self._recording_started_at
            self._update_duration_display(elapsed)

    def _grab_screen_frame(self) -> np.ndarray | None:
        screen = self._current_screen()
        if screen is None or self._cv2 is None:
            return None

        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            return None

        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return None

        ptr = image.bits()
        if hasattr(ptr, "setsize"):
            ptr.setsize(image.sizeInBytes())
            buffer = ptr
        else:
            buffer = ptr.asstring(image.sizeInBytes())
        frame_rgba = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))

        target_width, target_height = self._selected_resolution()
        if (target_width, target_height) != (width, height):
            frame_rgba = self._cv2.resize(frame_rgba, (target_width, target_height), interpolation=self._cv2.INTER_AREA)

        return self._cv2.cvtColor(frame_rgba, self._cv2.COLOR_RGBA2BGR)

    def _selected_fps(self) -> int:
        checked_button = self._frame_rate_buttons.checkedButton()
        if checked_button is None:
            return DEFAULT_CAPTURE_FPS
        try:
            return int(checked_button.text())
        except ValueError:
            return DEFAULT_CAPTURE_FPS

    def _selected_resolution(self) -> tuple[int, int]:
        text = self._resolution_combo.currentText()
        try:
            raw = text.split("(")[0].strip()
            width_str, height_str = [part.strip() for part in raw.split("x")]
            return int(width_str), int(height_str)
        except (IndexError, ValueError):
            return 1920, 1080

    def _restart_preview_timer(self) -> None:
        if self._preview_timer is None:
            return
        interval_ms = max(8, int(1000 / max(1, self._selected_fps())))
        self._preview_timer.start(interval_ms)

    def _current_screen(self):
        window_handle = self.window().windowHandle() if self.window() is not None else None
        if window_handle is not None and window_handle.screen() is not None:
            return window_handle.screen()
        return QGuiApplication.primaryScreen()

    def _set_recording_state(self, state: RecordingState) -> None:
        self._recording_state = state
        is_recording = state == RECORDING
        is_paused = state == PAUSED

        self._record_button.setText("Resume" if is_paused else "Record")
        self._pause_button.setEnabled(is_recording)
        self._stop_button.setEnabled(is_recording or is_paused)

    def _update_duration_display(self, total_seconds: float) -> None:
        seconds = max(0, int(total_seconds))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        self._timer_label.setText(f"{hours:02d}:{minutes:02d}:{secs:02d}")

    def _on_capture_mode_changed(self) -> None:
        button = self._capture_tabs.checkedButton()
        if button is None:
            return
        self._capture_mode = str(button.property("captureMode"))
        self.set_status(f"{button.text()} selected.")

    def _on_frame_rate_changed(self) -> None:
        self._restart_preview_timer()
        self.set_status(f"Frame rate set to {self._selected_fps()} FPS.")

    def _on_audio_toggle(self, name: str, checked: bool) -> None:
        state = "enabled" if checked else "disabled"
        self.set_status(f"{name} {state}. Audio recording is not wired in the OpenCV path yet.")

    def _restore_defaults(self) -> None:
        capture_buttons = self._capture_tabs.buttons()
        if capture_buttons:
            capture_buttons[0].setChecked(True)
        fps_buttons = self._frame_rate_buttons.buttons()
        if fps_buttons:
            fps_buttons[0].setChecked(True)
        self._resolution_combo.setCurrentIndex(0)
        self._system_audio_switch.setChecked(True)
        self._external_mic_switch.setChecked(False)
        self._capture_mode = "full_screen"
        self._restart_preview_timer()
        self.set_status("Defaults restored.")

    def _build_recording_path(self) -> Path:
        return self._save_directory / f"screen_recording_{self._timestamp_string()}.avi"

    def _build_snapshot_path(self) -> Path:
        return self._save_directory / f"screen_snapshot_{self._timestamp_string()}.png"

    def _timestamp_string(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _combo_style(self) -> str:
        return (
            f"QComboBox {{"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            "padding: 10px 12px;"
            "font-size: 12px;"
            "}"
            "QComboBox::drop-down { border: none; width: 24px; }"
        )

    def _path_input_style(self) -> str:
        return (
            f"QLineEdit {{"
            "background: #0f0c18;"
            f"color: {TEXT_SECONDARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 10px;"
            "padding: 10px 12px;"
            "font-size: 11px;"
            "}"
        )

    def _sidebar_button_style(self) -> str:
        return (
            f"QPushButton {{"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            "padding: 10px 14px;"
            "font-size: 13px;"
            "font-weight: 700;"
            "}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT_PRIMARY}; }}"
        )

    def _accent_button_style(self, compact: bool = False) -> str:
        padding = "10px 0" if compact else "12px 18px"
        return (
            f"QPushButton {{"
            f"background: {ACCENT};"
            f"color: {TEXT_PRIMARY};"
            "border: none;"
            "border-radius: 12px;"
            f"padding: {padding};"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover { background: #9f75ff; }"
        )

    def _footer_secondary_button_style(self) -> str:
        return (
            f"QPushButton {{"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            "padding: 12px 16px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT_PRIMARY}; }}"
            "QPushButton:disabled { color: #6d6287; border-color: #2a223d; }"
        )

    def _build_switch(self, checked: bool) -> QCheckBox:
        switch = QCheckBox()
        switch.setChecked(checked)
        switch.setCursor(Qt.CursorShape.PointingHandCursor)
        switch.setStyleSheet(
            f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 22px;
                border-radius: 11px;
                background: #4b3f69;
            }}
            QCheckBox::indicator:checked {{
                background: {ACCENT};
            }}
            """
        )
        return switch

    def _badge_style(self, background: str, color: str) -> str:
        return (
            "QLabel {"
            f"background: {background};"
            f"color: {color};"
            f"border: 1px solid {BORDER};"
            "border-radius: 10px;"
            "padding: 6px 10px;"
            "font-size: 11px;"
            "font-weight: 700;"
            "}"
        )
