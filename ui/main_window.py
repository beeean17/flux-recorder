from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from platform import system

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from core.app_mode import AppMode, CONVERT_MODE, DASHBOARD_MODE, SCREEN_MODE, WEBCAM_MODE
from core.conversion_service import ConversionRequest, convert
from core.recording_state import IDLE, PAUSED
from ui.theme import MAIN_WINDOW_BACKGROUNDS
from ui.widgets.converter_panel import ConverterPanel, _converter_text
from ui.widgets.dashboard_page import ActivityItem, DashboardPage
from ui.widgets.screen_capture_panel import ScreenCapturePanel, _screen_text
from ui.widgets.webcam_page import WebcamPage, _webcam_text

MAIN_WINDOW_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "select_save_directory": "Select save directory",
        "save_path_updated": "Save path updated to {path}",
        "select_screen_directory": "Select screen capture directory",
        "output_directory_updated": "Output directory updated to {path}",
        "select_conversion_directory": "Select conversion output directory",
        "output_folder_updated": "Output folder updated to {path}",
        "select_video_to_convert": "Select a video to convert",
        "select_image_to_convert": "Select an image to convert",
        "converting_mode": "Converting {mode}...",
        "mode_video": "video",
        "mode_image": "image",
        "converted_file_saved": "Converted file saved to {path}",
        "conversion_complete": "Conversion Complete",
        "saved_converted_file": "Saved converted file:\n{path}",
        "conversion_failed": "Conversion failed.",
        "conversion_error": "Conversion Error",
        "conversion_in_progress": "Conversion in Progress",
        "wait_for_conversion": "Wait for the current conversion to finish.",
        "stop_recording_title": "Stop Recording?",
        "stop_webcam_message": "Returning to the menu will stop the current recording. Continue?",
        "stop_screen_message": "Returning to the menu will stop the current screen recording. Continue?",
        "language_switch_title": "Language Switch",
        "stop_webcam_before_language": "Stop the current webcam recording before changing the language.",
        "stop_screen_before_language": "Stop the current screen recording before changing the language.",
        "wait_before_language": "Wait for the current conversion to finish before changing the language.",
        "dashboard_title": "flux-recorder | Dashboard",
        "webcam_title": "flux-recorder | Webcam",
        "screen_title": "flux-recorder | Screen Tools",
        "converter_title": "flux-recorder | Converter",
    },
    "ko": {
        "select_save_directory": "저장 폴더 선택",
        "save_path_updated": "저장 경로를 {path}(으)로 변경했습니다",
        "select_screen_directory": "화면 캡처 저장 폴더 선택",
        "output_directory_updated": "출력 폴더를 {path}(으)로 변경했습니다",
        "select_conversion_directory": "변환 결과 저장 폴더 선택",
        "output_folder_updated": "저장 폴더를 {path}(으)로 변경했습니다",
        "select_video_to_convert": "변환할 비디오 선택",
        "select_image_to_convert": "변환할 이미지 선택",
        "converting_mode": "{mode} 변환 중...",
        "mode_video": "비디오",
        "mode_image": "이미지",
        "converted_file_saved": "변환 파일을 {path}에 저장했습니다",
        "conversion_complete": "변환 완료",
        "saved_converted_file": "변환된 파일 저장 위치:\n{path}",
        "conversion_failed": "변환에 실패했습니다.",
        "conversion_error": "변환 오류",
        "conversion_in_progress": "변환 진행 중",
        "wait_for_conversion": "현재 진행 중인 변환이 끝날 때까지 기다려 주세요.",
        "stop_recording_title": "녹화를 종료할까요?",
        "stop_webcam_message": "메뉴로 돌아가면 현재 녹화가 종료됩니다. 계속할까요?",
        "stop_screen_message": "메뉴로 돌아가면 현재 화면 녹화가 종료됩니다. 계속할까요?",
        "language_switch_title": "언어 전환",
        "stop_webcam_before_language": "현재 웹캠 녹화를 종료한 뒤 언어를 변경하세요.",
        "stop_screen_before_language": "현재 화면 녹화를 종료한 뒤 언어를 변경하세요.",
        "wait_before_language": "현재 진행 중인 변환이 끝난 뒤 언어를 변경하세요.",
        "dashboard_title": "flux-recorder | 대시보드",
        "webcam_title": "flux-recorder | 웹캠",
        "screen_title": "flux-recorder | 화면 캡처",
        "converter_title": "flux-recorder | 변환기",
    },
}


