from __future__ import annotations

import ctypes
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from platform import system
from time import perf_counter

import numpy as np
from PyQt6.QtCore import QPoint, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QMouseEvent, QPainter, QPen, QRegion
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
FRAME_INTERVAL_WINDOW = 120
MIN_CAPTURE_FPS = 5.0
MAX_CAPTURE_FPS = 120.0
MIN_SELECTION_SIZE = 24
HOST_HIDE_DELAY_MS = 180
WDA_EXCLUDEFROMCAPTURE = 0x00000011
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
GA_ROOT = 2
SW_SHOW = 5
SW_RESTORE = 9

SCREEN_CAPTURE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "custom_area": "Custom area",
        "overlay_window_instruction": "Click the window you want to capture. Press Esc to cancel.",
        "overlay_area_instruction": "Drag to select a capture area. Release to confirm, or press Esc to cancel.",
        "floating_resume": "REC",
        "floating_pause": "PAUSE",
        "floating_stop": "STOP",
        "status_ready": "Ready",
        "no_capture": "No capture yet",
        "record": "Record",
        "snapshot": "Snapshot",
        "pause": "Pause",
        "stop": "Stop",
        "resume": "Resume",
        "capture_backend_missing": "Screen capture backend is unavailable. Missing dependency: {name}",
        "capture_backend_ready": "Capture backend ready.",
        "recording_resumed": "Recording resumed.",
        "preparing_capture": "Preparing capture. Recorder will hide before recording starts.",
        "recording_paused": "Recording paused. Use the mini controller to resume or stop.",
        "saved_screen_recording": "Saved screen recording to {path}",
        "recording_stopped": "Recording stopped.",
        "capturing_snapshot": "Capturing snapshot. Recorder will hide for a moment.",
        "back_to_menu": "Back to Menu (Esc)",
        "capture_settings": "Capture Settings",
        "capture_settings_subtitle": "Adjust recording quality, audio options, and the output location.",
        "video_settings": "Video Settings",
        "audio_source": "Audio Source",
        "output": "Output",
        "restore_defaults": "Restore Defaults",
        "screen_workflow": "Screen capture workflow",
        "hero_title": "Select the target first, then let the recorder step out of the way.",
        "hero_subtitle": "Window and custom-area capture now use a dedicated picker so you can lock onto the exact target before recording.",
        "helper": "When recording starts, the app hides itself and leaves behind only a tiny capture-excluded controller for resume, pause, and stop.",
        "capture_setup": "Capture Setup",
        "capture_setup_hint": "Choose the capture mode on the right, then confirm the exact target before you record.",
        "recent_capture": "Recent Capture",
        "full_screen": "Full Screen",
        "window": "Window",
        "custom": "Custom",
        "capture_target": "Capture Target",
        "output_size": "Output Size",
        "frame_rate": "Frame Rate",
        "system_audio": "System Audio",
        "external_mic": "External Mic",
        "save_path": "Save Path",
        "edit": "Edit",
        "capture_target_unavailable": "Capture target is unavailable. Recording stopped.",
        "mode_selected_full": "{mode} selected. The recorder hides itself when capture starts.",
        "mode_selected_other": "{mode} selected. Choose a target before capture.",
        "window_use_custom_fallback": "Window picking is unavailable on this OS. Use Custom and drag over the app window you want to capture.",
        "frame_rate_set": "Frame rate set to {fps} FPS.",
        "audio_toggle": "{name} {state}. Audio recording is not wired in the OpenCV path yet.",
        "enabled": "enabled",
        "disabled": "disabled",
        "defaults_restored": "Defaults restored.",
        "stop_before_target_change": "Stop the current recording before changing the capture target.",
        "full_screen_mode_note": "Full screen mode captures the entire desktop. No extra target selection is needed.",
        "window_windows_only": "Window picking is currently supported on Windows in this build.",
        "hide_and_choose_target": "Hide recorder and choose a capture target.",
        "window_selected": "Window selected: {title}",
        "area_selected_size": "Area selected: {width} x {height}",
        "area_selected": "Area selected.",
        "target_selection_cancelled": "Capture target selection cancelled.",
        "entire_desktop": "Entire desktop",
        "desktop_hint": "Use this when you want the whole workspace. The recorder hides itself when capture starts.",
        "desktop_ready": "Desktop Ready",
        "no_window_selected": "No window selected",
        "window_hint": "Click Choose Window, then click the app or window you want to capture.",
        "choose_window": "Choose Window",
        "use_custom_mode": "Use Custom Mode",
        "window_notice": "Window recording does not support resizing the selected window while recording.",
        "area_summary": "{width} x {height} area",
        "no_area_selected": "No area selected",
        "area_hint": "Click Choose Area, then drag across the region you want to capture.",
        "choose_area": "Choose Area",
        "matches_target_size": "Matches the selected target size automatically.",
        "saved_at_original_size": "{width} x {height} px (saved at original capture size)",
        "backend_unavailable": "Capture backend is unavailable.",
        "unable_capture_frame": "Unable to capture a screen frame.",
        "recording_to_with_controller": "Recording to {path}. Use the mini controller to resume, pause, or stop.",
        "unable_capture_snapshot": "Unable to capture a snapshot.",
        "unable_save_snapshot": "Unable to save snapshot to {path}",
        "saved_snapshot": "Saved snapshot to {path}",
        "language_button": "한국어",
    },
    "ko": {
        "custom_area": "사용자 지정 영역",
        "overlay_window_instruction": "캡처할 창을 클릭하세요. 취소하려면 Esc를 누르세요.",
        "overlay_area_instruction": "캡처할 영역을 드래그해 선택하세요. 마우스를 놓으면 확정되고, Esc로 취소할 수 있습니다.",
        "floating_resume": "REC",
        "floating_pause": "일시정지",
        "floating_stop": "종료",
        "status_ready": "준비 완료",
        "no_capture": "아직 캡처가 없습니다",
        "record": "녹화",
        "snapshot": "스냅샷",
        "pause": "일시정지",
        "stop": "종료",
        "resume": "재개",
        "capture_backend_missing": "화면 캡처 백엔드를 사용할 수 없습니다. 누락된 의존성: {name}",
        "capture_backend_ready": "캡처 백엔드가 준비되었습니다.",
        "recording_resumed": "녹화를 다시 시작했습니다.",
        "preparing_capture": "캡처를 준비 중입니다. 녹화 시작 전 창이 숨겨집니다.",
        "recording_paused": "녹화를 일시정지했습니다. 미니 컨트롤러에서 재개하거나 종료할 수 있습니다.",
        "saved_screen_recording": "{path}에 화면 녹화 파일을 저장했습니다",
        "recording_stopped": "녹화를 종료했습니다.",
        "capturing_snapshot": "스냅샷을 저장하는 중입니다. 잠시 창이 숨겨집니다.",
        "back_to_menu": "메뉴로 돌아가기 (Esc)",
        "capture_settings": "캡처 설정",
        "capture_settings_subtitle": "녹화 화질, 오디오 옵션, 저장 위치를 조정하세요.",
        "video_settings": "비디오 설정",
        "audio_source": "오디오 소스",
        "output": "출력",
        "restore_defaults": "기본값 복원",
        "screen_workflow": "화면 캡처 작업 흐름",
        "hero_title": "먼저 대상을 고른 뒤 녹화를 시작하세요.",
        "hero_subtitle": "창과 사용자 지정 영역 캡처는 전용 선택기를 사용하므로, 녹화 전에 정확한 대상을 지정할 수 있습니다.",
        "helper": "녹화가 시작되면 앱은 스스로 숨기고, 재개·일시정지·종료를 위한 작은 캡처 제외 컨트롤러만 남깁니다.",
        "capture_setup": "캡처 준비",
        "capture_setup_hint": "오른쪽에서 캡처 모드를 고른 뒤, 녹화 전에 정확한 대상을 확정하세요.",
        "recent_capture": "최근 캡처",
        "full_screen": "전체 화면",
        "window": "창",
        "custom": "사용자 지정",
        "capture_target": "캡처 대상",
        "output_size": "출력 크기",
        "frame_rate": "프레임 속도",
        "system_audio": "시스템 오디오",
        "external_mic": "외부 마이크",
        "save_path": "저장 경로",
        "edit": "변경",
        "capture_target_unavailable": "캡처 대상이 사용할 수 없어 녹화를 중지했습니다.",
        "mode_selected_full": "{mode} 모드를 선택했습니다. 캡처가 시작되면 녹화기가 자동으로 숨겨집니다.",
        "mode_selected_other": "{mode} 모드를 선택했습니다. 캡처 전에 대상을 먼저 고르세요.",
        "window_use_custom_fallback": "이 운영체제에서는 창 직접 선택을 지원하지 않습니다. 사용자 지정 모드로 전환한 뒤 캡처할 창 영역을 직접 드래그해 선택하세요.",
        "frame_rate_set": "프레임 속도를 {fps} FPS로 설정했습니다.",
        "audio_toggle": "{name} {state}. 현재 OpenCV 경로에서는 오디오 녹화가 연결되어 있지 않습니다.",
        "enabled": "켜짐",
        "disabled": "꺼짐",
        "defaults_restored": "기본값으로 복원했습니다.",
        "stop_before_target_change": "캡처 대상을 바꾸기 전에 현재 녹화를 종료하세요.",
        "full_screen_mode_note": "전체 화면 모드는 데스크톱 전체를 캡처합니다. 추가 대상 선택이 필요하지 않습니다.",
        "window_windows_only": "현재 빌드에서는 창 선택 기능이 Windows에서만 지원됩니다.",
        "hide_and_choose_target": "녹화기를 숨긴 뒤 캡처 대상을 선택하세요.",
        "window_selected": "선택한 창: {title}",
        "area_selected_size": "선택한 영역: {width} x {height}",
        "area_selected": "영역을 선택했습니다.",
        "target_selection_cancelled": "캡처 대상 선택을 취소했습니다.",
        "entire_desktop": "전체 데스크톱",
        "desktop_hint": "작업 공간 전체를 캡처할 때 사용하세요. 캡처가 시작되면 녹화기가 자동으로 숨겨집니다.",
        "desktop_ready": "데스크톱 준비 완료",
        "no_window_selected": "선택된 창이 없습니다",
        "window_hint": "창 선택을 누른 뒤 캡처할 앱이나 창을 클릭하세요.",
        "choose_window": "창 선택",
        "use_custom_mode": "사용자 지정 모드 사용",
        "window_notice": "창 녹화는 녹화 중 선택한 창의 크기 변경을 지원하지 않습니다.",
        "area_summary": "{width} x {height} 영역",
        "no_area_selected": "선택된 영역이 없습니다",
        "area_hint": "영역 선택을 누른 뒤 원하는 범위를 드래그하세요.",
        "choose_area": "영역 선택",
        "matches_target_size": "선택한 대상 크기에 자동으로 맞춰 저장합니다.",
        "saved_at_original_size": "{width} x {height} px (원본 캡처 크기로 저장)",
        "backend_unavailable": "캡처 백엔드를 사용할 수 없습니다.",
        "unable_capture_frame": "화면 프레임을 가져오지 못했습니다.",
        "recording_to_with_controller": "{path}에 녹화 중입니다. 미니 컨트롤러에서 재개, 일시정지, 종료를 사용할 수 있습니다.",
        "unable_capture_snapshot": "스냅샷을 캡처하지 못했습니다.",
        "unable_save_snapshot": "{path}에 스냅샷을 저장하지 못했습니다",
        "saved_snapshot": "{path}에 스냅샷을 저장했습니다",
    },
}


