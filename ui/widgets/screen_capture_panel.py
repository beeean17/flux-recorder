from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path
from platform import system
from time import perf_counter

import numpy as np
from PyQt6.QtCore import QPoint, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QMouseEvent, QPainter, QPen, QRegion
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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
MIN_SELECTION_SIZE = 24
HOST_HIDE_DELAY_MS = 180
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
HWND_TOPMOST = -1


@dataclass
class CaptureTarget:
    mode: str
    rect: QRect | None = None
    window_handle: int | None = None
    title: str = ""


if system() == "Windows":
    from ctypes import wintypes

    class _POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]


class CaptureSelectorOverlay(QWidget):
    selection_made = pyqtSignal(object)
    selection_cancelled = pyqtSignal()

    def __init__(self, mode: str, excluded_handles: set[int] | None = None) -> None:
        super().__init__(None)
        self._mode = mode
        self._excluded_handles = set(excluded_handles or set())
        self._desktop_geometry = self._virtual_desktop_geometry()
        self._dragging = False
        self._start_point: QPoint | None = None
        self._current_point: QPoint | None = None
        self._hovered_window: CaptureTarget | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(self._desktop_geometry)

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def keyPressEvent(self, event) -> None:  # noqa: ANN001
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            self.selection_cancelled.emit()
            self.close()
            event.accept()
            return

        if self._mode == "window":
            target = self._window_at_global_point(event.globalPosition().toPoint())
            if target is not None:
                self.selection_made.emit(target)
                self.close()
            event.accept()
            return

        self._dragging = True
        self._start_point = event.globalPosition().toPoint()
        self._current_point = self._start_point
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        global_point = event.globalPosition().toPoint()
        if self._mode == "window":
            self._hovered_window = self._window_at_global_point(global_point)
        elif self._dragging:
            self._current_point = global_point
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._mode != "region" or not self._dragging:
            event.accept()
            return

        self._dragging = False
        self._current_point = event.globalPosition().toPoint()
        selection_rect = self._normalized_selection_rect()
        if selection_rect is None:
            self.selection_cancelled.emit()
            self.close()
            event.accept()
            return

        self.selection_made.emit(CaptureTarget(mode="region", rect=selection_rect, title="Custom area"))
        self.close()
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(3, 4, 9, 165))

        selection_rect = self._hovered_window.rect if self._mode == "window" and self._hovered_window is not None else self._normalized_selection_rect()
        if selection_rect is not None:
            local_rect = self._to_local_rect(selection_rect)
            painter.fillRect(local_rect, QColor(139, 92, 246, 55))
            painter.setPen(QPen(QColor(196, 181, 253), 2))
            painter.drawRect(local_rect)

            label_text = self._hovered_window.title if self._mode == "window" and self._hovered_window is not None else f"{selection_rect.width()} x {selection_rect.height()}"
            label_rect = QRect(local_rect.left(), max(16, local_rect.top() - 42), min(local_rect.width(), 420), 32)
            painter.fillRect(label_rect, QColor(11, 9, 19, 220))
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(label_rect.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label_text)

        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(
            QRect(24, 20, self.width() - 48, 54),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            self._instruction_text(),
        )
        painter.end()

    def _instruction_text(self) -> str:
        if self._mode == "window":
            return "Click the window you want to capture. Press Esc to cancel."
        return "Drag to select a capture area. Release to confirm, or press Esc to cancel."

    def _normalized_selection_rect(self) -> QRect | None:
        if self._start_point is None or self._current_point is None:
            return None
        rect = QRect(self._start_point, self._current_point).normalized()
        if rect.width() < MIN_SELECTION_SIZE or rect.height() < MIN_SELECTION_SIZE:
            return None
        return rect

    def _to_local_rect(self, global_rect: QRect) -> QRect:
        local_top_left = global_rect.topLeft() - self.geometry().topLeft()
        return QRect(local_top_left, global_rect.size())

    def _window_at_global_point(self, global_point: QPoint) -> CaptureTarget | None:
        if system() != "Windows":
            return None

        user32 = ctypes.windll.user32
        get_window = user32.GetWindow
        get_top_window = user32.GetTopWindow
        is_visible = user32.IsWindowVisible
        get_window_rect = user32.GetWindowRect
        get_window_text_length = user32.GetWindowTextLengthW
        get_window_text = user32.GetWindowTextW
        hwnd = get_top_window(0)

        excluded_handles = set(self._excluded_handles)
        try:
            excluded_handles.add(int(self.winId()))
        except TypeError:
            pass

        while hwnd:
            handle = int(hwnd)
            if handle not in excluded_handles and is_visible(hwnd):
                rect = _RECT()
                if get_window_rect(hwnd, ctypes.byref(rect)):
                    bounds = QRect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
                    if bounds.width() >= MIN_SELECTION_SIZE and bounds.height() >= MIN_SELECTION_SIZE and bounds.contains(global_point):
                        title_length = get_window_text_length(hwnd)
                        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                        get_window_text(hwnd, title_buffer, len(title_buffer))
                        title = title_buffer.value.strip() or f"Window {handle}"
                        return CaptureTarget(mode="window", rect=bounds, window_handle=handle, title=title)
            hwnd = get_window(hwnd, 2)

        return None

    def _virtual_desktop_geometry(self) -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)

        geometry = QRect(screens[0].geometry())
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        return geometry


