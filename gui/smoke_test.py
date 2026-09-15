import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

import wfpctl_gui.engine as _eng
import wfpctl_gui.dialogs as _dlg
import wfpctl_gui.app as _app


class StubEngine:
    _exe = "stub"
    available = True

    def list_rules(self):
        return []

    def version(self):
        return "1.0.0"

    def list_sublayers(self):
        return [
            {"weight": 65535, "name": "wfpctl SubLayer", "key": "5AF52F9C-EE4D-4A9F-8599-94F0F59E289B"},
            {"weight": 0, "name": "Base Filtering Engine", "key": "E03CCE29-B53E-482A-81A9-8B8B1D3F4B13"},
        ]

    def add_rule(self, **kw):
        return "ok"

    def delete_rule(self, key):
        return True, "ok"

    def delete_sublayer(self, key):
        return True, "ok"

    def export_rules(self, path):
        return 0

    def import_rules(self, path):
        return {"added": 0, "skipped": 0, "failed": 0}


def main() -> int:
    _app.Engine = StubEngine
    _dlg.Engine = StubEngine

    qapp = QApplication(sys.argv)

    win = _app.MainWindow()
    assert win.windowTitle().startswith("wfpctl"), win.windowTitle()
    assert not win.windowIcon().isNull(), "window icon missing"

    table = win._table
    assert table.columnCount() == 7, f"expected 7 columns, got {table.columnCount()}"
    headers = [table.horizontalHeaderItem(i).text() for i in range(7)]
    assert headers[:2] == ["ID", "名称"], headers
    assert "规则数: 0" in win._status_label.text(), win._status_label.text()
    assert win.menuBar(), "menu bar missing"

    toolbar_actions = [a.text() for a in win.findChild(_app.QToolBar).actions()
                       if a.text()]
    assert len(toolbar_actions) == 8, f"expected 8 toolbar buttons, got {toolbar_actions}"
    assert any("阻止" in s for s in toolbar_actions), toolbar_actions
    assert any("允许" in s for s in toolbar_actions), toolbar_actions
    assert any("导出" in s for s in toolbar_actions), toolbar_actions
    assert any("导入" in s for s in toolbar_actions), toolbar_actions

    add = _app.AddRuleDialog()
    vals = add.values()
    assert vals["action"] in ("block", "allow"), vals

    about = _app.AboutDialog(StubEngine())
    assert "wfpctl" in about.windowTitle()

    sub = _app.SublayersDialog(StubEngine())
    assert sub.table.columnCount() == 3, sub.table.columnCount()

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())