def _screen_text(language: str, key: str, **kwargs) -> str:
    normalized = language if language in SCREEN_CAPTURE_TRANSLATIONS else "en"
    if key in SCREEN_CAPTURE_TRANSLATIONS[normalized]:
        template = SCREEN_CAPTURE_TRANSLATIONS[normalized][key]
    elif normalized == "ko" and key == "language_button":
        template = "English"
    else:
        template = SCREEN_CAPTURE_TRANSLATIONS["en"][key]
    return template.format(**kwargs)


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

    def __init__(self, mode: str, language: str = "en", excluded_handles: set[int] | None = None) -> None:
        super().__init__(None)
        self._mode = mode
        self._language = language
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

        self.selection_made.emit(
            CaptureTarget(mode="region", rect=selection_rect, title=_screen_text(self._language, "custom_area"))
        )
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
            return _screen_text(self._language, "overlay_window_instruction")
        return _screen_text(self._language, "overlay_area_instruction")

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


def _window_is_topmost(window_handle: int) -> bool:
    if system() != "Windows":
        return False

    window_handle = _root_window_handle(window_handle)
    try:
        style = int(ctypes.windll.user32.GetWindowLongW(window_handle, GWL_EXSTYLE))
    except (AttributeError, OSError):
        return False
    return bool(style & WS_EX_TOPMOST)


