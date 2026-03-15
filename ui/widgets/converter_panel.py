from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
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
from core.image_converter import DEFAULT_IMAGE_SIZE_OPTIONS, IMAGE_OUTPUT_FORMATS, image_size_option_for_label
from core.video_converter import VIDEO_OUTPUT_FORMATS


BASE = "#0d1511"
SIDEBAR = "#122019"
SURFACE = "#08100b"
SURFACE_ALT = "#1a2a21"
ACCENT = "#10b981"
TEXT_PRIMARY = "#ecfdf5"
TEXT_SECONDARY = "#94a3b8"
BORDER = "#244234"


class ConverterPanel(QWidget):
    back_requested = pyqtSignal()
    browse_output_requested = pyqtSignal()
    browse_source_requested = pyqtSignal(str)
    convert_requested = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("converter_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self._conversion_mode = "video"
        self._video_source_path: Path | None = None
        self._image_source_path: Path | None = None
        self._output_directory = Path.home()
        self._conversion_enabled = True

        self._mode_tabs = QButtonGroup(self)
        self._mode_tabs.setExclusive(True)

        self._status_label = QLabel("Choose a tab, then pick a source file.")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._recent_result_name = QLabel("No conversion yet")
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

        self._image_size_combo = QComboBox()
        self._image_size_combo.addItems([label for label, _size in DEFAULT_IMAGE_SIZE_OPTIONS])
        self._image_size_combo.setStyleSheet(self._combo_style())
        self._image_size_combo.currentTextChanged.connect(self._on_option_changed)

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

        self._options_title_label = QLabel()
        self._options_title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        self._options_hint_label = QLabel()
        self._options_hint_label.setWordWrap(True)
        self._options_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self._convert_button = QPushButton("Convert")
        self._convert_button.clicked.connect(self._emit_convert_requested)
        self._convert_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_button.setStyleSheet(self._accent_button_style())
        self._progress_title_label = QLabel("Conversion Progress")
        self._progress_title_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        self._progress_hint_label = QLabel("Progress will appear here after you start a conversion.")
        self._progress_hint_label.setWordWrap(True)
        self._progress_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("Ready")
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
        self._video_format_combo.setEnabled(enabled)
        self._image_format_combo.setEnabled(enabled)
        self._image_size_combo.setEnabled(enabled)
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
            self._image_source_path = path
        self.set_status(f"Selected {mode} source: {path.name}")
        self._sync_mode_ui()
        self._sync_action_state()

    def begin_conversion_progress(self) -> None:
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("%p%")
        self._progress_hint_label.setText(f"Converting the selected {self._conversion_mode} file...")

    def set_conversion_progress(self, value: int) -> None:
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setValue(max(0, min(100, value)))
        self._progress_hint_label.setText(f"Conversion in progress: {max(0, min(100, value))}% complete.")

    def finish_conversion_progress(self, success: bool) -> None:
        if success:
            self._progress_bar.setValue(100)
            self._progress_bar.setFormat("Done")
            self._progress_hint_label.setText("Conversion finished successfully.")
            return
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("Failed")
        self._progress_hint_label.setText("Conversion did not complete.")

    def _emit_browse_source_requested(self) -> None:
        self.browse_source_requested.emit(self._conversion_mode)

    def _emit_convert_requested(self) -> None:
        source_path = self._current_source_path()
        if source_path is None:
            self.set_status(f"Choose a {self._conversion_mode} file before converting.")
            return

        request = ConversionRequest(
            mode=self._conversion_mode,
            source_path=source_path,
            output_directory=self._output_directory,
            target_format=self._current_target_format(),
            image_size=self._current_image_size(),
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

        back_button = QPushButton("Back to Menu")
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel("Save Location")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")

        subtitle = QLabel("Choose where converted files should be saved.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        output_title = QLabel("Output Folder")
        output_title.setStyleSheet(self._section_title_style())

        browse_button = QPushButton("Edit")
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
        note_title = QLabel("Workflow")
        note_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        note_body = QLabel(
            "1. Pick Video or Image.\n"
            "2. Choose the source file.\n"
            "3. Adjust the available options.\n"
            "4. Press Convert in the footer."
        )
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

        badge = QLabel("OpenCV conversion workspace")
        badge.setStyleSheet(self._badge_style("#11241b", "#86efac"))

        title = QLabel("Choose a source first, then convert it.")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel(
            "Video conversion is limited to OpenCV-friendly outputs. Image conversion also supports resizing before export."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        tab_container = self._build_mode_tabs()
        source_card = self._build_source_card()
        options_card = self._build_options_card()
        progress_card = self._build_progress_card()

        helper = QLabel("Video outputs: MP4, AVI. Image outputs: PNG, JPG, BMP, ICO. OpenCV video conversion may not keep audio tracks.")
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
            ("Video", "video", True),
            ("Image", "image", False),
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

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._source_title_label)
        layout.addWidget(self._source_name_label)
        layout.addWidget(self._source_path_label)
        layout.addWidget(self._source_button, 0, Qt.AlignmentFlag.AlignLeft)
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

        label = QLabel("Video Format")
        label.setStyleSheet(self._section_title_style())
        layout.addWidget(label)
        layout.addWidget(self._video_format_combo)

        wrapper.setLayout(layout)
        return wrapper

    def _build_image_options(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        size_label = QLabel("Image Size")
        size_label.setStyleSheet(self._section_title_style())
        format_label = QLabel("Image Format")
        format_label.setStyleSheet(self._section_title_style())

        layout.addWidget(size_label)
        layout.addWidget(self._image_size_combo)
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

        recent_title = QLabel("Recent Output")
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
        self.set_status(f"{self._conversion_mode.title()} conversion mode selected.")

    def _on_option_changed(self) -> None:
        if self._conversion_mode == "video":
            self.set_status(f"Video output format set to {self._video_format_combo.currentText().upper()}.")
        else:
            size_label = self._image_size_combo.currentText()
            format_label = self._image_format_combo.currentText().upper()
            self.set_status(f"Image output set to {format_label} at {size_label.lower()}.")

    def _sync_mode_ui(self) -> None:
        is_video = self._conversion_mode == "video"
        source_path = self._current_source_path()

        self._source_title_label.setText("Video Source" if is_video else "Image Source")
        self._source_button.setText("Choose Video" if is_video else "Choose Image")
        self._convert_button.setText("Convert Video" if is_video else "Convert Image")
        self._options_title_label.setText("Video Output Options" if is_video else "Image Output Options")
        self._options_hint_label.setText(
            "Pick the target video format. The converted file keeps the original frame size, but OpenCV video conversion may omit audio."
            if is_video
            else "Pick the output size and format for the exported image."
        )
        self._video_options_widget.setVisible(is_video)
        self._image_options_widget.setVisible(not is_video)

        if source_path is None:
            self._source_name_label.setText("No file selected yet")
            self._source_path_label.setText(
                "Use the button below to choose the video file you want to convert."
                if is_video
                else "Use the button below to choose the image file you want to convert."
            )
        else:
            self._source_name_label.setText(source_path.name)
            self._source_path_label.setText(str(source_path))

    def _sync_action_state(self) -> None:
        can_convert = self._conversion_enabled and self._current_source_path() is not None
        self._convert_button.setEnabled(can_convert)

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
        return image_size_option_for_label(self._image_size_combo.currentText())

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
