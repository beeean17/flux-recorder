from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class ActivityItem:
    title: str
    timestamp: str
    color: str


class SidebarButton(QPushButton):
    def __init__(self, label: str, active: bool = False) -> None:
        super().__init__(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("active", active)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QPushButton {
                text-align: left;
                padding: 14px 18px;
                border-radius: 14px;
                color: #98a2b3;
                background: transparent;
                font-size: 15px;
                font-weight: 600;
                border: none;
            }
            QPushButton:hover {
                color: white;
                background: rgba(255, 255, 255, 0.06);
            }
            QPushButton[active="true"] {
                color: white;
                background: #2a2a2f;
            }
            """
        )


class ActionCard(QFrame):
    clicked = pyqtSignal()

    def __init__(
        self,
        accent_color: str,
        title: str,
        description: str,
        action_text: str,
    ) -> None:
        super().__init__()
        self.setObjectName("actionCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        icon_box = QFrame()
        icon_box.setObjectName("actionCardIconBox")
        icon_box.setFixedSize(72, 72)
        icon_box.setStyleSheet(
            f"""
            QFrame#actionCardIconBox {{
                background: {accent_color}22;
                border-radius: 22px;
                border: 1px solid {accent_color}33;
            }}
            """
        )

        icon_label = QLabel(title.split()[0][:1])
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"color: {accent_color}; font-size: 28px; font-weight: 800;")
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_label, 1)
        icon_box.setLayout(icon_layout)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #98a2b3; font-size: 14px; line-height: 1.6;")

        action_button = QPushButton(action_text)
        action_button.setCursor(Qt.CursorShape.PointingHandCursor)
        action_button.clicked.connect(self.clicked.emit)
        action_button.setStyleSheet(
            f"""
            QPushButton {{
                min-height: 48px;
                border-radius: 14px;
                background: {accent_color};
                color: white;
                font-size: 16px;
                font-weight: 700;
                border: none;
            }}
            QPushButton:hover {{
                background: {accent_color};
                border: 1px solid rgba(255, 255, 255, 0.16);
            }}
            """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)
        layout.addWidget(icon_box, 0)
        layout.addWidget(title_label, 0)
        layout.addWidget(description_label, 1)
        layout.addStretch(1)
        layout.addWidget(action_button, 0)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QFrame#actionCard {
                background: #111214;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 28px;
            }
            """
        )