def _main_text(language: str, key: str, **kwargs) -> str:
    normalized = language if language in MAIN_WINDOW_TRANSLATIONS else "en"
    template = MAIN_WINDOW_TRANSLATIONS[normalized][key]
    return template.format(**kwargs)


class ConverterThread(QThread):
    conversion_finished = pyqtSignal(object)
    conversion_failed = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, request: ConversionRequest, language: str = "en") -> None:
        super().__init__()
        self._request = request
        self._language = language if language in MAIN_WINDOW_TRANSLATIONS else "en"

    def run(self) -> None:
        mode_label = _main_text(
            self._language,
            "mode_video" if self._request.mode == "video" else "mode_image",
        )
        self.status_changed.emit(_main_text(self._language, "converting_mode", mode=mode_label))
        try:
            converted_path = convert(self._request, progress_callback=self.progress_changed.emit)
        except RuntimeError as exc:
            self.conversion_failed.emit(str(exc))
            return

        self.conversion_finished.emit(converted_path)


class MainWindow(QMainWindow):
    def __init__(self, mode: AppMode) -> None:
        super().__init__()
        self._mode = mode
        self._webcam_page: WebcamPage | None = None
        self._converter_panel: ConverterPanel | None = None
        self._screen_capture_panel: ScreenCapturePanel | None = None
        self._dashboard_page: DashboardPage | None = None
        self._converter_thread: ConverterThread | None = None
        self._recent_activity: list[ActivityItem] = []
        self._dashboard_language = "en"
        self._webcam_output_directory = self._default_video_directory()
        self._screen_output_directory = self._default_video_directory()
        self._converter_output_directory = self._default_media_directory()
        self._converter_source_directory = self._default_media_directory()

        self.setWindowTitle(self._window_title(mode))
        self.resize(1480, 980)
        self._switch_mode(mode)

    def _setup_dashboard_mode(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background: {MAIN_WINDOW_BACKGROUNDS['dashboard']}; }}")
        self._dashboard_page = DashboardPage(language=self._dashboard_language)
        self._dashboard_page.webcam_requested.connect(lambda: self._switch_mode(WEBCAM_MODE))
        self._dashboard_page.screen_requested.connect(lambda: self._switch_mode(SCREEN_MODE))
        self._dashboard_page.convert_requested.connect(lambda: self._switch_mode(CONVERT_MODE))
        self._dashboard_page.language_changed.connect(self.on_language_change_requested)
        self._dashboard_page.set_recent_activity(self._recent_activity)
        self.setCentralWidget(self._dashboard_page)

    def _setup_webcam_mode(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background: {MAIN_WINDOW_BACKGROUNDS['webcam']}; }}")
        self._webcam_page = WebcamPage(language=self._dashboard_language)
        self._webcam_page.set_save_path(self._webcam_output_directory)
        self.setCentralWidget(self._webcam_page)

        self._webcam_page.back_requested.connect(self.on_back_to_menu_requested)
        self._webcam_page.browse_save_path_requested.connect(self.on_browse_webcam_save_path_requested)
        self._webcam_page.recording_saved.connect(self.on_recording_saved)
        self._webcam_page.snapshot_saved.connect(self.on_snapshot_saved)
        self._webcam_page.start_preview()

    def _setup_screen_mode(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background: {MAIN_WINDOW_BACKGROUNDS['screen']}; }}")
        self._screen_capture_panel = ScreenCapturePanel(language=self._dashboard_language)
        self._screen_capture_panel.set_output_path(self._screen_output_directory)
        self._screen_capture_panel.back_requested.connect(self.on_back_to_menu_requested)
        self._screen_capture_panel.browse_output_requested.connect(self.on_browse_screen_save_path_requested)
        self._screen_capture_panel.recording_saved.connect(self.on_recording_saved)
        self._screen_capture_panel.snapshot_saved.connect(self.on_snapshot_saved)
        self.setCentralWidget(self._screen_capture_panel)
        self._screen_capture_panel.start_preview()

    def _setup_convert_mode(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background: {MAIN_WINDOW_BACKGROUNDS['convert']}; }}")
        self._converter_panel = ConverterPanel(language=self._dashboard_language)
        self._converter_panel.set_output_path(self._converter_output_directory)
        self._converter_panel.back_requested.connect(self.on_back_to_menu_requested)
        self._converter_panel.browse_output_requested.connect(self.on_browse_converter_output_requested)
        self._converter_panel.browse_source_requested.connect(self.on_browse_converter_source_requested)
        self._converter_panel.convert_requested.connect(self.on_convert_requested)
        self.setCentralWidget(self._converter_panel)

    def on_start_requested(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.toggle_recording()

    def on_pause_requested(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.pause_recording()

    def on_stop_requested(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.stop_recording()

    def on_photo_requested(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.capture_photo()

    def on_browse_webcam_save_path_requested(self) -> None:
        target_directory = QFileDialog.getExistingDirectory(
            self,
            _main_text(self._dashboard_language, "select_save_directory"),
            str(self._webcam_output_directory),
        )
        if not target_directory:
            return

        self._webcam_output_directory = Path(target_directory)
        if self._webcam_page is not None:
            self._webcam_page.set_save_path(self._webcam_output_directory)
            self._webcam_page.set_status(
                _main_text(self._dashboard_language, "save_path_updated", path=self._webcam_output_directory)
            )

    def on_recording_saved(self, saved_path: str) -> None:
        filename = Path(saved_path).name
        self._add_recent_activity(filename, "#2f6bff")
        if self._webcam_page is not None:
            self._webcam_page.set_recent_capture(filename)

    def on_snapshot_saved(self, saved_path: str) -> None:
        filename = Path(saved_path).name
        self._add_recent_activity(filename, "#ffffff")
        if self._webcam_page is not None:
            self._webcam_page.set_recent_capture(filename)

    def on_browse_screen_save_path_requested(self) -> None:
        target_directory = QFileDialog.getExistingDirectory(
            self,
            _main_text(self._dashboard_language, "select_screen_directory"),
            str(self._screen_output_directory),
        )
        if not target_directory:
            return

        self._screen_output_directory = Path(target_directory)
        if self._screen_capture_panel is not None:
            self._screen_capture_panel.set_output_path(self._screen_output_directory)
            self._screen_capture_panel.set_status(
                _main_text(self._dashboard_language, "output_directory_updated", path=self._screen_output_directory)
            )

    def on_browse_converter_output_requested(self) -> None:
        target_directory = QFileDialog.getExistingDirectory(
            self,
            _main_text(self._dashboard_language, "select_conversion_directory"),
            str(self._converter_output_directory),
        )
        if not target_directory:
            return

        self._converter_output_directory = Path(target_directory)
        if self._converter_panel is not None:
            self._converter_panel.set_output_path(self._converter_output_directory)
            self._converter_panel.set_status(
                _main_text(self._dashboard_language, "output_folder_updated", path=self._converter_output_directory)
            )

    def on_browse_converter_source_requested(self, mode: str) -> None:
        if mode == "video":
            title = _main_text(self._dashboard_language, "select_video_to_convert")
            file_filter = "Video Files (*.mp4 *.avi *.mov *.mkv *.m4v *.wmv *.webm)"
        else:
            title = _main_text(self._dashboard_language, "select_image_to_convert")
            file_filter = "Image Files (*.png *.jpg *.jpeg *.bmp *.webp *.ico)"

        source_path_str, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(self._converter_source_directory),
            file_filter,
        )
        if not source_path_str:
            return

        source_path = Path(source_path_str)
        self._converter_source_directory = source_path.parent
        if self._converter_panel is not None:
            self._converter_panel.set_selected_source(mode, source_path)

    def on_convert_requested(self, request: ConversionRequest) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            return

        self._converter_thread = ConverterThread(request, language=self._dashboard_language)
        self._converter_thread.status_changed.connect(self._set_converter_status)
        self._converter_thread.progress_changed.connect(self._set_converter_progress)
        self._converter_thread.conversion_finished.connect(self.on_conversion_finished)
        self._converter_thread.conversion_failed.connect(self.on_conversion_failed)
        self._converter_thread.finished.connect(self.on_conversion_thread_finished)

        self._set_converter_enabled(False)
        self._begin_converter_progress()
        self._converter_thread.start()

    def on_conversion_finished(self, output_path: Path) -> None:
        self._set_converter_status(_main_text(self._dashboard_language, "converted_file_saved", path=output_path))
        if self._converter_panel is not None:
            self._converter_panel.set_recent_result(output_path.name)
            self._converter_panel.finish_conversion_progress(success=True)
        self._add_recent_activity(output_path.name, "#10b981")
        QMessageBox.information(
            self,
            _main_text(self._dashboard_language, "conversion_complete"),
            _main_text(self._dashboard_language, "saved_converted_file", path=output_path),
        )

    def on_conversion_failed(self, message: str) -> None:
        self._set_converter_status(_main_text(self._dashboard_language, "conversion_failed"))
        if self._converter_panel is not None:
            self._converter_panel.finish_conversion_progress(success=False)
        QMessageBox.critical(self, _main_text(self._dashboard_language, "conversion_error"), message)

    def on_conversion_thread_finished(self) -> None:
        self._set_converter_enabled(True)
        self._converter_thread = None

    def on_back_to_menu_requested(self) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            QMessageBox.information(
                self,
                _main_text(self._dashboard_language, "conversion_in_progress"),
                _main_text(self._dashboard_language, "wait_for_conversion"),
            )
            return

        if self._webcam_page is not None and self._webcam_page.recording_state != IDLE:
            reply = QMessageBox.question(
                self,
                _main_text(self._dashboard_language, "stop_recording_title"),
                _main_text(self._dashboard_language, "stop_webcam_message"),
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self._screen_capture_panel is not None and self._screen_capture_panel.recording_state != IDLE:
            reply = QMessageBox.question(
                self,
                _main_text(self._dashboard_language, "stop_recording_title"),
                _main_text(self._dashboard_language, "stop_screen_message"),
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._switch_mode(DASHBOARD_MODE)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.isAutoRepeat():
            event.ignore()
            return

        if self._mode == WEBCAM_MODE and event.key() == Qt.Key.Key_Space:
            self.on_start_requested()
            event.accept()
            return
        if self._mode == WEBCAM_MODE and event.key() == Qt.Key.Key_P:
            self.on_pause_requested()
            event.accept()
            return
        if self._mode == WEBCAM_MODE and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.on_stop_requested()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._mode == DASHBOARD_MODE:
                self.close()
            else:
                self.on_back_to_menu_requested()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            self._converter_thread.wait()
        if self._webcam_page is not None:
            self._webcam_page.stop_preview()
        if self._screen_capture_panel is not None:
            self._screen_capture_panel.stop_preview()
        event.accept()

    def _default_video_directory(self) -> Path:
        home = Path.home()
        return home / ("Videos" if system() == "Windows" else "Movies")

    def _default_media_directory(self) -> Path:
        return Path.home()

    def _timestamp_string(self) -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _window_title(self, mode: AppMode) -> str:
        if mode == DASHBOARD_MODE:
            return _main_text(self._dashboard_language, "dashboard_title")
        if mode == WEBCAM_MODE:
            return _main_text(self._dashboard_language, "webcam_title")
        if mode == SCREEN_MODE:
            return _main_text(self._dashboard_language, "screen_title")
        return _main_text(self._dashboard_language, "converter_title")

    def _switch_mode(self, mode: AppMode) -> None:
        self._teardown_current_mode()
        self._mode = mode
        self.setWindowTitle(self._window_title(mode))

        if mode == DASHBOARD_MODE:
            self._setup_dashboard_mode()
        elif mode == WEBCAM_MODE:
            self._setup_webcam_mode()
        elif mode == SCREEN_MODE:
            self._setup_screen_mode()
        else:
            self._setup_convert_mode()

    def _teardown_current_mode(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.stop_preview()
        if self._screen_capture_panel is not None:
            self._screen_capture_panel.stop_preview()
        self._webcam_page = None
        self._converter_panel = None
        self._screen_capture_panel = None
        self._dashboard_page = None

        old_central_widget = self.centralWidget()
        if old_central_widget is not None:
            old_central_widget.deleteLater()

    def _set_converter_status(self, message: str) -> None:
        if self._converter_panel is not None:
            self._converter_panel.set_status(message)

    def _set_converter_progress(self, value: int) -> None:
        if self._converter_panel is not None:
            self._converter_panel.set_conversion_progress(value)

    def _set_converter_enabled(self, enabled: bool) -> None:
        if self._converter_panel is not None:
            self._converter_panel.set_conversion_enabled(enabled)

    def _begin_converter_progress(self) -> None:
        if self._converter_panel is not None:
            self._converter_panel.begin_conversion_progress()

    def on_language_change_requested(self, language: str) -> None:
        normalized = language if language in ("en", "ko") else "en"
        if normalized == self._dashboard_language and self._mode == DASHBOARD_MODE:
            return

        if self._mode == WEBCAM_MODE and self._webcam_page is not None and self._webcam_page.recording_state != IDLE:
            QMessageBox.information(
                self,
                _main_text(self._dashboard_language, "language_switch_title"),
                _main_text(self._dashboard_language, "stop_webcam_before_language"),
            )
            return

        if (
            self._mode == SCREEN_MODE
            and self._screen_capture_panel is not None
            and self._screen_capture_panel.recording_state != IDLE
        ):
            QMessageBox.information(
                self,
                _main_text(self._dashboard_language, "language_switch_title"),
                _main_text(self._dashboard_language, "stop_screen_before_language"),
            )
            return

        if self._converter_thread is not None and self._converter_thread.isRunning():
            QMessageBox.information(
                self,
                _main_text(self._dashboard_language, "language_switch_title"),
                _main_text(self._dashboard_language, "wait_before_language"),
            )
            return

        state = self._snapshot_current_mode_state()
        self._dashboard_language = normalized

        if self._mode == DASHBOARD_MODE:
            self.setWindowTitle(self._window_title(self._mode))
            return

        current_mode = self._mode
        self._switch_mode(current_mode)
        self._restore_current_mode_state(current_mode, state)

    def _snapshot_current_mode_state(self) -> dict[str, object]:
        if self._mode == WEBCAM_MODE and self._webcam_page is not None:
            recent_capture = self._webcam_page._recent_capture_name.text()
            if recent_capture == _webcam_text(self._dashboard_language, "no_capture"):
                recent_capture = None
            return {
                "camera_index": self._webcam_page._camera_index,
                "recent_capture": recent_capture,
            }

        if self._mode == SCREEN_MODE and self._screen_capture_panel is not None:
            recent_capture = self._screen_capture_panel._recent_capture_name.text()
            if recent_capture == _screen_text(self._dashboard_language, "no_capture"):
                recent_capture = None
            return {
                "capture_mode": self._screen_capture_panel._capture_mode,
                "window_target": deepcopy(self._screen_capture_panel._window_target),
                "region_target": deepcopy(self._screen_capture_panel._region_target),
                "fps": self._screen_capture_panel._selected_fps(),
                "system_audio": self._screen_capture_panel._system_audio_switch.isChecked(),
                "external_mic": self._screen_capture_panel._external_mic_switch.isChecked(),
                "recent_capture": recent_capture,
            }

        if self._mode == CONVERT_MODE and self._converter_panel is not None:
            recent_result = self._converter_panel._recent_result_name.text()
            if recent_result == _converter_text(self._dashboard_language, "recent_none"):
                recent_result = None
            return {
                "conversion_mode": self._converter_panel._conversion_mode,
                "video_source": self._converter_panel._video_source_path,
                "image_source": self._converter_panel._image_source_path,
                "video_format": self._converter_panel._video_format_combo.currentText(),
                "image_format": self._converter_panel._image_format_combo.currentText(),
                "image_size": self._converter_panel._image_size_combo.currentText(),
                "recent_result": recent_result,
            }

        return {}

    def _restore_current_mode_state(self, mode: AppMode, state: dict[str, object]) -> None:
        if mode == WEBCAM_MODE and self._webcam_page is not None:
            camera_index = state.get("camera_index")
            if isinstance(camera_index, int) and self._webcam_page._video_device_combo is not None:
                combo_index = self._webcam_page._video_device_combo.findData(camera_index)
                if combo_index >= 0:
                    self._webcam_page._video_device_combo.setCurrentIndex(combo_index)
            recent_capture = state.get("recent_capture")
            if isinstance(recent_capture, str):
                self._webcam_page.set_recent_capture(recent_capture)
            return

        if mode == SCREEN_MODE and self._screen_capture_panel is not None:
            self._screen_capture_panel._window_target = deepcopy(state.get("window_target"))
            self._screen_capture_panel._region_target = deepcopy(state.get("region_target"))
            self._screen_capture_panel._system_audio_switch.setChecked(bool(state.get("system_audio", True)))
            self._screen_capture_panel._external_mic_switch.setChecked(bool(state.get("external_mic", False)))

            fps = state.get("fps")
            if isinstance(fps, int):
                for button in self._screen_capture_panel._frame_rate_buttons.buttons():
                    button.setChecked(button.text() == str(fps))
                self._screen_capture_panel._restart_preview_timer()

            capture_mode = state.get("capture_mode")
            if isinstance(capture_mode, str):
                for button in self._screen_capture_panel._capture_tabs.buttons():
                    button.setChecked(str(button.property("captureMode")) == capture_mode)
                self._screen_capture_panel._capture_mode = capture_mode

            self._screen_capture_panel._update_capture_target_ui()
            recent_capture = state.get("recent_capture")
            if isinstance(recent_capture, str):
                self._screen_capture_panel.set_recent_capture(recent_capture)
            return

        if mode == CONVERT_MODE and self._converter_panel is not None:
            video_format = state.get("video_format")
            if isinstance(video_format, str):
                self._converter_panel._video_format_combo.setCurrentText(video_format)
            image_format = state.get("image_format")
            if isinstance(image_format, str):
                self._converter_panel._image_format_combo.setCurrentText(image_format)
            image_size = state.get("image_size")
            if isinstance(image_size, str):
                self._converter_panel._image_size_combo.setCurrentText(image_size)

            video_source = state.get("video_source")
            if isinstance(video_source, Path):
                self._converter_panel.set_selected_source("video", video_source)
            image_source = state.get("image_source")
            if isinstance(image_source, Path):
                self._converter_panel.set_selected_source("image", image_source)

            conversion_mode = state.get("conversion_mode")
            if isinstance(conversion_mode, str):
                for button in self._converter_panel._mode_tabs.buttons():
                    button.setChecked(str(button.property("conversionMode")) == conversion_mode)
                self._converter_panel._conversion_mode = conversion_mode
                self._converter_panel._sync_mode_ui()
                self._converter_panel._sync_action_state()

            recent_result = state.get("recent_result")
            if isinstance(recent_result, str):
                self._converter_panel.set_recent_result(recent_result)

    def _add_recent_activity(self, title: str, color: str) -> None:
        self._recent_activity.insert(0, ActivityItem(title=title, timestamp="Just now", color=color))
        self._recent_activity = self._recent_activity[:5]
        if self._dashboard_page is not None:
            self._dashboard_page.set_recent_activity(self._recent_activity)
