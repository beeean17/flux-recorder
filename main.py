from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QDialog

from ui.entry_dialog import EntryDialog
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    entry_dialog = EntryDialog()
    if entry_dialog.exec() != QDialog.DialogCode.Accepted or entry_dialog.selected_mode is None:
        return 0

    window = MainWindow(entry_dialog.selected_mode)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