def _set_window_capture_exclusion(widget: QWidget, excluded: bool = True) -> bool:
    if system() != "Windows":
        return False

    try:
        hwnd = int(widget.winId())
    except TypeError:
        return False

    affinity = WDA_EXCLUDEFROMCAPTURE if excluded else 0
    try:
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity))
    except (AttributeError, OSError):
        return False


def _set_window_click_through(widget: QWidget, enabled: bool = True) -> bool:
    if system() != "Windows":
        return False

    try:
        hwnd = int(widget.winId())
        user32 = ctypes.windll.user32
        current_style = int(user32.GetWindowLongW(hwnd, GWL_EXSTYLE))
    except (TypeError, AttributeError, OSError):
        return False

    updated_style = current_style | WS_EX_LAYERED | WS_EX_NOACTIVATE
    if enabled:
        updated_style |= WS_EX_TRANSPARENT
    else:
        updated_style &= ~WS_EX_TRANSPARENT

    try:
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, updated_style)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
    except (AttributeError, OSError):
        return False
    return True


def _raise_window_topmost(widget: QWidget) -> bool:
    if system() != "Windows":
        return False

    try:
        hwnd = int(widget.winId())
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
    except (TypeError, AttributeError, OSError):
        return False
    return True


def _capture_virtual_desktop_image() -> QImage | None:
    screens = QGuiApplication.screens()
    if not screens:
        return None

    geometry = QRect(screens[0].geometry())
    for screen in screens[1:]:
        geometry = geometry.united(screen.geometry())

    image = QImage(geometry.size(), QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.black)

    painter = QPainter(image)
    for screen in screens:
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            continue
        painter.drawPixmap(screen.geometry().topLeft() - geometry.topLeft(), pixmap)
    painter.end()
    return image


