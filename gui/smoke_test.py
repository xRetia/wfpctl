import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

import wfpctl_gui.engine as _eng
import wfpctl_gui.dialogs as _dlg
import wfpctl_gui.app as _app
import wfpctl_gui.i18n as _i18n


class StubEngine:
    _exe = "stub"
    available = True

    def list_rules(self, show_all=False, sublayer=""):
        return [{
            "id": 1, "name": "demo", "direction": "out", "action": "block",
            "layer": "ALE_AUTH_CONNECT_V4", "sublayer": "wfpctl SubLayer",
            "weight": "1", "target": "1.2.3.4", "port": "443",
            "protocol": "tcp", "key": "01234567-89AB-CDEF-0123-456789ABCDEF",
        }]

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

    _i18n.set_language(_i18n.EN)
    win = _app.MainWindow()
    win._switch_language(_i18n.EN)  # force English regardless of saved settings
    assert win.windowTitle().startswith("wfpctl"), win.windowTitle()
    assert not win.windowIcon().isNull(), "window icon missing"

    table = win._table
    assert table.columnCount() == 8, f"expected 8 columns, got {table.columnCount()}"
    headers = [table.horizontalHeaderItem(i).text() for i in range(8)]
    assert headers[:2] == ["ID", "Name"], headers
    assert "Sublayer" in headers, headers
    assert win._filter_combo, "sublayer filter combo missing"
    assert win._filter_combo.count() >= 2, "filter combo should have default + all + sublayers"
    assert win._filter_combo.itemText(0) == "Only wfpctl rules", win._filter_combo.itemText(0)
    assert table.rowCount() == 1, f"expected 1 row from stub, got {table.rowCount()}"
    assert "Rules: 1" in win._status_label.text(), win._status_label.text()

    # GUID column should be fixed-width, not stretch
    from PyQt6.QtWidgets import QHeaderView
    guid_mode = table.horizontalHeader().sectionResizeMode(7)
    assert guid_mode == QHeaderView.ResizeMode.Fixed, f"GUID column should be fixed, got {guid_mode}"
    assert win.menuBar(), "menu bar missing"

    toolbar_actions = [a.text() for a in win.findChild(_app.QToolBar).actions()
                       if a.text()]
    assert len(toolbar_actions) == 8, f"expected 8 toolbar buttons, got {toolbar_actions}"
    assert any("Block" in s for s in toolbar_actions), toolbar_actions
    assert any("Allow" in s for s in toolbar_actions), toolbar_actions
    assert any("Export" in s for s in toolbar_actions), toolbar_actions
    assert any("Import" in s for s in toolbar_actions), toolbar_actions

    # language menu exists with two checkable actions
    lang_actions = [a for a in win._lang_menu.actions()]
    assert len(lang_actions) == 2, lang_actions
    assert win._lang_act_en.isChecked(), "English should be default"

    # switching to Chinese updates UI strings
    win._switch_language(_i18n.ZH)
    assert win._lang_act_zh.isChecked(), "Chinese should be checked after switch"
    headers_zh = [table.horizontalHeaderItem(i).text() for i in range(8)]
    assert headers_zh[:2] == ["ID", "名称"], headers_zh
    assert win._filter_combo.itemText(0) == "仅 wfpctl 规则", win._filter_combo.itemText(0)
    win._switch_language(_i18n.EN)

    add = _app.AddRuleDialog()
    vals = add.values()
    assert vals["action"] in ("block", "allow"), vals

    about = _app.AboutDialog(StubEngine())
    assert "wfpctl" in about.windowTitle()

    sub = _app.SublayersDialog(StubEngine())
    assert sub.table.columnCount() == 3, sub.table.columnCount()
    sub_headers = [sub.table.horizontalHeaderItem(i).text() for i in range(3)]
    assert sub_headers == ["Weight", "Name", "GUID"], sub_headers

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())