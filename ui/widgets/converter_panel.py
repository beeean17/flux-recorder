from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.conversion_service import ConversionRequest
from core.image_converter import IMAGE_OUTPUT_FORMATS
from core.video_converter import VIDEO_OUTPUT_FORMATS
from ui.widgets.image_crop_dialog import ImageCropDialog


BASE = "#0d1511"
SIDEBAR = "#122019"
SURFACE = "#08100b"
SURFACE_ALT = "#1a2a21"
ACCENT = "#10b981"
TEXT_PRIMARY = "#ecfdf5"
TEXT_SECONDARY = "#94a3b8"
BORDER = "#244234"

CONVERTER_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "status_initial": "Choose a tab, then pick a source file.",
        "recent_none": "No conversion yet",
        "back_to_menu": "Back to Menu (Esc)",
        "save_location": "Save Location",
        "save_location_subtitle": "Choose where converted files should be saved.",
        "output_folder": "Output Folder",
        "edit": "Edit",
        "workflow": "Workflow",
        "workflow_body": "1. Pick Video or Image.\n2. Choose the source file.\n3. Adjust the available options.\n4. Press Convert in the footer.",
        "badge": "OpenCV conversion workspace",
        "hero_title": "Choose a source first, then convert it.",
        "hero_subtitle": "Video conversion is limited to OpenCV-friendly outputs. Image conversion also supports resizing before export.",
        "helper": "Video outputs: MP4, AVI. Image outputs: PNG, JPG, BMP, ICO. OpenCV video conversion may not keep audio tracks.",
        "video_tab": "Video",
        "image_tab": "Image",
        "video_format": "Video Format",
        "image_size": "Image Size",
        "width": "Width",
        "height": "Height",
        "original_size": "original size",
        "image_format": "Image Format",
        "recent_output": "Recent Output",
        "progress_title": "Conversion Progress",
        "progress_hint_idle": "Progress will appear here after you start a conversion.",
        "progress_hint_start": "Converting the selected {mode} file...",
        "progress_hint_running": "Conversion in progress: {value}% complete.",
        "progress_hint_success": "Conversion finished successfully.",
        "progress_hint_failed": "Conversion did not complete.",
        "progress_done": "Done",
        "progress_failed": "Failed",
        "progress_ready": "Ready",
        "choose_source_before": "Choose a {mode} file before converting.",
        "selected_source": "Selected {mode} source: {name}",
        "mode_selected": "{mode} conversion mode selected.",
        "video_format_set": "Video output format set to {fmt}.",
        "image_format_set": "Image output set to {fmt} at {size}.",
        "image_size_missing": "Enter both width and height for image conversion, or leave both blank to keep the original size.",
        "image_size_invalid": "Image width and height must be positive whole numbers.",
        "source_title_video": "Video Source",
        "source_title_image": "Image Source",
        "choose_video": "Choose Video",
        "choose_image": "Choose Image",
        "crop_image": "Crop",
        "edit_crop": "Edit Crop",
        "crop_not_selected": "No crop selected. The full image will be exported.",
        "crop_selected": "Crop area: {width} x {height} at ({x}, {y})",
        "crop_unavailable": "Choose an image before selecting a crop area.",
        "crop_load_failed": "Unable to open the selected image for cropping.",
        "convert_video": "Convert Video",
        "convert_image": "Convert Image",
        "convert_generic": "Convert",
        "options_title_video": "Video Output Options",
        "options_title_image": "Image Output Options",
        "options_hint_video": "Pick the target video format. The converted file keeps the original frame size, but OpenCV video conversion may omit audio.",
        "options_hint_image": "Pick the output size and format for the exported image.",
        "source_none": "No file selected yet",
        "source_path_video": "Use the button below to choose the video file you want to convert.",
        "source_path_image": "Use the button below to choose the image file you want to convert.",
        "language_button": "한국어",
    },
    "ko": {
        "status_initial": "탭을 고른 뒤 변환할 파일을 선택하세요.",
        "recent_none": "아직 변환된 파일이 없습니다",
        "back_to_menu": "메뉴로 돌아가기 (Esc)",
        "save_location": "저장 위치",
        "save_location_subtitle": "변환된 파일을 저장할 위치를 선택하세요.",
        "output_folder": "저장 폴더",
        "edit": "변경",
        "workflow": "사용 순서",
        "workflow_body": "1. 비디오 또는 이미지를 고릅니다.\n2. 원본 파일을 선택합니다.\n3. 변환 옵션을 조정합니다.\n4. 하단의 변환 버튼을 누릅니다.",
        "badge": "OpenCV 변환 작업 공간",
        "hero_title": "원본 파일을 먼저 고른 뒤 변환하세요.",
        "hero_subtitle": "비디오 변환은 OpenCV에서 안정적으로 처리 가능한 출력 형식으로 제한됩니다. 이미지는 크기 조절 후 저장할 수 있습니다.",
        "helper": "비디오 출력: MP4, AVI. 이미지 출력: PNG, JPG, BMP, ICO. OpenCV 비디오 변환은 오디오를 유지하지 못할 수 있습니다.",
        "video_tab": "비디오",
        "image_tab": "이미지",
        "video_format": "비디오 형식",
        "image_size": "이미지 크기",
        "image_format": "이미지 형식",
        "recent_output": "최근 결과",
        "progress_title": "변환 진행 상태",
        "progress_hint_idle": "변환을 시작하면 이곳에 진행 상태가 표시됩니다.",
        "progress_hint_start": "선택한 {mode} 파일을 변환하는 중입니다...",
        "progress_hint_running": "변환 진행 중: {value}% 완료.",
        "progress_hint_success": "변환이 성공적으로 완료되었습니다.",
        "progress_hint_failed": "변환이 완료되지 않았습니다.",
        "progress_done": "완료",
        "progress_failed": "실패",
        "progress_ready": "대기 중",
        "choose_source_before": "{mode} 파일을 먼저 선택하세요.",
        "selected_source": "선택한 {mode} 원본: {name}",
        "mode_selected": "{mode} 변환 모드를 선택했습니다.",
        "video_format_set": "비디오 출력 형식을 {fmt}(으)로 설정했습니다.",
        "image_format_set": "이미지 출력은 {size}, 형식은 {fmt}(으)로 설정했습니다.",
        "source_title_video": "비디오 원본",
        "source_title_image": "이미지 원본",
        "choose_video": "비디오 선택",
        "choose_image": "이미지 선택",
        "convert_video": "비디오 변환",
        "convert_image": "이미지 변환",
        "convert_generic": "변환",
        "options_title_video": "비디오 출력 옵션",
        "options_title_image": "이미지 출력 옵션",
        "options_hint_video": "출력 비디오 형식을 고르세요. 변환된 파일은 원본 프레임 크기를 유지하지만, OpenCV 비디오 변환은 오디오를 생략할 수 있습니다.",
        "options_hint_image": "저장할 이미지의 크기와 형식을 선택하세요.",
        "source_none": "아직 선택한 파일이 없습니다",
        "source_path_video": "아래 버튼으로 변환할 비디오 파일을 선택하세요.",
        "source_path_image": "아래 버튼으로 변환할 이미지 파일을 선택하세요.",
        "language_button": "English",
    },
}


