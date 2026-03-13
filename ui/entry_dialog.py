from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_mode import AppMode, CONVERT_MODE, SCREEN_MODE, WEBCAM_MODE


class ModeCard(QFrame):
    def __init__(self, title: str, description: str, action_text: str) -> None:
        super().__init__()
        self._button = QPushButton(action_text)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: 700;")

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #56606b;")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch(1)
        layout.addWidget(self._button)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QFrame {
                background: #f5f7fa;
                border: 1px solid #d8dee6;
                border-radius: 14px;
            }
            QPushButton {
                min-height: 40px;
                border-radius: 10px;
                background: #111827;
                color: white;
                font-weight: 600;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: #1f2937;
            }
            """
        )

    @property
    def button(self) -> QPushButton:
        return self._button


class EntryDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self._selected_mode: AppMode | None = None

        self.setWindowTitle("Choose a workflow")
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        title_label = QLabel("How do you want to start?")
        title_label.setStyleSheet("font-size: 28px; font-weight: 700;")

        description_label = QLabel(
            "Pick one entry point. The main window will open directly in that workflow."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #5b6470; font-size: 14px;")

        webcam_card = ModeCard(
            "Record with Webcam",
            "Open the live camera preview and control start, pause, and stop recording.",
            "Open Webcam Recorder",
        )
        screen_card = ModeCard(
            "Record or Capture Screen",
            "Enter the screen tools flow for full-screen recording or single-frame capture.",
            "Open Screen Tools",
        )
        convert_card = ModeCard(
            "Convert Images and Videos",
            "Choose a file and export it into the target format you need.",
            "Open Converter",
        )

        webcam_card.button.clicked.connect(lambda: self._accept_mode(WEBCAM_MODE))
        screen_card.button.clicked.connect(lambda: self._accept_mode(SCREEN_MODE))
        convert_card.button.clicked.connect(lambda: self._accept_mode(CONVERT_MODE))

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        cards_layout.addWidget(webcam_card)
        cards_layout.addWidget(screen_card)
        cards_layout.addWidget(convert_card)

        cards_container = QWidget()
        cards_container.setLayout(cards_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(cards_container)
        self.setLayout(layout)

    @property
    def selected_mode(self) -> AppMode | None:
        return self._selected_mode

    def _accept_mode(self, mode: AppMode) -> None:
        self._selected_mode = mode
        self.accept()
