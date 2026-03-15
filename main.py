from __future__ import annotations

import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from core.app_mode import DASHBOARD_MODE
from ui.main_window import MainWindow


def _apply_app_font(app: QApplication) -> None:
    preferred_families = ("Noto Sans KR", "Noto Sans", "Segoe UI")
    available_families = set(QFontDatabase.families())
    chosen_family = next((family for family in preferred_families if family in available_families), None)
    if chosen_family is None:
        return
    app.setFont(QFont(chosen_family, 10))


def main() -> int:
    app = QApplication(sys.argv)
    _apply_app_font(app)
    window = MainWindow(DASHBOARD_MODE)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
