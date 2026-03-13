from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from core.app_mode import DASHBOARD_MODE
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(DASHBOARD_MODE)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