def _converter_text(language: str, key: str, **kwargs) -> str:
    normalized = language if language in CONVERTER_TRANSLATIONS else "en"
    if key in CONVERTER_TRANSLATIONS[normalized]:
        template = CONVERTER_TRANSLATIONS[normalized][key]
    else:
        template = CONVERTER_TRANSLATIONS["en"][key]
    return template.format(**kwargs)


class ConverterPanel(QWidget):
    back_requested = pyqtSignal()
    browse_output_requested = pyqtSignal()
    browse_source_requested = pyqtSignal(str)
    convert_requested = pyqtSignal(object)
    language_changed = pyqtSignal(str)

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self.setObjectName("converter_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._language = language if language in CONVERTER_TRANSLATIONS else "en"

        self._conversion_mode = "video"
        self._video_source_path: Path | None = None
        self._image_source_path: Path | None = None
        self._image_crop_rect: tuple[int, int, int, int] | None = None
        self._output_directory = Path.home()
        self._conversion_enabled = True

        self._mode_tabs = QButtonGroup(self)
        self._mode_tabs.setExclusive(True)

        self._status_label = QLabel(_converter_text(self._language, "status_initial"))
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._recent_result_name = QLabel(_converter_text(self._language, "recent_none"))
        self._recent_result_name.setStyleSheet("color: #d1fae5; font-size: 13px;")

        self._recent_result_thumb = QLabel("FILE")
        self._recent_result_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._recent_result_thumb.setFixedSize(52, 52)
        self._recent_result_thumb.setStyleSheet(
            """
            QLabel {
                background: #1f3a2c;
                color: #ecfdf5;
                border: 1px solid #2f5f46;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }
            """
        )

        self._output_path_input = QLineEdit()
        self._output_path_input.setReadOnly(True)
        self._output_path_input.setStyleSheet(self._path_input_style())

        self._video_format_combo = QComboBox()
        self._video_format_combo.addItems(VIDEO_OUTPUT_FORMATS)
        self._video_format_combo.setStyleSheet(self._combo_style())
        self._video_format_combo.currentTextChanged.connect(self._on_option_changed)

        self._image_format_combo = QComboBox()
        self._image_format_combo.addItems(IMAGE_OUTPUT_FORMATS)
        self._image_format_combo.setStyleSheet(self._combo_style())
        self._image_format_combo.currentTextChanged.connect(self._on_option_changed)

        self._image_width_input = QLineEdit()
        self._image_width_input.setPlaceholderText("1920")
        self._image_width_input.setValidator(QIntValidator(1, 32768, self))
        self._image_width_input.setStyleSheet(self._number_input_style())
        self._image_width_input.textChanged.connect(self._on_option_changed)

        self._image_height_input = QLineEdit()
        self._image_height_input.setPlaceholderText("1080")
        self._image_height_input.setValidator(QIntValidator(1, 32768, self))
        self._image_height_input.setStyleSheet(self._number_input_style())
        self._image_height_input.textChanged.connect(self._on_option_changed)

        self._source_title_label = QLabel()
        self._source_title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        self._source_name_label = QLabel()
        self._source_name_label.setWordWrap(True)
        self._source_name_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")

        self._source_path_label = QLabel()
        self._source_path_label.setWordWrap(True)
        self._source_path_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._source_button = QPushButton()
        self._source_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._source_button.clicked.connect(self._emit_browse_source_requested)
        self._source_button.setStyleSheet(self._accent_button_style())

        self._crop_button = QPushButton()
        self._crop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._crop_button.clicked.connect(self._open_image_crop_dialog)
        self._crop_button.setStyleSheet(self._sidebar_button_style())

        self._image_crop_label = QLabel()
        self._image_crop_label.setWordWrap(True)
        self._image_crop_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._options_title_label = QLabel()
        self._options_title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        self._options_hint_label = QLabel()
        self._options_hint_label.setWordWrap(True)
        self._options_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._convert_button = QPushButton(_converter_text(self._language, "convert_generic"))
        self._convert_button.clicked.connect(self._emit_convert_requested)
        self._convert_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_button.setStyleSheet(self._accent_button_style())
        self._progress_title_label = QLabel(_converter_text(self._language, "progress_title"))
        self._progress_title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        self._progress_hint_label = QLabel(_converter_text(self._language, "progress_hint_idle"))
        self._progress_hint_label.setWordWrap(True)
        self._progress_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat(_converter_text(self._language, "progress_ready"))
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setStyleSheet(self._progress_bar_style())

        self._video_options_widget = self._build_video_options()
        self._image_options_widget = self._build_image_options()

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._build_body(), 1)
        root.addWidget(self._build_footer())
        self.setLayout(root)
        self.setStyleSheet(
            f"""
            QWidget#converter_panel {{
                background: {BASE};
            }}
            """
        )

        self._sync_mode_ui()
        self._sync_action_state()

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_conversion_enabled(self, enabled: bool) -> None:
        self._conversion_enabled = enabled
        for button in self._mode_tabs.buttons():
            button.setEnabled(enabled)
        self._source_button.setEnabled(enabled)
        self._crop_button.setEnabled(enabled)
        self._video_format_combo.setEnabled(enabled)
        self._image_format_combo.setEnabled(enabled)
        self._image_width_input.setEnabled(enabled)
        self._image_height_input.setEnabled(enabled)
        self._sync_action_state()

    def set_recent_result(self, filename: str) -> None:
        self._recent_result_name.setText(filename)
        extension = Path(filename).suffix.lower().removeprefix(".") or "FILE"
        self._recent_result_thumb.setText(extension[:4].upper())

    def set_output_path(self, path: Path) -> None:
        self._output_directory = path
        self._output_path_input.setText(str(path))

    def set_selected_source(self, mode: str, path: Path) -> None:
        if mode == "video":
            self._video_source_path = path
        else:
            if self._image_source_path != path:
                self._image_crop_rect = None
            self._image_source_path = path
        mode_label = _converter_text(self._language, "video_tab") if mode == "video" else _converter_text(self._language, "image_tab")
        self.set_status(_converter_text(self._language, "selected_source", mode=mode_label, name=path.name))
        self._sync_mode_ui()
        self._sync_action_state()

    def set_image_crop_rect(self, crop_rect: tuple[int, int, int, int] | None) -> None:
        self._image_crop_rect = crop_rect
        self._sync_mode_ui()
        self._sync_action_state()

    def begin_conversion_progress(self) -> None:
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("%p%")
        mode_label = _converter_text(self._language, "video_tab") if self._conversion_mode == "video" else _converter_text(self._language, "image_tab")
        self._progress_hint_label.setText(_converter_text(self._language, "progress_hint_start", mode=mode_label))

    def set_conversion_progress(self, value: int) -> None:
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setValue(max(0, min(100, value)))
        self._progress_hint_label.setText(
            _converter_text(self._language, "progress_hint_running", value=max(0, min(100, value)))
        )

    def finish_conversion_progress(self, success: bool) -> None:
        if success:
            self._progress_bar.setValue(100)
            self._progress_bar.setFormat(_converter_text(self._language, "progress_done"))
            self._progress_hint_label.setText(_converter_text(self._language, "progress_hint_success"))
            return
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(_converter_text(self._language, "progress_failed"))
        self._progress_hint_label.setText(_converter_text(self._language, "progress_hint_failed"))

    def _emit_browse_source_requested(self) -> None:
        self.browse_source_requested.emit(self._conversion_mode)

    def _emit_convert_requested(self) -> None:
        source_path = self._current_source_path()
        if source_path is None:
            mode_label = _converter_text(self._language, "video_tab") if self._conversion_mode == "video" else _converter_text(self._language, "image_tab")
            self.set_status(_converter_text(self._language, "choose_source_before", mode=mode_label))
            return

        if self._conversion_mode == "image":
            try:
                image_size = self._current_image_size()
            except ValueError as exc:
                self.set_status(str(exc))
                return
        else:
            image_size = None

        request = ConversionRequest(
            mode=self._conversion_mode,
            source_path=source_path,
            output_directory=self._output_directory,
            target_format=self._current_target_format(),
            image_size=image_size,
            image_crop=self._image_crop_rect if self._conversion_mode == "image" else None,
        )
        self.convert_requested.emit(request)

    def _build_body(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main_panel(), 1)
        return layout

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("converterSidebar")
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet(
            f"""
            QFrame#converterSidebar {{
                background: {SIDEBAR};
            }}
            """
        )

        back_button = QPushButton(_converter_text(self._language, "back_to_menu"))
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel(_converter_text(self._language, "save_location"))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")

        subtitle = QLabel(_converter_text(self._language, "save_location_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        output_title = QLabel(_converter_text(self._language, "output_folder"))
        output_title.setStyleSheet(self._section_title_style())

        browse_button = QPushButton(_converter_text(self._language, "edit"))
        browse_button.clicked.connect(self.browse_output_requested.emit)
        browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_button.setFixedWidth(68)
        browse_button.setStyleSheet(self._accent_button_style(compact=True))

        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.setSpacing(8)
        output_row.addWidget(self._output_path_input, 1)
        output_row.addWidget(browse_button)

        note_card = QFrame()
        note_card.setObjectName("converterSidebarNote")
        note_card.setStyleSheet(
            f"""
            QFrame#converterSidebarNote {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            """
        )
        note_layout = QVBoxLayout()
        note_layout.setContentsMargins(14, 14, 14, 14)
        note_layout.setSpacing(8)
        note_title = QLabel(_converter_text(self._language, "workflow"))
        note_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        note_body = QLabel(_converter_text(self._language, "workflow_body"))
        note_body.setWordWrap(True)
        note_body.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        note_layout.addWidget(note_title)
        note_layout.addWidget(note_body)
        note_layout.addWidget(self._status_label)
        note_card.setLayout(note_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(18)
        layout.addWidget(back_button)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(output_title)
        layout.addLayout(output_row)
        layout.addWidget(note_card)
        layout.addStretch(1)
        sidebar.setLayout(layout)
        return sidebar

    def _build_main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("converterMainPanel")
        panel.setStyleSheet(
            f"""
            QFrame#converterMainPanel {{
                background: {SURFACE};
                border-left: 1px solid {BORDER};
                border-bottom: 1px solid {BORDER};
            }}
            """
        )

        badge = QLabel(_converter_text(self._language, "badge"))
        badge.setStyleSheet(self._badge_style("#11241b", "#86efac"))

        title = QLabel(_converter_text(self._language, "hero_title"))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel(_converter_text(self._language, "hero_subtitle"))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        tab_container = self._build_mode_tabs()
        source_card = self._build_source_card()
        options_card = self._build_options_card()
        progress_card = self._build_progress_card()

        helper = QLabel(_converter_text(self._language, "helper"))
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addWidget(tab_container)
        layout.addWidget(source_card)
        layout.addWidget(options_card)
        layout.addWidget(progress_card)
        layout.addStretch(1)
        layout.addWidget(helper, 0, Qt.AlignmentFlag.AlignCenter)
        panel.setLayout(layout)
        return panel

    def _build_mode_tabs(self) -> QWidget:
        container = QFrame()
        container.setObjectName("converterModeTabs")
        container.setStyleSheet(
            f"""
            QFrame#converterModeTabs {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        for label, mode, checked in (
            (_converter_text(self._language, "video_tab"), "video", True),
            (_converter_text(self._language, "image_tab"), "image", False),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(checked)
            button.setProperty("conversionMode", mode)
            button.clicked.connect(self._on_mode_changed)
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
                    font-size: 13px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    color: {TEXT_PRIMARY};
                    border-color: {BORDER};
                }}
                QPushButton:checked {{
                    background: rgba(16, 185, 129, 0.18);
                    color: {TEXT_PRIMARY};
                    border-color: {ACCENT};
                }}
                """
            )
            self._mode_tabs.addButton(button)
            layout.addWidget(button, 1)

        container.setLayout(layout)
        return container

    def _build_source_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("converterSourceCard")
        card.setStyleSheet(
            f"""
            QFrame#converterSourceCard {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(10)
        button_row.addWidget(self._source_button, 0, Qt.AlignmentFlag.AlignLeft)
        button_row.addWidget(self._crop_button, 0, Qt.AlignmentFlag.AlignLeft)
        button_row.addStretch(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._source_title_label)
        layout.addWidget(self._source_name_label)
        layout.addWidget(self._source_path_label)
        layout.addWidget(self._image_crop_label)
        layout.addLayout(button_row)
        card.setLayout(layout)
        return card

    def _build_options_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("converterOptionsCard")
        card.setStyleSheet(
            f"""
            QFrame#converterOptionsCard {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(self._options_title_label)
        layout.addWidget(self._options_hint_label)
        layout.addWidget(self._video_options_widget)
        layout.addWidget(self._image_options_widget)
        card.setLayout(layout)
        return card

    def _build_progress_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("converterProgressCard")
        card.setStyleSheet(
            f"""
            QFrame#converterProgressCard {{
                background: {SURFACE_ALT};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(self._progress_title_label)
        layout.addWidget(self._progress_hint_label)
        layout.addWidget(self._progress_bar)
        card.setLayout(layout)
        return card

    def _build_video_options(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        label = QLabel(_converter_text(self._language, "video_format"))
        label.setStyleSheet(self._section_title_style())
        layout.addWidget(label)
        layout.addWidget(self._video_format_combo)

        wrapper.setLayout(layout)
        return wrapper

    def _open_image_crop_dialog(self) -> None:
        if self._image_source_path is None:
            self.set_status(_converter_text(self._language, "crop_unavailable"))
            return

        dialog = ImageCropDialog(
            self._image_source_path,
            crop_rect=self._image_crop_rect,
            language=self._language,
            parent=self,
        )
        if not dialog.is_ready():
            self.set_status(_converter_text(self._language, "crop_load_failed"))
            return

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._image_crop_rect = dialog.selected_crop_rect()
        self._sync_mode_ui()
        self._sync_action_state()
        self.set_status(self._image_crop_summary())

    def _toggle_language(self) -> None:
        self.language_changed.emit("ko" if self._language == "en" else "en")

    def _build_image_options(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        size_label = QLabel(_converter_text(self._language, "image_size"))
        size_label.setStyleSheet(self._section_title_style())
        width_label = QLabel(_converter_text(self._language, "width"))
        width_label.setStyleSheet(self._section_title_style())
        height_label = QLabel(_converter_text(self._language, "height"))
        height_label.setStyleSheet(self._section_title_style())
        format_label = QLabel(_converter_text(self._language, "image_format"))
        format_label.setStyleSheet(self._section_title_style())

        layout.addWidget(size_label)
        size_row = QHBoxLayout()
        size_row.setContentsMargins(0, 0, 0, 0)
        size_row.setSpacing(12)

        width_column = QVBoxLayout()
        width_column.setContentsMargins(0, 0, 0, 0)
        width_column.setSpacing(8)
        width_column.addWidget(width_label)
        width_column.addWidget(self._image_width_input)

        height_column = QVBoxLayout()
        height_column.setContentsMargins(0, 0, 0, 0)
        height_column.setSpacing(8)
        height_column.addWidget(height_label)
        height_column.addWidget(self._image_height_input)

        size_row.addLayout(width_column, 1)
        size_row.addLayout(height_column, 1)
        layout.addLayout(size_row)
        layout.addWidget(format_label)
        layout.addWidget(self._image_format_combo)
        wrapper.setLayout(layout)
        return wrapper

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("converterFooter")
        footer.setFixedHeight(104)
        footer.setStyleSheet(
            f"""
            QFrame#converterFooter {{
                background: #09100c;
                border-top: 1px solid {BORDER};
            }}
            """
        )

        recent_title = QLabel(_converter_text(self._language, "recent_output"))
        recent_title.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: 700; text-transform: uppercase;"
        )

        recent_text_layout = QVBoxLayout()
        recent_text_layout.setContentsMargins(0, 0, 0, 0)
        recent_text_layout.setSpacing(2)
        recent_text_layout.addWidget(recent_title)
        recent_text_layout.addWidget(self._recent_result_name)

        recent_layout = QHBoxLayout()
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(12)
        recent_layout.addWidget(self._recent_result_thumb)
        recent_layout.addLayout(recent_text_layout)
        recent_layout.addStretch(1)

        left_panel = QWidget()
        left_panel.setLayout(recent_layout)

        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(12)
        center_layout.addWidget(self._convert_button)

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

    def _on_mode_changed(self) -> None:
        button = self._mode_tabs.checkedButton()
        if button is None:
            return
        self._conversion_mode = str(button.property("conversionMode"))
        self._sync_mode_ui()
        self._sync_action_state()
        mode_label = _converter_text(self._language, "video_tab") if self._conversion_mode == "video" else _converter_text(self._language, "image_tab")
        self.set_status(_converter_text(self._language, "mode_selected", mode=mode_label))

    def _on_option_changed(self) -> None:
        if self._conversion_mode == "video":
            self.set_status(
                _converter_text(
                    self._language,
                    "video_format_set",
                    fmt=self._video_format_combo.currentText().upper(),
                )
            )
        else:
            size_label = self._image_size_summary()
            format_label = self._image_format_combo.currentText().upper()
            self.set_status(
                _converter_text(
                    self._language,
                    "image_format_set",
                    fmt=format_label,
                    size=size_label.lower(),
                )
            )

    def _sync_mode_ui(self) -> None:
        is_video = self._conversion_mode == "video"
        source_path = self._current_source_path()

        self._source_title_label.setText(
            _converter_text(self._language, "source_title_video")
            if is_video
            else _converter_text(self._language, "source_title_image")
        )
        self._source_button.setText(
            _converter_text(self._language, "choose_video")
            if is_video
            else _converter_text(self._language, "choose_image")
        )
        self._crop_button.setText(
            _converter_text(self._language, "edit_crop")
            if self._image_crop_rect is not None
            else _converter_text(self._language, "crop_image")
        )
        self._convert_button.setText(
            _converter_text(self._language, "convert_video")
            if is_video
            else _converter_text(self._language, "convert_image")
        )
        self._options_title_label.setText(
            _converter_text(self._language, "options_title_video")
            if is_video
            else _converter_text(self._language, "options_title_image")
        )
        self._options_hint_label.setText(
            _converter_text(self._language, "options_hint_video")
            if is_video
            else _converter_text(self._language, "options_hint_image")
        )
        self._video_options_widget.setVisible(is_video)
        self._image_options_widget.setVisible(not is_video)
        self._crop_button.setVisible(not is_video)
        self._image_crop_label.setVisible(not is_video)

        if source_path is None:
            self._source_name_label.setText(_converter_text(self._language, "source_none"))
            self._source_path_label.setText(
                _converter_text(self._language, "source_path_video")
                if is_video
                else _converter_text(self._language, "source_path_image")
            )
            self._image_crop_label.setText(_converter_text(self._language, "crop_not_selected"))
        else:
            self._source_name_label.setText(source_path.name)
            self._source_path_label.setText(str(source_path))
            self._image_crop_label.setText(self._image_crop_summary())

    def _sync_action_state(self) -> None:
        can_convert = self._conversion_enabled and self._current_source_path() is not None
        self._convert_button.setEnabled(can_convert)
        can_crop = self._conversion_enabled and self._conversion_mode == "image" and self._image_source_path is not None
        self._crop_button.setEnabled(can_crop)

    def _current_source_path(self) -> Path | None:
        if self._conversion_mode == "video":
            return self._video_source_path
        return self._image_source_path

    def _current_target_format(self) -> str:
        if self._conversion_mode == "video":
            return self._video_format_combo.currentText()
        return self._image_format_combo.currentText()

    def _current_image_size(self) -> tuple[int, int] | None:
        if self._conversion_mode != "image":
            return None
        width_text = self._image_width_input.text().strip()
        height_text = self._image_height_input.text().strip()

        if not width_text and not height_text:
            return None
        if not width_text or not height_text:
            raise ValueError(_converter_text(self._language, "image_size_missing"))

        try:
            width = int(width_text)
            height = int(height_text)
        except ValueError as exc:
            raise ValueError(_converter_text(self._language, "image_size_invalid")) from exc

        if width <= 0 or height <= 0:
            raise ValueError(_converter_text(self._language, "image_size_invalid"))
        return (width, height)

    def _image_size_summary(self) -> str:
        width_text = self._image_width_input.text().strip()
        height_text = self._image_height_input.text().strip()
        if not width_text and not height_text:
            return _converter_text(self._language, "original_size")
        if width_text and height_text:
            return f"{width_text} x {height_text}"
        return _converter_text(self._language, "image_size_missing")

    def _image_crop_summary(self) -> str:
        if self._image_crop_rect is None:
            return _converter_text(self._language, "crop_not_selected")

        left, top, width, height = self._image_crop_rect
        return _converter_text(
            self._language,
            "crop_selected",
            x=left,
            y=top,
            width=width,
            height=height,
        )

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
            "background: #0d1712;"
            f"color: {TEXT_SECONDARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 10px;"
            "padding: 10px 12px;"
            "font-size: 11px;"
            "}"
        )

    def _number_input_style(self) -> str:
        return (
            f"QLineEdit {{"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 12px;"
            "padding: 10px 12px;"
            "font-size: 12px;"
            "}"
            f"QLineEdit:focus {{ border-color: {ACCENT}; }}"
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
            "QPushButton:disabled { color: #7da791; border-color: #1d3529; }"
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
            "QPushButton:hover { background: #34d399; }"
            "QPushButton:disabled { background: #235a47; color: #a7c8ba; }"
        )

    def _progress_bar_style(self) -> str:
        return (
            "QProgressBar {"
            f"background: {SURFACE_ALT};"
            f"color: {TEXT_PRIMARY};"
            f"border: 1px solid {BORDER};"
            "border-radius: 9px;"
            "text-align: center;"
            "font-size: 11px;"
            "font-weight: 700;"
            "}"
            f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}"
        )

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

    def _section_title_style(self) -> str:
        return (
            f"color: {TEXT_SECONDARY};"
            "font-size: 11px;"
            "font-weight: 700;"
            "text-transform: uppercase;"
        )