def _root_window_handle(window_handle: int) -> int:
    if system() != "Windows":
        return window_handle

    try:
        root_handle = int(ctypes.windll.user32.GetAncestor(window_handle, GA_ROOT))
    except (AttributeError, OSError):
        return window_handle
    return root_handle or window_handle


def _set_window_topmost_state(window_handle: int, enabled: bool) -> bool:
    if system() != "Windows":
        return False

    user32 = ctypes.windll.user32
    root_handle = _root_window_handle(window_handle)
    hwnd_insert_after = HWND_TOPMOST if enabled else HWND_NOTOPMOST
    try:
        if user32.IsIconic(root_handle):
            user32.ShowWindow(root_handle, SW_RESTORE)
        else:
            user32.ShowWindow(root_handle, SW_SHOW)
        ok = bool(
            user32.SetWindowPos(
                root_handle,
                hwnd_insert_after,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW,
            )
        )
        if ok and enabled:
            user32.BringWindowToTop(root_handle)
            user32.SetForegroundWindow(root_handle)
            user32.SetActiveWindow(root_handle)
        return ok
    except (AttributeError, OSError):
        return False


class FloatingCaptureController(QWidget):
    resume_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, language: str = "en") -> None:
        super().__init__(None)
        self._language = language
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

        self._resume_button = QPushButton(_screen_text(self._language, "floating_resume"))
        self._pause_button = QPushButton(_screen_text(self._language, "floating_pause"))
        self._stop_button = QPushButton(_screen_text(self._language, "floating_stop"))

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