def _build_soft_blur(image: QImage, divisor: int = 12) -> QImage:
    width = max(1, image.width() // divisor)
    height = max(1, image.height() // divisor)
    reduced = image.scaled(
        width,
        height,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return reduced.scaled(
        image.width(),
        image.height(),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _window_rect_from_handle(window_handle: int) -> QRect | None:
    if system() != "Windows":
        return None

    rect = _RECT()
    try:
        ok = bool(ctypes.windll.user32.GetWindowRect(window_handle, ctypes.byref(rect)))
    except (AttributeError, OSError):
        return None
    if not ok:
        return None

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width < MIN_SELECTION_SIZE or height < MIN_SELECTION_SIZE:
        return None
    return QRect(rect.left, rect.top, width, height)


class FloatingCaptureController(QWidget):
    resume_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__(None)
        self._drag_offset: QPoint | None = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet(
            """
            QWidget {
                background: rgba(11, 9, 19, 0.94);
                border: 1px solid #34294b;
                border-radius: 18px;
            }
            """
        )

        self._resume_button = QPushButton("REC")
        self._pause_button = QPushButton("PAUSE")
        self._stop_button = QPushButton("STOP")

        self._resume_button.clicked.connect(self.resume_requested.emit)
        self._pause_button.clicked.connect(self.pause_requested.emit)
        self._stop_button.clicked.connect(self.stop_requested.emit)

        for button, background, border in (
            (self._resume_button, "#10b981", "#34d399"),
            (self._pause_button, "#211a35", "#8b5cf6"),
            (self._stop_button, "#7f1d1d", "#ef4444"),
        ):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(28)
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {background};
                    color: #f8fafc;
                    border: 1px solid {border};
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 10px;
                    font-weight: 800;
                }}
                QPushButton:disabled {{
                    background: #1f2937;
                    color: #64748b;
                    border-color: #334155;
                }}
                """
            )

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(self._resume_button)
        layout.addWidget(self._pause_button)
        layout.addWidget(self._stop_button)
        self.setLayout(layout)
        self.adjustSize()

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        _set_window_capture_exclusion(self, excluded=True)
        _raise_window_topmost(self)

    def sync_state(self, state: RecordingState) -> None:
        self._resume_button.setEnabled(state == PAUSED)
        self._pause_button.setEnabled(state == RECORDING)
        self._stop_button.setEnabled(state in (RECORDING, PAUSED))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if not isinstance(child, QPushButton):
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                _raise_window_topmost(self)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class RecordingFocusOverlay(QWidget):
    def __init__(self, target_provider) -> None:  # noqa: ANN001
        super().__init__(None)
        self._target_provider = target_provider
        self._blurred_desktop_image: QImage | None = None
        self._target_rect: QRect | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        _set_window_capture_exclusion(self, excluded=True)
        _set_window_click_through(self, enabled=True)

    def start(self) -> None:
        self.refresh_overlay()
        self.show()
        self.raise_()
        _raise_window_topmost(self)

    def stop(self) -> None:
        self.hide()

    def refresh_overlay(self) -> None:
        target = self._target_provider()
        if target is None or target.rect is None:
            self.hide()
            return

        geometry = self._virtual_desktop_geometry()
        self.setGeometry(geometry)
        self._target_rect = QRect(target.rect)
        desktop_image = _capture_virtual_desktop_image()
        if desktop_image is None or desktop_image.isNull():
            self.hide()
            return

        self._blurred_desktop_image = _build_soft_blur(desktop_image)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        if self._blurred_desktop_image is None or self._target_rect is None:
            return

        painter = QPainter(self)

        local_target_rect = QRect(self._target_rect)
        local_target_rect.translate(-self.geometry().topLeft())

        clip_region = QRegion(self.rect()).subtracted(QRegion(local_target_rect))
        painter.save()
        painter.setClipRegion(clip_region)
        painter.drawImage(self.rect(), self._blurred_desktop_image)
        painter.fillRect(self.rect(), QColor(9, 11, 20, 28))
        painter.restore()

        painter.setPen(QPen(QColor(196, 181, 253), 2))
        painter.drawRect(local_target_rect)
        painter.end()

    def _virtual_desktop_geometry(self) -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)

        geometry = QRect(screens[0].geometry())
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        return geometry


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
        self._window_target: CaptureTarget | None = None
        self._region_target: CaptureTarget | None = None
        self._selection_overlay: CaptureSelectorOverlay | None = None
        self._pending_action: str | None = None
        self._restore_window_maximized = False
        self._host_window_hidden = False
        self._hidden_for_recording = False
        self._floating_controller: FloatingCaptureController | None = None
        self._focus_overlay: RecordingFocusOverlay | None = None

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

        self._output_size_value = QLabel()
        self._output_size_value.setWordWrap(True)
        self._output_size_value.setMinimumHeight(44)
        self._output_size_value.setStyleSheet(self._readonly_info_style())

        self._system_audio_switch = self._build_switch(True)
        self._external_mic_switch = self._build_switch(False)

        self._timer_label = QLabel("00:00:00")
        self._timer_label.setStyleSheet(f"color: {ACCENT}; font-size: 24px; font-weight: 800;")

        self._record_button = QPushButton("Record")
        self._snapshot_button = QPushButton("Snapshot")
        self._pause_button = QPushButton("Pause")
        self._stop_button = QPushButton("Stop")
        self._target_summary_label = QLabel()
        self._target_summary_label.setWordWrap(True)
        self._target_summary_label.setMinimumHeight(22)
        self._target_summary_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        self._target_hint_label = QLabel()
        self._target_hint_label.setWordWrap(True)
        self._target_hint_label.setMinimumHeight(38)
        self._target_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self._select_target_button = QPushButton()
        self._select_target_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_target_button.setMinimumHeight(44)
        self._select_target_button.clicked.connect(lambda: self._begin_target_selection())
        self._select_target_button.setStyleSheet(self._sidebar_button_style())

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
        self._update_capture_target_ui()

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

        if self._selection_overlay is not None:
            self._selection_overlay.close()
            self._selection_overlay.deleteLater()
        self._selection_overlay = None
        self._pending_action = None

        if self._recorder is not None:
            saved_path = self._recorder.stop()
            if saved_path is not None and self._recording_state != IDLE:
                self.recording_saved.emit(str(saved_path))

        self._teardown_floating_controller()
        self._teardown_focus_overlay()
        if self._host_window_hidden:
            self._restore_host_window()

        self._recorder = None
        self._cv2 = None
        self._current_frame_bgr = None
        self._recording_started_at = None
        self._elapsed_before_pause = 0.0
        self._hidden_for_recording = False
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

        if not self._ensure_capture_target_ready("record"):
            return

        self.set_status("Preparing capture. Recorder will hide before recording starts.")
        self._run_hidden_host_action(self._start_recording_now, restore_after=False)

    def pause_recording(self) -> None:
        if self._recording_state != RECORDING:
            return

        if self._recording_started_at is not None:
            self._elapsed_before_pause += perf_counter() - self._recording_started_at
        self._recording_started_at = None
        self._set_recording_state(PAUSED)
        self.set_status("Recording paused. Use the mini controller to resume or stop.")

    def stop_recording(self) -> None:
        if self._recording_state == IDLE or self._recorder is None:
            if self._hidden_for_recording:
                self._finish_hidden_recording_session()
            return

        if self._recording_state == RECORDING and self._recording_started_at is not None:
            self._elapsed_before_pause += perf_counter() - self._recording_started_at

        self._recording_started_at = None
        saved_path = self._recorder.stop()
        self._elapsed_before_pause = 0.0
        self._update_duration_display(0.0)
        self._set_recording_state(IDLE)
        self._finish_hidden_recording_session()

        if saved_path is not None:
            self.set_recent_capture(saved_path.name)
            self.set_status(f"Saved screen recording to {saved_path}")
            self.recording_saved.emit(str(saved_path))
        else:
            self.set_status("Recording stopped.")

    def capture_snapshot(self) -> None:
        if self._cv2 is None:
            self.start_preview()
        if self._cv2 is None:
            return

        if not self._ensure_capture_target_ready("snapshot"):
            return

        self.set_status("Capturing snapshot. Recorder will hide for a moment.")
        self._run_hidden_host_action(self._capture_snapshot_now, restore_after=True)

    def _build_body(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main_canvas(), 1)
        return layout

    def _build_sidebar(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setFixedWidth(340)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea {{
                background: {SIDEBAR};
                border: none;
            }}
            QWidget#screen_capture_sidebar {{
                background: {SIDEBAR};
            }}
            QScrollBar:vertical {{
                background: {SIDEBAR};
                width: 10px;
                margin: 8px 4px 8px 0;
            }}
            QScrollBar::handle:vertical {{
                background: #2a223d;
                border-radius: 5px;
                min-height: 36px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        sidebar = QFrame()
        sidebar.setObjectName("screen_capture_sidebar")
        sidebar.setMinimumWidth(320)
        sidebar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(18)

        back_button = QPushButton("Back to Menu")
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel("Capture Settings")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Adjust recording quality, audio options, and the output location.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        layout.addWidget(back_button)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title("Video Settings"))
        layout.addWidget(self._build_output_size_group())
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
        scroll_area.setWidget(sidebar)
        return scroll_area

    def _build_main_canvas(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("screen_capture_main_canvas")
        frame.setStyleSheet(
            f"""
            QFrame#screen_capture_main_canvas {{
                background: {SURFACE};
                border-left: 1px solid {BORDER};
                border-bottom: 1px solid {BORDER};
            }}
            """
        )

        badge = QLabel("Screen capture workflow")
        badge.setStyleSheet(self._badge_style("#1d1730", "#c4b5fd"))

        title = QLabel("Select the target first, then let the recorder step out of the way.")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel(
            "Window and custom-area capture now use a dedicated picker so you can lock onto the exact target before recording."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        helper = QLabel(
            "When recording starts, the app hides itself and leaves behind only a tiny capture-excluded controller for resume, pause, and stop."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")

        setup_title = QLabel("Capture Setup")
        setup_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        setup_hint = QLabel("Choose the capture mode on the right, then confirm the exact target before you record.")
        setup_hint.setWordWrap(True)
        setup_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        self._window_recording_notice = QLabel()
        self._window_recording_notice.setWordWrap(True)
        self._window_recording_notice.setStyleSheet(f"color: #fbbf24; font-size: 12px; font-weight: 600;")
        self._window_recording_notice.hide()

        setup_panel = QFrame()
        setup_panel.setObjectName("screen_capture_setup_panel")
        setup_panel.setStyleSheet(
            f"""
            QFrame#screen_capture_setup_panel {{
                background: #120f1d;
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            """
        )

        setup_layout = QVBoxLayout()
        setup_layout.setContentsMargins(24, 24, 24, 24)
        setup_layout.setSpacing(18)
        setup_layout.addWidget(setup_title)
        setup_layout.addWidget(setup_hint)
        setup_layout.addWidget(self._window_recording_notice)
        setup_layout.addWidget(self._build_sidebar_capture_toggle())
        setup_layout.addWidget(self._build_target_card())
        setup_panel.setLayout(setup_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(setup_panel)
        layout.addWidget(helper, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        frame.setLayout(layout)
        return frame

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("screen_capture_footer")
        footer.setFixedHeight(104)
        footer.setStyleSheet(
            f"""
            QFrame#screen_capture_footer {{
                background: #0d0a15;
                border-top: 1px solid {BORDER};
            }}
            """
        )

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

        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)
        center_layout.addWidget(self._record_button)
        center_layout.addWidget(self._snapshot_button)

        left_panel = QWidget()
        left_panel.setLayout(recent_layout)

        center_panel = QWidget()
        center_panel.setLayout(center_layout)

        side_width = left_panel.sizeHint().width()
        left_panel.setFixedWidth(side_width)

        right_spacer = QWidget()
        right_spacer.setFixedWidth(side_width)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(22)
        layout.addWidget(left_panel, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(center_panel, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(right_spacer, 0)
        footer.setLayout(layout)
        return footer

    def _build_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        return label

    def _build_sidebar_capture_toggle(self) -> QWidget:
        container = QFrame()
        container.setObjectName("screen_capture_mode_toggle")
        container.setStyleSheet(
            f"""
            QFrame#screen_capture_mode_toggle {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            """
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

    def _build_target_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("screen_capture_target_card")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        card.setMinimumHeight(168)
        card.setStyleSheet(
            f"""
            QFrame#screen_capture_target_card {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Capture Target")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")

        layout.addWidget(title)
        layout.addWidget(self._target_summary_label)
        layout.addWidget(self._target_hint_label)
        layout.addStretch(1)
        layout.addWidget(self._select_target_button)
        card.setLayout(layout)
        return card

    def _build_output_size_group(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        caption = QLabel("Output Size")
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(caption)
        layout.addWidget(self._output_size_value)
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
            self._current_frame_bgr = None
            if self._recording_state == RECORDING:
                self.stop_recording()
                self.set_status("Capture target is unavailable. Recording stopped.")
            return

        self._current_frame_bgr = frame_bgr

        if self._recording_state == RECORDING and self._recorder is not None:
            self._recorder.write(frame_bgr)
            elapsed = self._elapsed_before_pause
            if self._recording_started_at is not None:
                elapsed += perf_counter() - self._recording_started_at
            self._update_duration_display(elapsed)

    def _grab_screen_frame(self) -> np.ndarray | None:
        if self._cv2 is None:
            return None

        if self._capture_mode == "window":
            image = self._grab_selected_window_image()
        elif self._capture_mode == "region":
            image = self._grab_selected_region_image()
        else:
            image = self._grab_virtual_desktop_image()

        if image is None or image.isNull():
            return None

        return self._qimage_to_bgr_frame(image)

    def _grab_selected_window_image(self) -> QImage | None:
        target = self._window_target
        if target is None:
            return None

        if target.window_handle is not None:
            screen = self._screen_for_rect(target.rect)
            if screen is not None:
                pixmap = screen.grabWindow(target.window_handle)
                if not pixmap.isNull():
                    return pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)

        if target.rect is None:
            return None
        return self._crop_image(self._grab_virtual_desktop_image(), target.rect)

    def _grab_selected_region_image(self) -> QImage | None:
        target = self._region_target
        if target is None or target.rect is None:
            return None
        return self._crop_image(self._grab_virtual_desktop_image(), target.rect)

    def _grab_virtual_desktop_image(self) -> QImage | None:
        screens = QGuiApplication.screens()
        if not screens:
            return None

        geometry = self._virtual_desktop_geometry()
        image = QImage(geometry.size(), QImage.Format.Format_RGBA8888)
        image.fill(Qt.GlobalColor.black)

        painter = QPainter(image)
        for screen in screens:
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                continue
            painter.drawPixmap(screen.geometry().topLeft() - geometry.topLeft(), pixmap)
        painter.end()
        return image

    def _crop_image(self, image: QImage | None, global_rect: QRect) -> QImage | None:
        if image is None or image.isNull():
            return None

        desktop_geometry = self._virtual_desktop_geometry()
        local_rect = QRect(global_rect)
        local_rect.translate(-desktop_geometry.topLeft())
        local_rect = local_rect.intersected(image.rect())
        if local_rect.width() < MIN_SELECTION_SIZE or local_rect.height() < MIN_SELECTION_SIZE:
            return None
        return image.copy(local_rect)

    def _qimage_to_bgr_frame(self, image: QImage) -> np.ndarray | None:
        if self._cv2 is None:
            return None

        converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
        width = converted.width()
        height = converted.height()
        if width <= 0 or height <= 0:
            return None

        ptr = converted.bits()
        if hasattr(ptr, "setsize"):
            ptr.setsize(converted.sizeInBytes())
            buffer = ptr
        else:
            buffer = ptr.asstring(converted.sizeInBytes())
        frame_rgba = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))

        return self._cv2.cvtColor(frame_rgba, self._cv2.COLOR_RGBA2BGR)

    def _selected_fps(self) -> int:
        checked_button = self._frame_rate_buttons.checkedButton()
        if checked_button is None:
            return DEFAULT_CAPTURE_FPS
        try:
            return int(checked_button.text())
        except ValueError:
            return DEFAULT_CAPTURE_FPS

    def _restart_preview_timer(self) -> None:
        if self._preview_timer is None:
            return
        interval_ms = max(8, int(1000 / max(1, self._selected_fps())))
        self._preview_timer.start(interval_ms)

    def _set_recording_state(self, state: RecordingState) -> None:
        self._recording_state = state
        is_recording = state == RECORDING
        is_paused = state == PAUSED

        self._record_button.setText("Resume" if is_paused else "Record")
        self._pause_button.setEnabled(is_recording)
        self._stop_button.setEnabled(is_recording or is_paused)
        self._update_floating_controller()

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
        self._update_capture_target_ui()
        mode_label = button.text()
        if self._capture_mode == "full_screen":
            self.set_status(f"{mode_label} selected. The recorder hides itself when capture starts.")
        else:
            self.set_status(f"{mode_label} selected. Choose a target before capture.")

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
        self._system_audio_switch.setChecked(True)
        self._external_mic_switch.setChecked(False)
        self._capture_mode = "full_screen"
        self._window_target = None
        self._region_target = None
        self._restart_preview_timer()
        self._update_capture_target_ui()
        self.set_status("Defaults restored.")

    def _build_recording_path(self) -> Path:
        return self._save_directory / f"screen_recording_{self._timestamp_string()}.avi"

    def _build_snapshot_path(self) -> Path:
        return self._save_directory / f"screen_snapshot_{self._timestamp_string()}.png"

    def _timestamp_string(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _readonly_info_style(self) -> str:
        return (
            "QLabel {"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            "padding: 10px 12px;"
            "font-size: 12px;"
            "}"
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

    def _ensure_capture_target_ready(self, action: str) -> bool:
        if self._capture_mode == "full_screen":
            return True

        target = self._current_target()
        if target is not None:
            return True

        self._pending_action = action
        self._begin_target_selection()
        return False

    def _begin_target_selection(self) -> None:
        if self._recording_state != IDLE:
            self.set_status("Stop the current recording before changing the capture target.")
            return
        if self._selection_overlay is not None:
            return
        if self._capture_mode == "full_screen":
            self.set_status("Full screen mode captures the entire desktop. No extra target selection is needed.")
            return
        if self._capture_mode == "window" and system() != "Windows":
            self.set_status("Window picking is currently supported on Windows in this build.")
            return

        self.set_status("Hide recorder and choose a capture target.")
        self._run_hidden_host_action(self._show_target_selector, restore_after=False)

    def _show_target_selector(self) -> None:
        excluded_handles = self._excluded_window_handles()
        self._selection_overlay = CaptureSelectorOverlay(self._capture_mode, excluded_handles=excluded_handles)
        self._selection_overlay.selection_made.connect(self._on_target_selected)
        self._selection_overlay.selection_cancelled.connect(self._on_target_selection_cancelled)
        self._selection_overlay.show()

    def _on_target_selected(self, target: CaptureTarget) -> None:
        if self._selection_overlay is not None:
            self._selection_overlay.deleteLater()
        self._selection_overlay = None

        if target.mode == "window":
            self._window_target = target
            self.set_status(f"Window selected: {target.title}")
        else:
            self._region_target = target
            if target.rect is not None:
                self.set_status(f"Area selected: {target.rect.width()} x {target.rect.height()}")
            else:
                self.set_status("Area selected.")

        self._restore_host_window()
        self._update_capture_target_ui()

        pending_action = self._pending_action
        self._pending_action = None
        if pending_action == "record":
            QTimer.singleShot(120, self.start_or_resume_recording)
        elif pending_action == "snapshot":
            QTimer.singleShot(120, self.capture_snapshot)

    def _on_target_selection_cancelled(self) -> None:
        if self._selection_overlay is not None:
            self._selection_overlay.deleteLater()
        self._selection_overlay = None
        self._restore_host_window()
        self._pending_action = None
        self.set_status("Capture target selection cancelled.")

    def _current_target(self) -> CaptureTarget | None:
        if self._capture_mode == "window":
            return self._window_target
        if self._capture_mode == "region":
            return self._region_target
        return CaptureTarget(mode="full_screen", rect=self._virtual_desktop_geometry(), title="Entire desktop")

    def _update_capture_target_ui(self) -> None:
        if self._capture_mode == "full_screen":
            self._target_summary_label.setText("Entire desktop")
            self._target_hint_label.setText("Use this when you want the whole workspace. The recorder hides itself when capture starts.")
            self._select_target_button.setText("Desktop Ready")
            self._select_target_button.setEnabled(False)
            self._output_size_value.setText(self._capture_dimensions_text(self._virtual_desktop_geometry()))
            self._window_recording_notice.hide()
            return

        if self._capture_mode == "window":
            target = self._window_target
            self._target_summary_label.setText(target.title if target is not None else "No window selected")
            self._target_hint_label.setText("Click Choose Window, then click the app or window you want to capture.")
            self._select_target_button.setText("Choose Window")
            self._select_target_button.setEnabled(True)
            self._output_size_value.setText(self._capture_dimensions_text(target.rect if target is not None else None))
            self._window_recording_notice.setText("Window recording does not support resizing the selected window while recording.")
            self._window_recording_notice.show()
            return

        target = self._region_target
        if target is not None and target.rect is not None:
            self._target_summary_label.setText(f"{target.rect.width()} x {target.rect.height()} area")
        else:
            self._target_summary_label.setText("No area selected")
        self._target_hint_label.setText("Click Choose Area, then drag across the region you want to capture.")
        self._select_target_button.setText("Choose Area")
        self._select_target_button.setEnabled(True)
        self._output_size_value.setText(self._capture_dimensions_text(target.rect if target is not None else None))
        self._window_recording_notice.hide()

    def _capture_dimensions_text(self, rect: QRect | None) -> str:
        if rect is None:
            return "Matches the selected target size automatically."
        return f"{rect.width()} x {rect.height()} px (saved at original capture size)"

    def _run_hidden_host_action(self, callback, restore_after: bool) -> None:  # noqa: ANN001
        self._hide_host_window()

        def runner() -> None:
            try:
                callback()
            finally:
                if restore_after:
                    self._restore_host_window()

        QTimer.singleShot(HOST_HIDE_DELAY_MS, runner)

    def _hide_host_window(self) -> None:
        host = self.window()
        if host is None or self._host_window_hidden:
            return

        self._restore_window_maximized = bool(host.isMaximized())
        host.hide()
        QApplication.processEvents()
        self._host_window_hidden = True

    def _restore_host_window(self) -> None:
        host = self.window()
        if host is None or not self._host_window_hidden:
            return

        if self._restore_window_maximized:
            host.showMaximized()
        else:
            host.showNormal()
        host.raise_()
        host.activateWindow()
        QApplication.processEvents()
        self._host_window_hidden = False

    def _start_recording_now(self) -> None:
        if self._cv2 is None or self._recorder is None:
            self._restore_host_window()
            self.set_status("Capture backend is unavailable.")
            return

        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
            self._restore_host_window()
            self.set_status("Unable to capture a screen frame.")
            return

        output_path = self._build_recording_path()
        height, width = frame_bgr.shape[:2]
        try:
            self._recorder.start(output_path=output_path, fps=float(self._selected_fps()), size=(width, height))
        except RuntimeError as exc:
            self._restore_host_window()
            self.set_status(str(exc))
            return

        self._hidden_for_recording = True
        self._elapsed_before_pause = 0.0
        self._recording_started_at = perf_counter()
        self._set_recording_state(RECORDING)
        self._show_floating_controller()
        self._show_focus_overlay()
        self.set_status(f"Recording to {output_path}. Use the mini controller to resume, pause, or stop.")

    def _capture_snapshot_now(self) -> None:
        if self._cv2 is None:
            self.set_status("Capture backend is unavailable.")
            return

        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
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

    def _show_floating_controller(self) -> None:
        if self._floating_controller is None:
            self._floating_controller = FloatingCaptureController()
            self._floating_controller.resume_requested.connect(self.start_or_resume_recording)
            self._floating_controller.pause_requested.connect(self.pause_recording)
            self._floating_controller.stop_requested.connect(self.stop_recording)

        self._position_floating_controller()
        self._floating_controller.sync_state(self._recording_state)
        self._floating_controller.show()
        self._floating_controller.raise_()
        _raise_window_topmost(self._floating_controller)

    def _teardown_floating_controller(self) -> None:
        if self._floating_controller is not None:
            self._floating_controller.hide()
            self._floating_controller.deleteLater()
        self._floating_controller = None

    def _update_floating_controller(self) -> None:
        if self._floating_controller is not None:
            self._floating_controller.sync_state(self._recording_state)

    def _position_floating_controller(self) -> None:
        if self._floating_controller is None:
            return

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        self._floating_controller.adjustSize()
        geometry = screen.availableGeometry()
        x = geometry.right() - self._floating_controller.width() - 20
        y = geometry.top() + 20
        self._floating_controller.move(x, y)

    def _show_focus_overlay(self) -> None:
        if self._capture_mode == "full_screen" or system() != "Windows":
            self._teardown_focus_overlay()
            return

        if self._focus_overlay is None:
            self._focus_overlay = RecordingFocusOverlay(self._recording_focus_target)

        self._focus_overlay.start()
        if self._floating_controller is not None:
            self._floating_controller.raise_()
            _raise_window_topmost(self._floating_controller)

    def _teardown_focus_overlay(self) -> None:
        if self._focus_overlay is not None:
            self._focus_overlay.stop()
            self._focus_overlay.deleteLater()
        self._focus_overlay = None

    def _recording_focus_target(self) -> CaptureTarget | None:
        if self._capture_mode == "window":
            target = self._window_target
            if target is None or target.window_handle is None:
                return target
            live_rect = _window_rect_from_handle(target.window_handle)
            if live_rect is None:
                return target
            return CaptureTarget(
                mode=target.mode,
                rect=live_rect,
                window_handle=target.window_handle,
                title=target.title,
            )
        if self._capture_mode == "region":
            return self._region_target
        return None

    def _finish_hidden_recording_session(self) -> None:
        self._hidden_for_recording = False
        self._teardown_floating_controller()
        self._teardown_focus_overlay()
        self._restore_host_window()

    def _screen_for_rect(self, rect: QRect | None):
        if rect is None:
            return QGuiApplication.primaryScreen()

        center = rect.center()
        for screen in QGuiApplication.screens():
            if screen.geometry().contains(center):
                return screen
        return QGuiApplication.primaryScreen()

    def _virtual_desktop_geometry(self) -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1920, 1080)

        geometry = QRect(screens[0].geometry())
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        return geometry

    def _excluded_window_handles(self) -> set[int]:
        handles: set[int] = set()
        host = self.window()
        if host is not None:
            try:
                handles.add(int(host.winId()))
            except TypeError:
                pass
        if self._floating_controller is not None:
            try:
                handles.add(int(self._floating_controller.winId()))
            except TypeError:
                pass
        if self._focus_overlay is not None:
            try:
                handles.add(int(self._focus_overlay.winId()))
            except TypeError:
                pass
        return handles
