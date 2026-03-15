from __future__ import annotations

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
from ui.widgets.converter_panel import ConverterPanel
from ui.widgets.dashboard_page import ActivityItem, DashboardPage
from ui.widgets.screen_capture_panel import ScreenCapturePanel
from ui.widgets.webcam_page import WebcamPage


class ConverterThread(QThread):
    conversion_finished = pyqtSignal(object)
    conversion_failed = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, request: ConversionRequest) -> None:
        super().__init__()
        self._request = request

    def run(self) -> None:
        self.status_changed.emit(f"Converting {self._request.mode}...")
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
        self._webcam_output_directory = self._default_video_directory()
        self._screen_output_directory = self._default_video_directory()
        self._converter_output_directory = self._default_media_directory()
        self._converter_source_directory = self._default_media_directory()

        self.setWindowTitle(self._window_title(mode))
        self.resize(1480, 980)
        self._switch_mode(mode)

    def _setup_dashboard_mode(self) -> None:
        self.setStyleSheet("")
        self._dashboard_page = DashboardPage()
        self._dashboard_page.webcam_requested.connect(lambda: self._switch_mode(WEBCAM_MODE))
        self._dashboard_page.screen_requested.connect(lambda: self._switch_mode(SCREEN_MODE))
        self._dashboard_page.convert_requested.connect(lambda: self._switch_mode(CONVERT_MODE))
        self._dashboard_page.history_requested.connect(
            lambda: QMessageBox.information(self, "History", "Recent history details will be added next.")
        )
        self._dashboard_page.notifications_requested.connect(
            lambda: QMessageBox.information(self, "Notifications", "Notifications panel will be added next.")
        )
        self._dashboard_page.settings_requested.connect(
            lambda: QMessageBox.information(self, "Settings", "Settings page will be added next.")
        )
        self._dashboard_page.set_recent_activity(self._recent_activity)
        self.setCentralWidget(self._dashboard_page)

    def _setup_webcam_mode(self) -> None:
        self.setStyleSheet("")
        self._webcam_page = WebcamPage()
        self._webcam_page.set_save_path(self._webcam_output_directory)
        self.setCentralWidget(self._webcam_page)

        self._webcam_page.back_requested.connect(self.on_back_to_menu_requested)
        self._webcam_page.browse_save_path_requested.connect(self.on_browse_webcam_save_path_requested)
        self._webcam_page.recording_saved.connect(self.on_recording_saved)
        self._webcam_page.snapshot_saved.connect(self.on_snapshot_saved)
        self._webcam_page.start_preview()

    def _setup_screen_mode(self) -> None:
        self.setStyleSheet("QMainWindow { background: #110f1a; }")
        self._screen_capture_panel = ScreenCapturePanel()
        self._screen_capture_panel.set_output_path(self._screen_output_directory)
        self._screen_capture_panel.back_requested.connect(self.on_back_to_menu_requested)
        self._screen_capture_panel.browse_output_requested.connect(self.on_browse_screen_save_path_requested)
        self._screen_capture_panel.recording_saved.connect(self.on_recording_saved)
        self._screen_capture_panel.snapshot_saved.connect(self.on_snapshot_saved)
        self.setCentralWidget(self._screen_capture_panel)
        self._screen_capture_panel.start_preview()

    def _setup_convert_mode(self) -> None:
        self.setStyleSheet("QMainWindow { background: #0d1511; }")
        self._converter_panel = ConverterPanel()
        self._converter_panel.set_output_path(self._converter_output_directory)
        self._converter_panel.back_requested.connect(self.on_back_to_menu_requested)
        self._converter_panel.browse_output_requested.connect(self.on_browse_converter_output_requested)
        self._converter_panel.browse_source_requested.connect(self.on_browse_converter_source_requested)
        self._converter_panel.convert_requested.connect(self.on_convert_requested)
        self.setCentralWidget(self._converter_panel)

    def on_start_requested(self) -> None:
        if self._webcam_page is not None:
            self._webcam_page.start_or_resume_recording()

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
            "Select save directory",
            str(self._webcam_output_directory),
        )
        if not target_directory:
            return

        self._webcam_output_directory = Path(target_directory)
        if self._webcam_page is not None:
            self._webcam_page.set_save_path(self._webcam_output_directory)
            self._webcam_page.set_status(f"Save path updated to {self._webcam_output_directory}")

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
            "Select screen capture directory",
            str(self._screen_output_directory),
        )
        if not target_directory:
            return

        self._screen_output_directory = Path(target_directory)
        if self._screen_capture_panel is not None:
            self._screen_capture_panel.set_output_path(self._screen_output_directory)
            self._screen_capture_panel.set_status(f"Output directory updated to {self._screen_output_directory}")

    def on_browse_converter_output_requested(self) -> None:
        target_directory = QFileDialog.getExistingDirectory(
            self,
            "Select conversion output directory",
            str(self._converter_output_directory),
        )
        if not target_directory:
            return

        self._converter_output_directory = Path(target_directory)
        if self._converter_panel is not None:
            self._converter_panel.set_output_path(self._converter_output_directory)
            self._converter_panel.set_status(f"Output folder updated to {self._converter_output_directory}")

    def on_browse_converter_source_requested(self, mode: str) -> None:
        if mode == "video":
            title = "Select a video to convert"
            file_filter = "Video Files (*.mp4 *.avi *.mov *.mkv *.m4v *.wmv *.webm)"
        else:
            title = "Select an image to convert"
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

        self._converter_thread = ConverterThread(request)
        self._converter_thread.status_changed.connect(self._set_converter_status)
        self._converter_thread.progress_changed.connect(self._set_converter_progress)
        self._converter_thread.conversion_finished.connect(self.on_conversion_finished)
        self._converter_thread.conversion_failed.connect(self.on_conversion_failed)
        self._converter_thread.finished.connect(self.on_conversion_thread_finished)

        self._set_converter_enabled(False)
        self._begin_converter_progress()
        self._converter_thread.start()

    def on_conversion_finished(self, output_path: Path) -> None:
        self._set_converter_status(f"Converted file saved to {output_path}")
        if self._converter_panel is not None:
            self._converter_panel.set_recent_result(output_path.name)
            self._converter_panel.finish_conversion_progress(success=True)
        self._add_recent_activity(output_path.name, "#10b981")
        QMessageBox.information(self, "Conversion Complete", f"Saved converted file:\n{output_path}")

    def on_conversion_failed(self, message: str) -> None:
        self._set_converter_status("Conversion failed.")
        if self._converter_panel is not None:
            self._converter_panel.finish_conversion_progress(success=False)
        QMessageBox.critical(self, "Conversion Error", message)

    def on_conversion_thread_finished(self) -> None:
        self._set_converter_enabled(True)
        self._converter_thread = None

    def on_back_to_menu_requested(self) -> None:
        if self._converter_thread is not None and self._converter_thread.isRunning():
            QMessageBox.information(self, "Conversion in Progress", "Wait for the current conversion to finish.")
            return

        if self._webcam_page is not None and self._webcam_page.recording_state != IDLE:
            reply = QMessageBox.question(
                self,
                "Stop Recording?",
                "Returning to the menu will stop the current recording. Continue?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if self._screen_capture_panel is not None and self._screen_capture_panel.recording_state != IDLE:
            reply = QMessageBox.question(
                self,
                "Stop Recording?",
                "Returning to the menu will stop the current screen recording. Continue?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._switch_mode(DASHBOARD_MODE)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._mode != WEBCAM_MODE:
            super().keyPressEvent(event)
            return

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
            return "flux-recorder | Dashboard"
        if mode == WEBCAM_MODE:
            return "flux-recorder | Webcam"
        if mode == SCREEN_MODE:
            return "flux-recorder | Screen Tools"
        return "flux-recorder | Converter"

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

    def _add_recent_activity(self, title: str, color: str) -> None:
        self._recent_activity.insert(0, ActivityItem(title=title, timestamp="Just now", color=color))
        self._recent_activity = self._recent_activity[:5]
        if self._dashboard_page is not None:
            self._dashboard_page.set_recent_activity(self._recent_activity)
