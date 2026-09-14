import ctypes
import os
import sys
from pathlib import Path


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def main():
    if not _is_admin():
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = ""
        else:
            exe = sys.executable
            params = str(Path(os.path.abspath(__file__)))
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        return

    from PyQt6.QtWidgets import QApplication

    from wfpctl_gui.app import MainWindow

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()