class RecordingCountdownOverlay(QWidget):
    countdown_finished = pyqtSignal()

    def __init__(self, target_provider) -> None:  # noqa: ANN001
        super().__init__(None)
        self._target_provider = target_provider
        self._remaining = 3
        self._target_rect: QRect | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_countdown)

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

    def start(self, seconds: int = 3) -> None:
        self._remaining = max(1, seconds)
        self._refresh_geometry()
        self.show()
        self.raise_()
        _raise_window_topmost(self)
        self.update()
        self._timer.start(1000)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance_countdown(self) -> None:
        self._remaining -= 1
        if self._remaining <= 0:
            self.stop()
            self.countdown_finished.emit()
            return

        self._refresh_geometry()
        self.update()

    def _refresh_geometry(self) -> None:
        geometry = self._virtual_desktop_geometry()
        self.setGeometry(geometry)

        target = self._target_provider()
        self._target_rect = QRect(target.rect) if target is not None and target.rect is not None else None

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._target_rect is not None:
            local_target_rect = QRect(self._target_rect)
            local_target_rect.translate(-self.geometry().topLeft())
            center = local_target_rect.center()
        else:
            center = self.rect().center()

        badge_size = 140
        badge_rect = QRect(
            center.x() - badge_size // 2,
            center.y() - badge_size // 2,
            badge_size,
            badge_size,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(11, 9, 19, 185))
        painter.drawEllipse(badge_rect)

        base_font = QApplication.font()
        font = QFont(base_font.family(), 54, QFont.Weight.Bold)
        painter.setFont(font)

        shadow_rect = badge_rect.translated(0, 6)
        painter.setPen(QColor(0, 0, 0, 140))
        painter.drawText(shadow_rect, Qt.AlignmentFlag.AlignCenter, str(self._remaining))

        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self._remaining))
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
    language_changed = pyqtSignal(str)

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self._language = language if language in SCREEN_CAPTURE_TRANSLATIONS else "en"
        self.setObjectName("screen_capture_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._save_directory = Path.home()
        self._cv2 = None
        self._recorder = None
        self._preview_timer: QTimer | None = None
        self._recording_state: RecordingState = IDLE
        self._current_frame_bgr: np.ndarray | None = None
        self._frame_intervals: deque[float] = deque(maxlen=FRAME_INTERVAL_WINDOW)
        self._last_frame_timestamp: float | None = None
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
        self._promoted_window_handle: int | None = None
        self._promoted_window_was_topmost = False
        self._floating_controller: FloatingCaptureController | None = None
        self._focus_overlay: RecordingFocusOverlay | None = None
        self._countdown_overlay: RecordingCountdownOverlay | None = None

        self._capture_tabs = QButtonGroup(self)
        self._capture_tabs.setExclusive(True)
        self._frame_rate_buttons = QButtonGroup(self)
        self._frame_rate_buttons.setExclusive(True)

        self._status_label = QLabel(_screen_text(self._language, "status_ready"))
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self._status_label.setWordWrap(True)

        self._recent_capture_name = QLabel(_screen_text(self._language, "no_capture"))
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

        self._record_button = QPushButton(_screen_text(self._language, "record"))
        self._snapshot_button = QPushButton(_screen_text(self._language, "snapshot"))
        self._pause_button = QPushButton(_screen_text(self._language, "pause"))
        self._stop_button = QPushButton(_screen_text(self._language, "stop"))
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
        self._select_target_button.clicked.connect(self._on_select_target_button_clicked)
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
                self.set_status(_screen_text(self._language, "capture_backend_missing", name=exc.name))
                return
            self._cv2 = cv2
            self._recorder = Recorder()

        if self._preview_timer is None:
            self._preview_timer = QTimer(self)
            self._preview_timer.timeout.connect(self._poll_frame)

        self._restart_preview_timer()
        self._poll_frame()
        self.set_status(_screen_text(self._language, "capture_backend_ready"))

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
        self._teardown_countdown_overlay()
        self._restore_promoted_target_window()
        if self._host_window_hidden:
            self._restore_host_window()

        self._recorder = None
        self._cv2 = None
        self._current_frame_bgr = None
        self._last_frame_timestamp = None
        self._frame_intervals.clear()
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

        if self._countdown_overlay is not None and self._countdown_overlay.isVisible():
            return

        if self._recording_state == PAUSED:
            self._recording_started_at = perf_counter()
            self._set_recording_state(RECORDING)
            self.set_status(_screen_text(self._language, "recording_resumed"))
            return

        if self._recording_state == RECORDING:
            return

        if not self._ensure_capture_target_ready("record"):
            return

        if self._capture_mode == "window":
            self._promote_target_window_for_capture()
            QApplication.processEvents()

        self.set_status(_screen_text(self._language, "preparing_capture"))
        self._run_hidden_host_action(self._begin_recording_countdown, restore_after=False)

    def pause_recording(self) -> None:
        if self._recording_state != RECORDING:
            return

        if self._recording_started_at is not None:
            self._elapsed_before_pause += perf_counter() - self._recording_started_at
        self._recording_started_at = None
        self._set_recording_state(PAUSED)
        self.set_status(_screen_text(self._language, "recording_paused"))

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
            self.set_status(_screen_text(self._language, "saved_screen_recording", path=saved_path))
            self.recording_saved.emit(str(saved_path))
        else:
            self.set_status(_screen_text(self._language, "recording_stopped"))

    def capture_snapshot(self) -> None:
        if self._cv2 is None:
            self.start_preview()
        if self._cv2 is None:
            return

        if not self._ensure_capture_target_ready("snapshot"):
            return

        self.set_status(_screen_text(self._language, "capturing_snapshot"))
        restore_after = self._capture_mode != "window"
        self._run_hidden_host_action(self._capture_snapshot_now, restore_after=restore_after)

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

        back_button = QPushButton(_screen_text(self._language, "back_to_menu"))
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel(_screen_text(self._language, "capture_settings"))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")
        subtitle = QLabel(_screen_text(self._language, "capture_settings_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        layout.addWidget(back_button)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title(_screen_text(self._language, "video_settings")))
        layout.addWidget(self._build_output_size_group())
        layout.addLayout(self._build_frame_rate_group())
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title(_screen_text(self._language, "audio_source")))
        layout.addLayout(self._build_audio_group())
        layout.addSpacing(4)
        layout.addWidget(self._build_section_title(_screen_text(self._language, "output")))
        layout.addLayout(self._build_output_group())
        layout.addStretch(1)
        layout.addWidget(self._status_label)

        restore_button = QPushButton(_screen_text(self._language, "restore_defaults"))
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

        badge = QLabel(_screen_text(self._language, "screen_workflow"))
        badge.setStyleSheet(self._badge_style("#1d1730", "#c4b5fd"))

        title = QLabel(_screen_text(self._language, "hero_title"))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel(_screen_text(self._language, "hero_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        helper = QLabel(_screen_text(self._language, "helper"))
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")

        setup_title = QLabel(_screen_text(self._language, "capture_setup"))
        setup_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        setup_hint = QLabel(_screen_text(self._language, "capture_setup_hint"))
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

        recent_title = QLabel(_screen_text(self._language, "recent_capture"))
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
            (_screen_text(self._language, "full_screen"), "full_screen", True),
            (_screen_text(self._language, "window"), "window", False),
            (_screen_text(self._language, "custom"), "region", False),
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

        title = QLabel(_screen_text(self._language, "capture_target"))
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
        caption = QLabel(_screen_text(self._language, "output_size"))
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(caption)
        layout.addWidget(self._output_size_value)
        wrapper.setLayout(layout)
        return wrapper

    def _build_frame_rate_group(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        caption = QLabel(_screen_text(self._language, "frame_rate"))
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
        layout.addLayout(self._build_switch_row(_screen_text(self._language, "system_audio"), self._system_audio_switch))
        layout.addLayout(self._build_switch_row(_screen_text(self._language, "external_mic"), self._external_mic_switch))
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

        caption = QLabel(_screen_text(self._language, "save_path"))
        caption.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; text-transform: uppercase;")

        edit_button = QPushButton(_screen_text(self._language, "edit"))
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

    def _toggle_language(self) -> None:
        self.language_changed.emit("ko" if self._language == "en" else "en")

    def _poll_frame(self) -> None:
        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
            self._current_frame_bgr = None
            if self._recording_state == RECORDING:
                self.stop_recording()
                self.set_status(_screen_text(self._language, "capture_target_unavailable"))
            return

        now = perf_counter()
        if self._last_frame_timestamp is not None:
            interval = now - self._last_frame_timestamp
            if interval > 0:
                self._frame_intervals.append(interval)
        self._last_frame_timestamp = now

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

        live_rect = target.rect
        if target.window_handle is not None:
            refreshed_rect = _window_rect_from_handle(target.window_handle)
            if refreshed_rect is not None:
                live_rect = refreshed_rect
                self._window_target = CaptureTarget(
                    mode=target.mode,
                    rect=refreshed_rect,
                    window_handle=target.window_handle,
                    title=target.title,
                )

        if live_rect is None:
            return None

        return self._crop_image(self._grab_virtual_desktop_image(), live_rect)

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

    def _estimated_capture_fps(self) -> float:
        fallback_fps = float(self._selected_fps())
        if not self._frame_intervals:
            return fallback_fps

        sorted_intervals = sorted(self._frame_intervals)
        trim = max(1, len(sorted_intervals) // 10) if len(sorted_intervals) >= 10 else 0
        stable_intervals = sorted_intervals[trim:-trim] if trim else sorted_intervals
        if not stable_intervals:
            return fallback_fps

        average_interval = sum(stable_intervals) / len(stable_intervals)
        if average_interval <= 0:
            return fallback_fps

        measured_fps = 1.0 / average_interval
        bounded_fps = max(MIN_CAPTURE_FPS, min(MAX_CAPTURE_FPS, measured_fps))
        return round(min(bounded_fps, fallback_fps), 2)

    def _restart_preview_timer(self) -> None:
        if self._preview_timer is None:
            return
        interval_ms = max(8, int(1000 / max(1, self._selected_fps())))
        self._preview_timer.start(interval_ms)

    def _set_recording_state(self, state: RecordingState) -> None:
        self._recording_state = state
        is_recording = state == RECORDING
        is_paused = state == PAUSED

        self._record_button.setText(
            _screen_text(self._language, "resume") if is_paused else _screen_text(self._language, "record")
        )
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
            self.set_status(_screen_text(self._language, "mode_selected_full", mode=mode_label))
        elif self._capture_mode == "window" and system() != "Windows":
            self.set_status(_screen_text(self._language, "window_use_custom_fallback"))
        else:
            self.set_status(_screen_text(self._language, "mode_selected_other", mode=mode_label))

    def _on_select_target_button_clicked(self) -> None:
        if self._capture_mode == "window" and system() != "Windows":
            self._switch_capture_mode("region")
            self.set_status(_screen_text(self._language, "window_use_custom_fallback"))
            return
        self._begin_target_selection()

    def _switch_capture_mode(self, mode_name: str) -> None:
        for button in self._capture_tabs.buttons():
            if str(button.property("captureMode")) != mode_name:
                continue
            button.setChecked(True)
            self._on_capture_mode_changed()
            return

    def _on_frame_rate_changed(self) -> None:
        self._restart_preview_timer()
        self.set_status(_screen_text(self._language, "frame_rate_set", fps=self._selected_fps()))

    def _on_audio_toggle(self, name: str, checked: bool) -> None:
        state = _screen_text(self._language, "enabled") if checked else _screen_text(self._language, "disabled")
        self.set_status(_screen_text(self._language, "audio_toggle", name=name, state=state))

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
        self.set_status(_screen_text(self._language, "defaults_restored"))

    def _build_recording_path(self) -> Path:
        return self._save_directory / f"screen_recording_{self._timestamp_string()}.mp4"

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

    def _sidebar_button_style(self, compact: bool = False) -> str:
        padding = "10px 0" if compact else "10px 14px"
        return (
            f"QPushButton {{"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            f"padding: {padding};"
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
            self.set_status(_screen_text(self._language, "stop_before_target_change"))
            return
        if self._selection_overlay is not None:
            return
        if self._capture_mode == "full_screen":
            self.set_status(_screen_text(self._language, "full_screen_mode_note"))
            return
        if self._capture_mode == "window" and system() != "Windows":
            self._switch_capture_mode("region")
            self.set_status(_screen_text(self._language, "window_use_custom_fallback"))
            return

        self.set_status(_screen_text(self._language, "hide_and_choose_target"))
        self._run_hidden_host_action(self._show_target_selector, restore_after=False)

    def _show_target_selector(self) -> None:
        excluded_handles = self._excluded_window_handles()
        self._selection_overlay = CaptureSelectorOverlay(
            self._capture_mode,
            language=self._language,
            excluded_handles=excluded_handles,
        )
        self._selection_overlay.selection_made.connect(self._on_target_selected)
        self._selection_overlay.selection_cancelled.connect(self._on_target_selection_cancelled)
        self._selection_overlay.show()

    def _on_target_selected(self, target: CaptureTarget) -> None:
        if self._selection_overlay is not None:
            self._selection_overlay.deleteLater()
        self._selection_overlay = None

        if target.mode == "window":
            self._window_target = target
            self.set_status(_screen_text(self._language, "window_selected", title=target.title))
        else:
            self._region_target = target
            if target.rect is not None:
                self.set_status(
                    _screen_text(
                        self._language,
                        "area_selected_size",
                        width=target.rect.width(),
                        height=target.rect.height(),
                    )
                )
            else:
                self.set_status(_screen_text(self._language, "area_selected"))

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
        self.set_status(_screen_text(self._language, "target_selection_cancelled"))

    def _current_target(self) -> CaptureTarget | None:
        if self._capture_mode == "window":
            return self._window_target
        if self._capture_mode == "region":
            return self._region_target
        return CaptureTarget(
            mode="full_screen",
            rect=self._virtual_desktop_geometry(),
            title=_screen_text(self._language, "entire_desktop"),
        )

    def _update_capture_target_ui(self) -> None:
        if self._capture_mode == "full_screen":
            self._target_summary_label.setText(_screen_text(self._language, "entire_desktop"))
            self._target_hint_label.setText(_screen_text(self._language, "desktop_hint"))
            self._select_target_button.setText(_screen_text(self._language, "desktop_ready"))
            self._select_target_button.setEnabled(False)
            self._output_size_value.setText(self._capture_dimensions_text(self._virtual_desktop_geometry()))
            self._window_recording_notice.hide()
            return

        if self._capture_mode == "window":
            target = self._window_target
            self._target_summary_label.setText(target.title if target is not None else _screen_text(self._language, "no_window_selected"))
            if system() == "Windows":
                self._target_hint_label.setText(_screen_text(self._language, "window_hint"))
                self._select_target_button.setText(_screen_text(self._language, "choose_window"))
                self._window_recording_notice.setText(_screen_text(self._language, "window_notice"))
                self._window_recording_notice.show()
            else:
                self._target_hint_label.setText(_screen_text(self._language, "window_use_custom_fallback"))
                self._select_target_button.setText(_screen_text(self._language, "use_custom_mode"))
                self._window_recording_notice.hide()
            self._select_target_button.setEnabled(True)
            self._output_size_value.setText(self._capture_dimensions_text(target.rect if target is not None else None))
            return

        target = self._region_target
        if target is not None and target.rect is not None:
            self._target_summary_label.setText(
                _screen_text(self._language, "area_summary", width=target.rect.width(), height=target.rect.height())
            )
        else:
            self._target_summary_label.setText(_screen_text(self._language, "no_area_selected"))
        self._target_hint_label.setText(_screen_text(self._language, "area_hint"))
        self._select_target_button.setText(_screen_text(self._language, "choose_area"))
        self._select_target_button.setEnabled(True)
        self._output_size_value.setText(self._capture_dimensions_text(target.rect if target is not None else None))
        self._window_recording_notice.hide()

    def _capture_dimensions_text(self, rect: QRect | None) -> str:
        if rect is None:
            return _screen_text(self._language, "matches_target_size")
        return _screen_text(self._language, "saved_at_original_size", width=rect.width(), height=rect.height())

    def _run_hidden_host_action(self, callback, restore_after: bool) -> None:  # noqa: ANN001
        self._hide_host_window()

        def runner() -> None:
            try:
                callback()
            finally:
                if restore_after:
                    self._restore_host_window()

        QTimer.singleShot(HOST_HIDE_DELAY_MS, runner)

    def _begin_recording_countdown(self) -> None:
        if self._countdown_overlay is None:
            self._countdown_overlay = RecordingCountdownOverlay(self._recording_focus_target)
            self._countdown_overlay.countdown_finished.connect(self._start_recording_now)

        self._countdown_overlay.start(seconds=3)

    def _hide_host_window(self) -> None:
        host = self.window()
        if host is None or self._host_window_hidden:
            return

        _set_window_capture_exclusion(host, excluded=True)
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
        _set_window_capture_exclusion(host, excluded=False)
        self._host_window_hidden = False

    def _promote_target_window_for_capture(self) -> None:
        if self._capture_mode != "window":
            return

        target = self._window_target
        if target is None or target.window_handle is None:
            return

        window_handle = _root_window_handle(target.window_handle)
        if self._promoted_window_handle == window_handle:
            _set_window_topmost_state(window_handle, enabled=True)
            return

        self._restore_promoted_target_window()
        self._promoted_window_handle = window_handle
        self._promoted_window_was_topmost = _window_is_topmost(window_handle)
        _set_window_topmost_state(window_handle, enabled=True)

    def _restore_promoted_target_window(self) -> None:
        if self._promoted_window_handle is None:
            return

        if not self._promoted_window_was_topmost:
            _set_window_topmost_state(self._promoted_window_handle, enabled=False)

        self._promoted_window_handle = None
        self._promoted_window_was_topmost = False

    def _teardown_countdown_overlay(self) -> None:
        if self._countdown_overlay is not None:
            self._countdown_overlay.stop()
            self._countdown_overlay.deleteLater()
        self._countdown_overlay = None

    def _start_recording_now(self) -> None:
        self._teardown_countdown_overlay()
        if self._cv2 is None or self._recorder is None:
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "backend_unavailable"))
            return

        self._start_recording_after_promotion()

    def _start_recording_after_promotion(self) -> None:
        if self._cv2 is None or self._recorder is None:
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "backend_unavailable"))
            return

        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "unable_capture_frame"))
            return

        output_path = self._build_recording_path()
        height, width = frame_bgr.shape[:2]
        recording_fps = self._estimated_capture_fps()
        try:
            self._recorder.start(output_path=output_path, fps=recording_fps, size=(width, height))
        except RuntimeError as exc:
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(str(exc))
            return

        self._hidden_for_recording = True
        self._elapsed_before_pause = 0.0
        self._recording_started_at = perf_counter()
        self._set_recording_state(RECORDING)
        self._show_floating_controller()
        self._show_focus_overlay()
        self.set_status(_screen_text(self._language, "recording_to_with_controller", path=output_path))

    def _capture_snapshot_now(self) -> None:
        if self._cv2 is None:
            self.set_status(_screen_text(self._language, "backend_unavailable"))
            return

        if self._capture_mode == "window":
            self._promote_target_window_for_capture()
            QApplication.processEvents()
            QTimer.singleShot(120, self._capture_snapshot_after_promotion)
            return

        self._capture_snapshot_after_promotion()

    def _capture_snapshot_after_promotion(self) -> None:
        if self._cv2 is None:
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "backend_unavailable"))
            return

        frame_bgr = self._grab_screen_frame()
        if frame_bgr is None:
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "unable_capture_snapshot"))
            return

        output_path = self._build_snapshot_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._cv2.imwrite(str(output_path), frame_bgr):
            self._restore_promoted_target_window()
            self._restore_host_window()
            self.set_status(_screen_text(self._language, "unable_save_snapshot", path=output_path))
            return

        self._restore_promoted_target_window()
        self._restore_host_window()
        self.set_recent_capture(output_path.name)
        self.set_status(_screen_text(self._language, "saved_snapshot", path=output_path))
        self.snapshot_saved.emit(str(output_path))

    def _show_floating_controller(self) -> None:
        if self._floating_controller is None:
            self._floating_controller = FloatingCaptureController(language=self._language)
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
        self._teardown_countdown_overlay()
        self._teardown_floating_controller()
        self._teardown_focus_overlay()
        self._restore_promoted_target_window()
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
