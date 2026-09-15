import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

import wfpctl_gui.app as _app
import wfpctl_gui.dialogs as _dlg
import wfpctl_gui.i18n as _i18n


class StubEngine:
    _exe = "stub"
    available = True

    def list_rules(self, show_all=False, sublayer=""):
        return [
            {"id": 1, "name": "Block Remote Desktop", "direction": "out", "action": "block",
             "layer": "ALE_AUTH_CONNECT_V4", "sublayer": "wfpctl SubLayer",
             "weight": "Highest", "target": "203.0.113.7", "port": "3389",
             "protocol": "tcp", "key": "01234567-89AB-CDEF-0123-456789ABCDEF"},
            {"id": 2, "name": "Allow Web", "direction": "out", "action": "allow",
             "layer": "ALE_AUTH_CONNECT_V4", "sublayer": "wfpctl SubLayer",
             "weight": "Lowest", "target": "192.0.2.0/24", "port": "443",
             "protocol": "tcp", "key": "11234567-89AB-CDEF-0123-456789ABCDEF"},
            {"id": 3, "name": "Block LAN Scan", "direction": "in", "action": "block",
             "layer": "ALE_AUTH_RECV_ACCEPT_V4", "sublayer": "wfpctl SubLayer",
             "weight": "Custom 100", "target": "10.0.0.0/8", "port": "",
             "protocol": "icmp", "key": "21234567-89AB-CDEF-0123-456789ABCDEF"},
        ]

    def version(self):
        return "1.1.0"

    def list_sublayers(self):
        return [
            {"weight": 65535, "name": "wfpctl SubLayer", "key": "5AF52F9C-EE4D-4A9F-8599-94F0F59E289B"},
            {"weight": 0, "name": "Base Filtering Engine", "key": "E03CCE29-B53E-482A-81A9-8B8B1D3F4B13"},
        ]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    _app.Engine = StubEngine
    _dlg.Engine = StubEngine

    from PyQt6.QtCore import QTimer

    qapp = QApplication(sys.argv)
    _i18n.set_language(lang)

    win = _app.MainWindow()
    win.resize(960, 600)
    win._switch_language(lang)
    win.show()

    def shoot():
        win.repaint()
        qapp.processEvents()
        pm = win.grab()
        ok = pm.save(out)
        print("saved", out, pm.width(), "x", pm.height(), "ok=", ok, "null=", pm.isNull())
        qapp.quit()

    QTimer.singleShot(500, shoot)
    qapp.exec()


if __name__ == "__main__":
    main()