class ActivityRow(QFrame):
    def __init__(self, item: ActivityItem) -> None:
        super().__init__()
        self.setObjectName("activityRow")

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {item.color}; border-radius: 5px;")

        title_label = QLabel(item.title)
        title_label.setStyleSheet("color: #f3f4f6; font-size: 15px;")

        time_label = QLabel(item.timestamp)
        time_label.setStyleSheet("color: #7c8593; font-size: 13px;")

        left_layout = QHBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(dot)
        left_layout.addWidget(title_label)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addLayout(left_layout)
        layout.addStretch(1)
        layout.addWidget(time_label)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QFrame#activityRow {
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            """
        )


class DashboardPage(QWidget):
    webcam_requested = pyqtSignal()
    screen_requested = pyqtSignal()
    convert_requested = pyqtSignal()
    history_requested = pyqtSignal()
    notifications_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dashboard_page")
        self._activity_layout = QVBoxLayout()
        self._activity_empty_label = QLabel("No recent activity yet.")
        self._activity_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._activity_empty_label.setStyleSheet("color: #7c8593; font-size: 14px;")

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content(), 1)
        self.setLayout(root_layout)
        self.setStyleSheet(
            """
            QWidget#dashboard_page {
                background: #050607;
            }
            """
        )

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("dashboardSidebar")
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(
            """
            QFrame#dashboardSidebar {
                background: #0d0f12;
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
            """
        )

        logo_box = QFrame()
        logo_box.setObjectName("dashboardLogoBox")
        logo_box.setFixedSize(40, 40)
        logo_box.setStyleSheet(
            """
            QFrame#dashboardLogoBox {
                background: #315efb;
                border-radius: 12px;
            }
            """
        )
        logo_label = QLabel("F")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 20px; font-weight: 800;")
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(logo_label, 1)
        logo_box.setLayout(logo_layout)

        brand_label = QLabel("flux-recorder")
        brand_label.setStyleSheet("color: white; font-size: 24px; font-weight: 700;")

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(12)
        brand_row.addWidget(logo_box)
        brand_row.addWidget(brand_label)
        brand_row.addStretch(1)

        dashboard_button = SidebarButton("Dashboard", active=True)
        history_button = SidebarButton("History")
        notifications_button = SidebarButton("Notifications")
        settings_button = SidebarButton("Settings")

        history_button.clicked.connect(self.history_requested.emit)
        notifications_button.clicked.connect(self.notifications_requested.emit)
        settings_button.clicked.connect(self.settings_requested.emit)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(18)
        layout.addLayout(brand_row)
        layout.addSpacing(24)
        layout.addWidget(dashboard_button)
        layout.addWidget(history_button)
        layout.addWidget(notifications_button)
        layout.addStretch(1)
        layout.addWidget(settings_button)
        sidebar.setLayout(layout)
        return sidebar

    def _build_content(self) -> QWidget:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                background: #050607;
                border: none;
            }
            QScrollBar:vertical {
                background: #0d0f12;
                width: 10px;
                margin: 6px 0 6px 0;
            }
            QScrollBar::handle:vertical {
                background: #20242b;
                border-radius: 5px;
                min-height: 40px;
            }
            """
        )

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 34, 40, 34)
        layout.setSpacing(24)

        header_title = QLabel("Welcome back")
        header_title.setStyleSheet("color: white; font-size: 44px; font-weight: 800;")

        header_subtitle = QLabel("What would you like to do today?")
        header_subtitle.setStyleSheet("color: #8b94a3; font-size: 16px;")

        version_badge = QLabel("v1.0.0")
        version_badge.setStyleSheet(
            """
            color: #8b94a3;
            font-size: 13px;
            padding: 8px 16px;
            background: #0d0f12;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 18px;
            """
        )

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addWidget(header_title)
        header_row.addStretch(1)
        header_row.addWidget(version_badge)

        title_block = QVBoxLayout()
        title_block.setSpacing(8)
        title_block.addLayout(header_row)
        title_block.addWidget(header_subtitle)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)

        webcam_card = ActionCard(
            "#2f6bff",
            "Webcam Record & Photo",
            "Capture crystal-clear photos or record high-definition video directly from your connected camera devices.",
            "Open Camera",
        )
        screen_card = ActionCard(
            "#8b5cf6",
            "Screen Capture & Record",
            "Record your desktop or a selected area. The page is ready now and the capture engine can be wired next.",
            "Start Capture",
        )
        convert_card = ActionCard(
            "#10b981",
            "File Converter",
            "Convert images and videos into the target format you need from a dedicated conversion workflow.",
            "Convert Files",
        )

        webcam_card.clicked.connect(self.webcam_requested.emit)
        screen_card.clicked.connect(self.screen_requested.emit)
        convert_card.clicked.connect(self.convert_requested.emit)

        cards_layout.addWidget(webcam_card, 1)
        cards_layout.addWidget(screen_card, 1)
        cards_layout.addWidget(convert_card, 1)

        cards_widget = QWidget()
        cards_widget.setLayout(cards_layout)

        activity_title = QLabel("RECENT ACTIVITY")
        activity_title.setStyleSheet(
            "color: #71798a; font-size: 14px; font-weight: 800; letter-spacing: 2px;"
        )

        activity_container = QFrame()
        activity_container.setObjectName("dashboardActivityContainer")
        activity_container.setStyleSheet(
            """
            QFrame#dashboardActivityContainer {
                background: #0d0f12;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 24px;
            }
            """
        )
        self._activity_layout.setContentsMargins(0, 0, 0, 0)
        self._activity_layout.setSpacing(0)

        activity_layout = QVBoxLayout()
        activity_layout.setContentsMargins(0, 22, 0, 22)
        activity_layout.setSpacing(0)
        activity_layout.addWidget(self._activity_empty_label)
        activity_layout.addLayout(self._activity_layout)
        activity_container.setLayout(activity_layout)

        layout.addLayout(title_block)
        layout.addWidget(cards_widget)
        layout.addSpacing(10)
        layout.addWidget(activity_title)
        layout.addWidget(activity_container)
        layout.addStretch(1)
        container.setLayout(layout)
        scroll_area.setWidget(container)
        return scroll_area

    def set_recent_activity(self, activities: list[ActivityItem]) -> None:
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._activity_empty_label.setVisible(not activities)

        for index, activity in enumerate(activities):
            row = ActivityRow(activity)
            if index == len(activities) - 1:
                row.setStyleSheet(
                    """
                    QFrame#activityRow {
                        border-bottom: none;
                    }
                    """
                )
            self._activity_layout.addWidget(row)
