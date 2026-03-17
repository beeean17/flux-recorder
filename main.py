from __future__ import annotations

import sys
import ctypes
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PyQt6.QtWidgets import QApplication

from core.app_mode import DASHBOARD_MODE
from ui.main_window import MainWindow
from ui.theme import apply_dark_theme

APP_ID = "com.yoon.fluxrecorder"


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
        project_root / "assets" / "app.icns",
        project_root / "assets" / "app.png",
        project_root / "assets" / "icon.ico",
        project_root / "assets" / "icon.icns",
        project_root / "assets" / "icon.png",
    )
    for candidate_path in candidate_paths:
        if not candidate_path.exists():
            continue
        icon = QIcon(str(candidate_path))
        if not icon.isNull():
            return icon
    return QIcon()


def _apply_platform_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _enable_high_dpi_support() -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main() -> int:
    _enable_high_dpi_support()
    _apply_platform_identity()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("flux-recorder")
    app.setDesktopFileName(APP_ID)
    apply_dark_theme(app)
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
