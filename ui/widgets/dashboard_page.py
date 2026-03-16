from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


BASE = "#05070b"
HEADER_BG = "#0a0f18"
PANEL = "#0f1724"
PANEL_ALT = "#131d2c"
FOOTER_BG = "#09101a"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#94a3b8"
BORDER = "rgba(148, 163, 184, 0.18)"


@dataclass(slots=True)
class ActivityItem:
    title: str
    timestamp: str
    color: str

class FeatureCard(QFrame):
    clicked = pyqtSignal()

    def __init__(
        self,
        accent_color: str,
        button_hover_color: str,
        surface_color: str,
        border_color: str,
        icon_kind: str,
        title: str,
        description: str,
        action_text: str,
    ) -> None:
        super().__init__()
        self.setObjectName("featureCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(290, 540)
        self.setStyleSheet(
            f"""
            QFrame#featureCard {{
                background: {surface_color};
                border: 1px solid {border_color};
                border-radius: 26px;
            }}
            """
        )

        badge_frame = QFrame()
        badge_frame.setObjectName("featureCardBadge")
        badge_frame.setFixedSize(86, 86)
        badge_frame.setStyleSheet(
            f"""
            QFrame#featureCardBadge {{
                background: {accent_color}22;
                border: 1px solid {accent_color}44;
                border-radius: 43px;
            }}
            """
        )

        badge_label = QLabel()
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setStyleSheet("background: transparent;")
        badge_label.setPixmap(self._build_icon(icon_kind, accent_color))

        badge_layout = QVBoxLayout()
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.addWidget(badge_label, 1)
        badge_frame.setLayout(badge_layout)

        self._title_label = QLabel(title)
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(
            f"background: transparent; color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 800;"
        )

        self._description_label = QLabel(description)
        self._description_label.setWordWrap(True)
        self._description_label.setTextFormat(Qt.TextFormat.RichText)
        self._description_label.setStyleSheet(
            f"background: transparent; color: {TEXT_SECONDARY}; font-size: 14px;"
        )

        self._action_button = QPushButton(action_text)
        self._action_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_button.clicked.connect(self.clicked.emit)
        self._action_button.setMinimumHeight(54)
        self._action_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {accent_color};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 18px;
            }}
            QPushButton:hover {{
                background: {button_hover_color};
                border: 1px solid rgba(255, 255, 255, 0.24);
            }}
            QPushButton:pressed {{
                background: {accent_color};
            }}
            """
        )
        self.set_content(title, description, action_text)

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)
        layout.addWidget(badge_frame, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._description_label, 1)
        layout.addStretch(1)
        layout.addWidget(self._action_button)
        self.setLayout(layout)

    def set_content(self, title: str, description: str, action_text: str) -> None:
        self._title_label.setText(title)
        self._description_label.setText(f"<div style='line-height: 1.55;'>{description}</div>")
        self._action_button.setText(action_text)

    def _build_icon(self, icon_kind: str, color: str) -> QPixmap:
        icon_size = 42
        device_pixel_ratio = 2.0
        pixmap = QPixmap(int(icon_size * device_pixel_ratio), int(icon_size * device_pixel_ratio))
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(device_pixel_ratio)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 2.6)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if icon_kind == "camera":
            painter.drawRoundedRect(8, 13, 26, 17, 4, 4)
            painter.drawEllipse(16, 17, 10, 10)
            painter.drawRoundedRect(13, 9, 8, 5, 2, 2)
        elif icon_kind == "screen":
            painter.drawRoundedRect(6, 9, 30, 19, 4, 4)
            painter.drawLine(17, 31, 25, 31)
            painter.drawLine(21, 28, 21, 31)
        else:
            file_path = QPainterPath()
            file_path.moveTo(12, 8)
            file_path.lineTo(25, 8)
            file_path.lineTo(31, 14)
            file_path.lineTo(31, 33)
            file_path.lineTo(12, 33)
            file_path.closeSubpath()
            painter.drawPath(file_path)
            painter.drawLine(25, 8, 25, 14)
            painter.drawLine(25, 14, 31, 14)
            painter.drawLine(16, 23, 26, 23)
            painter.drawLine(23, 20, 26, 23)
            painter.drawLine(23, 26, 26, 23)

        painter.end()
        return pixmap

class DashboardPage(QWidget):
    webcam_requested = pyqtSignal()
    screen_requested = pyqtSignal()
    convert_requested = pyqtSignal()
    language_changed = pyqtSignal(str)

    def __init__(self, language: str = "en") -> None:
        super().__init__()
        self.setObjectName("dashboard_page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self._language = language if language in ("en", "ko") else "en"

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_content(), 1)
        root_layout.addWidget(self._build_footer())
        self.setLayout(root_layout)
        self.setStyleSheet(
            f"""
            QWidget#dashboard_page {{
                background: {BASE};
            }}
            """
        )
        self._apply_language()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("dashboardHeader")
        header.setFixedHeight(84)
        header.setStyleSheet(
            f"""
            QFrame#dashboardHeader {{
                background: {HEADER_BG};
                border-bottom: 1px solid {BORDER};
            }}
            QFrame#dashboardBrandMark {{
                background: #0a47c2;
                border-radius: 10px;
            }}
            """
        )

        brand_mark = QFrame()
        brand_mark.setObjectName("dashboardBrandMark")
        brand_mark.setFixedSize(36, 36)
        brand_letter = QLabel("F")
        brand_letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_letter.setStyleSheet("color: white; font-size: 18px; font-weight: 800;")
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.addWidget(brand_letter, 1)
        brand_mark.setLayout(brand_layout)

        brand_name = QLabel("flux-recorder")
        brand_name.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 800;")

        self._brand_hint = QLabel()
        self._brand_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(12)
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand_name)
        brand_row.addWidget(self._brand_hint)

        language_switch = QFrame()
        language_switch.setObjectName("languageSwitch")
        language_switch.setStyleSheet(
            """
            QFrame#languageSwitch {
                background: #0f1724;
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 14px;
            }
            """
        )

        self._ko_button = QPushButton("한국어")
        self._en_button = QPushButton("English")
        for button, language in ((self._ko_button, "ko"), (self._en_button, "en")):
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(34)
            button.clicked.connect(lambda _checked, lang=language: self._select_language(lang))
            button.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    color: #94a3b8;
                    border: none;
                    border-radius: 10px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    color: #e2e8f0;
                }
                QPushButton:checked {
                    background: #1d4ed8;
                    color: white;
                }
                """
            )

        language_layout = QHBoxLayout()
        language_layout.setContentsMargins(6, 6, 6, 6)
        language_layout.setSpacing(6)
        language_layout.addWidget(self._ko_button)
        language_layout.addWidget(self._en_button)
        language_switch.setLayout(language_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(26, 16, 26, 16)
        layout.setSpacing(24)
        layout.addLayout(brand_row)
        layout.addStretch(1)
        layout.addWidget(language_switch, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.setLayout(layout)
        return header

    def _build_content(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setObjectName("dashboardScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.viewport().setObjectName("dashboardViewport")
        scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll_area.viewport().setAutoFillBackground(True)
        scroll_area.setStyleSheet(
            f"""
            QScrollArea#dashboardScrollArea,
            QWidget#dashboardViewport {{
                background: {BASE};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {HEADER_BG};
                width: 10px;
                margin: 8px 0 8px 0;
            }}
            QScrollBar::handle:vertical {{
                background: #1f2a3a;
                border-radius: 5px;
                min-height: 40px;
            }}
            """
        )

        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setAutoFillBackground(True)
        container.setStyleSheet(f"background: {BASE};")
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(34, 28, 34, 28)
        container_layout.setSpacing(0)

        shell = QWidget()
        shell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shell.setAutoFillBackground(True)
        shell.setStyleSheet(f"background: {BASE};")
        shell.setMaximumWidth(1360)
        shell_layout = QVBoxLayout()
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(22)

        self._hero_title = QLabel()
        self._hero_title.setWordWrap(True)
        self._hero_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 42px; font-weight: 800;")

        self._hero_subtitle = QLabel()
        self._hero_subtitle.setWordWrap(True)
        self._hero_subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 16px;")

        cards_layout = QGridLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(24)
        cards_layout.setVerticalSpacing(24)
        cards_layout.setColumnStretch(0, 1)
        cards_layout.setColumnStretch(1, 1)
        cards_layout.setColumnStretch(2, 1)
        cards_layout.setRowStretch(0, 1)

        self._webcam_card = FeatureCard(
            accent_color="#2563eb",
            button_hover_color="#3b82f6",
            surface_color="#0e1726",
            border_color="#1d3557",
            icon_kind="camera",
            title="",
            description="",
            action_text="",
        )
        self._screen_card = FeatureCard(
            accent_color="#7c3aed",
            button_hover_color="#8b5cf6",
            surface_color="#231235",
            border_color="#4c1d95",
            icon_kind="screen",
            title="",
            description="",
            action_text="",
        )
        self._convert_card = FeatureCard(
            accent_color="#10b981",
            button_hover_color="#34d399",
            surface_color="#0d201b",
            border_color="#14532d",
            icon_kind="convert",
            title="",
            description="",
            action_text="",
        )

        self._webcam_card.clicked.connect(self.webcam_requested.emit)
        self._screen_card.clicked.connect(self.screen_requested.emit)
        self._convert_card.clicked.connect(self.convert_requested.emit)

        cards_layout.addWidget(self._webcam_card, 0, 0)
        cards_layout.addWidget(self._screen_card, 0, 1)
        cards_layout.addWidget(self._convert_card, 0, 2)

        shell_layout.addWidget(self._hero_title)
        shell_layout.addWidget(self._hero_subtitle)
        shell_layout.addSpacing(8)
        shell_layout.addLayout(cards_layout, 1)
        shell.setLayout(shell_layout)

        shell_row = QHBoxLayout()
        shell_row.setContentsMargins(0, 0, 0, 0)
        shell_row.addStretch(1)
        shell_row.addWidget(shell, 1)
        shell_row.addStretch(1)

        container_layout.addLayout(shell_row)
        container_layout.addStretch(1)
        container.setLayout(container_layout)
        scroll_area.setWidget(container)
        return scroll_area

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("dashboardFooter")
        footer.setFixedHeight(66)
        footer.setStyleSheet(
            f"""
            QFrame#dashboardFooter {{
                background: {FOOTER_BG};
                border-top: 1px solid {BORDER};
            }}
            """
        )

        self._version_label = QLabel()
        self._version_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(self._version_label)

        self._exit_hint = QLabel()
        self._exit_hint.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")

        right_layout = QHBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(self._exit_hint)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)
        layout.addLayout(left_layout)
        layout.addStretch(1)
        layout.addLayout(right_layout)
        footer.setLayout(layout)
        return footer

    def set_language(self, language: str) -> None:
        normalized = language if language in ("en", "ko") else "en"
        if normalized == self._language:
            return
        self._language = normalized
        self._apply_language()

    def _select_language(self, language: str) -> None:
        if language == self._language:
            self._apply_language()
            return
        self._language = language
        self._apply_language()
        self.language_changed.emit(self._language)

    def _apply_language(self) -> None:
        texts = self._translations()[self._language]
        self._brand_hint.setText(texts["brand_hint"])
        self._ko_button.setChecked(self._language == "ko")
        self._en_button.setChecked(self._language == "en")
        self._hero_title.setText(texts["hero_title"])
        self._hero_subtitle.setText(texts["hero_subtitle"])
        self._webcam_card.set_content(texts["webcam_title"], texts["webcam_description"], texts["webcam_action"])
        self._screen_card.set_content(texts["screen_title"], texts["screen_description"], texts["screen_action"])
        self._convert_card.set_content(texts["convert_title"], texts["convert_description"], texts["convert_action"])
        self._version_label.setText(texts["version"])
        self._exit_hint.setText(texts["exit_hint"])

    def _translations(self) -> dict[str, dict[str, str]]:
        return {
            "en": {
                "brand_hint": "OpenCV-powered camera, screen, and conversion tools",
                "language_button": "한국어",
                "hero_title": "Launch the recorder workspace you need.",
                "hero_subtitle": (
                    "Open the camera recorder, start a screen capture session, or convert media files from one focused dashboard."
                ),
                "webcam_title": "Webcam Recorder",
                "webcam_description": (
                    "Preview your connected camera, capture still images, and record OpenCV-powered video clips from one workspace."
                ),
                "webcam_action": "Open Camera",
                "screen_title": "Screen Tools",
                "screen_description": (
                    "Capture the full screen, a single window, or a custom region with a dedicated setup flow before recording."
                ),
                "screen_action": "Start Capture",
                "convert_title": "File Converter",
                "convert_description": (
                    "Convert videos and images with format controls, image sizing options, and progress tracking in one place."
                ),
                "convert_action": "Convert Files",
                "version": "Version 1.0.0",
                "exit_hint": "Press ESC to Exit",
            },
            "ko": {
                "brand_hint": "OpenCV 기반 카메라, 화면 캡처, 파일 변환 도구",
                "language_button": "English",
                "hero_title": "필요한 녹화 작업 공간을 바로 실행하세요.",
                "hero_subtitle": "하나의 대시보드에서 카메라 녹화, 화면 캡처, 파일 변환 작업을 바로 시작할 수 있습니다.",
                "webcam_title": "웹캠 레코더",
                "webcam_description": "연결된 카메라를 미리 보고, 사진을 저장하고, OpenCV 기반 영상 녹화를 한 곳에서 진행합니다.",
                "webcam_action": "카메라 열기",
                "screen_title": "화면 캡처 도구",
                "screen_description": "전체 화면, 특정 창, 또는 원하는 영역을 선택한 뒤 녹화를 시작할 수 있습니다.",
                "screen_action": "캡처 시작",
                "convert_title": "파일 변환기",
                "convert_description": "비디오와 이미지를 원하는 형식과 크기로 변환하고 진행 상태도 함께 확인할 수 있습니다.",
                "convert_action": "파일 변환",
                "version": "버전 1.0.0",
                "exit_hint": "ESC를 눌러 종료",
            },
        }

    def set_recent_activity(self, activities: list[ActivityItem]) -> None:
        del activities
