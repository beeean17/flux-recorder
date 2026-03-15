from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from core.app_mode import DASHBOARD_MODE
from ui.main_window import MainWindow


def _resource_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _apply_app_font(app: QApplication) -> None:
    preferred_families = ("Noto Sans KR", "Noto Sans", "Segoe UI")
    available_families = set(QFontDatabase.families())
    chosen_family = next((family for family in preferred_families if family in available_families), None)
    if chosen_family is None:
        return
    app.setFont(QFont(chosen_family, 10))


def _load_app_icon() -> QIcon:
    project_root = _resource_root()
    candidate_paths = (
        project_root / "assets" / "app.ico",
        project_root / "assets" / "app.png",
        project_root / "assets" / "icon.ico",
        project_root / "assets" / "icon.png",
    )
    for candidate_path in candidate_paths:
        if not candidate_path.exists():
            continue
        icon = QIcon(str(candidate_path))
        if not icon.isNull():
            return icon
    return QIcon()


def main() -> int:
    app = QApplication(sys.argv)
    _apply_app_font(app)
    app_icon = _load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    window = MainWindow(DASHBOARD_MODE)
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
