from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.converter import SUPPORTED_FORMATS


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
    convert_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("converter_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self._format_combo = QComboBox()
        self._format_combo.addItems(SUPPORTED_FORMATS)
        self._format_combo.setStyleSheet(self._combo_style())
        self._format_combo.currentTextChanged.connect(self._on_format_changed)

        self._convert_button = QPushButton("Choose File and Convert")
        self._convert_button.clicked.connect(self._emit_convert_requested)
        self._convert_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._convert_button.setStyleSheet(self._accent_button_style())

        self._status_label = QLabel("Ready to convert a media file.")
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

        self._selected_format_badge = QLabel(f"Target: {self._format_combo.currentText().upper()}")
        self._selected_format_badge.setStyleSheet(self._badge_style("#163226", "#6ee7b7"))

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

    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_conversion_enabled(self, enabled: bool) -> None:
        self._format_combo.setEnabled(enabled)
        self._convert_button.setEnabled(enabled)

    def set_recent_result(self, filename: str) -> None:
        self._recent_result_name.setText(filename)
        extension = Path(filename).suffix.lower().removeprefix(".") or "FILE"
        self._recent_result_thumb.setText(extension[:4].upper())

    def _emit_convert_requested(self) -> None:
        self.convert_requested.emit(self._format_combo.currentText())

    def _on_format_changed(self, value: str) -> None:
        self._selected_format_badge.setText(f"Target: {value.upper()}")
        self.set_status(f"Output format set to {value.upper()}.")

    def _build_body(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_main_panel(), 1)
        layout.addWidget(self._build_sidebar())
        return layout

    def _build_main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            f"background: {SURFACE}; border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};"
        )

        badge = QLabel("File conversion workspace")
        badge.setStyleSheet(self._badge_style("#11241b", "#86efac"))

        title = QLabel("Convert images and videos with one action.")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")

        subtitle = QLabel("Choose a target format on the right, then pick a file to convert.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")

        helper = QLabel(
            "Supported outputs include MP4, AVI, MOV, MKV, PNG, JPG, WEBP, and GIF."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")

        feature_card = QFrame()
        feature_card.setStyleSheet(
            f"background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 18px;"
        )

        card_title = QLabel("How it works")
        card_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")

        steps = QLabel(
            "1. Select the output format.\n"
            "2. Click the convert button.\n"
            "3. Pick a source image or video.\n"
            "4. Wait for ffmpeg to finish the export."
        )
        steps.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; line-height: 1.5;")

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        card_layout.addWidget(card_title)
        card_layout.addWidget(steps)
        feature_card.setLayout(card_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addWidget(feature_card)
        layout.addStretch(1)
        layout.addWidget(helper, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet(f"background: {SIDEBAR};")

        back_button = QPushButton("Back to Menu")
        back_button.clicked.connect(self.back_requested.emit)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.setStyleSheet(self._sidebar_button_style())

        title = QLabel("Conversion Settings")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")

        subtitle = QLabel("Choose the target format and start a new export.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        format_title = QLabel("Output Format")
        format_title.setStyleSheet(self._section_title_style())

        tips_title = QLabel("Conversion Notes")
        tips_title.setStyleSheet(self._section_title_style())

        tips = QLabel(
            "Files are converted with ffmpeg. If the source already matches the selected extension, "
            "a `_converted` suffix is added."
        )
        tips.setWordWrap(True)
        tips.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        status_card = QFrame()
        status_card.setStyleSheet(
            f"background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 14px;"
        )
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(14, 14, 14, 14)
        status_layout.setSpacing(8)
        status_title = QLabel("Current Status")
        status_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self._status_label)
        status_card.setLayout(status_layout)

        restore_button = QPushButton("Restore Defaults")
        restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_button.clicked.connect(self._restore_defaults)
        restore_button.setStyleSheet(self._sidebar_button_style())

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(18)
        layout.addWidget(back_button)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addWidget(format_title)
        layout.addWidget(self._selected_format_badge, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._format_combo)
        layout.addSpacing(6)
        layout.addWidget(tips_title)
        layout.addWidget(tips)
        layout.addWidget(status_card)
        layout.addStretch(1)
        layout.addWidget(restore_button)
        sidebar.setLayout(layout)
        return sidebar

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFixedHeight(104)
        footer.setStyleSheet(f"background: #09100c; border-top: 1px solid {BORDER};")

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

        format_label = QLabel("Format")
        format_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 10px; font-weight: 700; text-transform: uppercase;"
        )

        format_layout = QVBoxLayout()
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(4)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self._selected_format_badge)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self._convert_button)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(22)
        layout.addLayout(recent_layout, 1)
        layout.addLayout(controls_layout)
        layout.addStretch(1)
        layout.addLayout(format_layout)
        footer.setLayout(layout)
        return footer

    def _restore_defaults(self) -> None:
        self._format_combo.setCurrentIndex(0)
        self.set_status("Defaults restored.")

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

    def _accent_button_style(self) -> str:
        return (
            f"QPushButton {{"
            f"background: {ACCENT};"
            f"color: {TEXT_PRIMARY};"
            "border: none;"
            "border-radius: 12px;"
            "padding: 12px 18px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover { background: #34d399; }"
            "QPushButton:disabled { background: #235a47; color: #a7c8ba; }"
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
