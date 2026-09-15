from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from wfpctl_gui.dialogs import AboutDialog, AddRuleDialog, SublayersDialog
from wfpctl_gui.engine import Engine
from wfpctl_gui.icons import app_icon


LAYER_SHORT = {
    "ALE_AUTH_CONNECT_V4": "出站 V4",
    "ALE_AUTH_CONNECT_V6": "出站 V6",
    "ALE_AUTH_RECV_ACCEPT_V4": "入站 V4",
    "ALE_AUTH_RECV_ACCEPT_V6": "入站 V6",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("wfpctl - Windows 防火墙控制台 (管理员)")
        self.setWindowIcon(app_icon())
        self.resize(960, 600)

        self._engine = Engine()

        self._show_all = False
        self._sub_filter = ""

        self._build_menu()
        self._build_toolbar()
        self._build_table()
        self._build_statusbar()
        self._connect_signals()
        self._refresh_sublayers()
        self._refresh_rules()

    def _build_menu(self) -> None:
        mb = self.menuBar()

        style = self.style()

        file_menu = mb.addMenu("文件")
        self._act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "刷新规则", self)
        self._act_refresh.setShortcut("F5")
        file_menu.addAction(self._act_refresh)
        file_menu.addSeparator()
        self._act_export = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "导出规则…", self)
        self._act_export.setShortcut("Ctrl+E")
        file_menu.addAction(self._act_export)
        self._act_import = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "导入规则…", self)
        self._act_import.setShortcut("Ctrl+I")
        file_menu.addAction(self._act_import)
        file_menu.addSeparator()
        act_quit = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "退出", self)
        act_quit.setShortcut("Alt+F4")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        rule_menu = mb.addMenu("规则")
        self._act_add_block = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical), "添加阻止规则", self)
        rule_menu.addAction(self._act_add_block)
        self._act_add_allow = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation), "添加允许规则", self)
        rule_menu.addAction(self._act_add_allow)
        rule_menu.addSeparator()
        self._act_delete = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "删除所选", self)
        rule_menu.addAction(self._act_delete)

        tool_menu = mb.addMenu("工具")
        self._act_sublayers = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "查看子层", self)
        tool_menu.addAction(self._act_sublayers)
        tool_menu.addSeparator()
        self._act_cleanup = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton), "清理全部规则", self)
        tool_menu.addAction(self._act_cleanup)

        help_menu = mb.addMenu("帮助")
        self._act_about = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion), "关于", self)
        help_menu.addAction(self._act_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("工具栏")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(tb)

        style = self.style()

        tb.addAction(self._act_add_block)
        tb.addAction(self._act_add_allow)
        tb.addAction(self._act_delete)
        tb.addSeparator()
        tb.addAction(self._act_refresh)
        tb.addAction(self._act_export)
        tb.addAction(self._act_import)
        tb.addSeparator()
        tb.addAction(self._act_sublayers)
        tb.addAction(self._act_cleanup)

    def _build_table(self) -> None:
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(["ID", "名称", "方向", "动作", "层", "子层", "权重", "GUID"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self._guid_col = header.sectionSizeHint(7)
        guid_w = self._table.fontMetrics().horizontalAdvance("00000000-0000-0000-0000-000000000000") + 24
        header.resizeSection(7, max(self._guid_col, guid_w))
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.setStyleSheet(
            "QTableWidget::item:selected { background-color: #0078D7; color: white; }"
        )

        self._filter_combo = QComboBox()
        self._filter_combo.addItem("仅 wfpctl 规则", "")
        self._filter_combo.addItem("所有子层 (All)", "__all__")
        self._filter_combo.setToolTip("按子层筛选规则")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(6, 4, 6, 0)
        vbox.addWidget(self._filter_combo)
        vbox.addWidget(self._table)
        self.setCentralWidget(container)

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self._status_label = QLabel("规则数: 0")
        sb.addWidget(self._status_label)
        self._status_msg = QLabel("")
        sb.addPermanentWidget(self._status_msg)

    def _connect_signals(self) -> None:
        self._act_refresh.triggered.connect(self._refresh_rules)
        self._act_export.triggered.connect(self._export_rules)
        self._act_import.triggered.connect(self._import_rules)
        self._act_add_block.triggered.connect(lambda: self._add_rule("block"))
        self._act_add_allow.triggered.connect(lambda: self._add_rule("allow"))
        self._act_delete.triggered.connect(self._delete_selected)
        self._act_sublayers.triggered.connect(self._show_sublayers)
        self._act_cleanup.triggered.connect(self._cleanup_all)
        self._act_about.triggered.connect(self._show_about)
        self._table.customContextMenuRequested.connect(self._context_menu)

    def _set_status(self, msg: str, temporary: bool = True) -> None:
        if temporary:
            self._status_msg.setText(msg)
            QTimer.singleShot(2000, lambda: self._status_msg.setText(""))
        else:
            self._status_label.setText(msg)

    def _refresh_sublayers(self) -> None:
        if not self._engine.available:
            return
        current = self._filter_combo.currentData()
        try:
            sublayers = self._engine.list_sublayers()
        except Exception:
            sublayers = []
        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        self._filter_combo.addItem("仅 wfpctl 规则", "")
        self._filter_combo.addItem("所有子层 (All)", "__all__")
        for s in sublayers:
            name = s.get("name", "")
            key = s.get("key", "")
            self._filter_combo.addItem(f"{name}  [{key}]", key)
        idx = self._filter_combo.findData(current)
        if idx >= 0:
            self._filter_combo.setCurrentIndex(idx)
        else:
            self._filter_combo.setCurrentIndex(0)
        self._filter_combo.blockSignals(False)

    def _on_filter_changed(self) -> None:
        data = self._filter_combo.currentData()
        self._show_all = data == "__all__"
        self._sub_filter = "" if data in (None, "", "__all__") else str(data)
        self._refresh_rules()

    def _refresh_rules(self) -> None:
        if not self._engine.available:
            QMessageBox.critical(
                self,
                "引擎未找到",
                "未找到 wfpctl 可执行文件。\n请确保 wfpctl.exe 在程序目录或 PATH 中。",
            )
            return

        rules = self._engine.list_rules(show_all=self._show_all, sublayer=self._sub_filter)
        self._table.setRowCount(0)
        self._table.setRowCount(len(rules))

        allow_brush = QBrush(QColor(0, 150, 0))
        block_brush = QBrush(QColor(200, 0, 0))

        for i, r in enumerate(rules):
            items = [
                str(r.get("id", "")),
                r.get("name", ""),
                r.get("direction", ""),
                r.get("action", ""),
                LAYER_SHORT.get(r.get("layer", ""), r.get("layer", "")),
                r.get("sublayer", ""),
                r.get("weight", ""),
                r.get("key", ""),
            ]
            action_val = r.get("action", "")
            brush = allow_brush if action_val == "allow" else block_brush

            for j, text in enumerate(items):
                item = QTableWidgetItem(text)
                if j == 3:
                    item.setForeground(brush)
                if j == 7:
                    item.setData(Qt.ItemDataRole.UserRole, r.get("key", ""))
                self._table.setItem(i, j, item)

        self._set_status(f"规则数: {len(rules)}", temporary=False)

    def _export_rules(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出规则",
            "wfpctl-rules.json",
            "规则文件 (*.json);;所有文件 (*)",
        )
        if not path:
            return
        try:
            count = self._engine.export_rules(path)
            QMessageBox.information(self, "导出完成", f"已导出 {count} 条规则到:\n{path}")
            self._set_status(f"已导出 {count} 条规则")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def _import_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入规则",
            "",
            "规则文件 (*.json);;所有文件 (*)",
        )
        if not path:
            return
        try:
            result = self._engine.import_rules(path)
            lines = [
                f"新增: {result.get('added', 0)}",
                f"跳过(已存在): {result.get('skipped', 0)}",
                f"失败: {result.get('failed', 0)}",
            ]
            errors = result.get("errors")
            if errors:
                lines.append("错误详情:")
                lines.append(str(errors))
            QMessageBox.information(self, "导入完成", "\n".join(lines))
            self._refresh_rules()
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def _add_rule(self, default_action: str) -> None:
        dlg = AddRuleDialog(default_action=default_action, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.values()
        try:
            output = self._engine.add_rule(
                name=vals["name"],
                target=vals["target"],
                port=vals["port"],
                protocol=vals["protocol"],
                direction=vals["direction"],
                action=vals["action"],
                priority=vals["priority"],
                weight=vals["weight"],
            )
            QMessageBox.information(self, "操作成功", output)
            self._refresh_rules()
        except Exception as exc:
            QMessageBox.critical(self, "操作失败", str(exc))

    def _delete_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(rows)} 条规则吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        errors: list[str] = []
        for idx in rows:
            key_item = self._table.item(idx.row(), 7)
            if not key_item:
                continue
            key = key_item.data(Qt.ItemDataRole.UserRole) or key_item.text()
            ok, msg = self._engine.delete_rule(key)
            if not ok:
                errors.append(msg)

        if errors:
            QMessageBox.critical(self, "删除错误", "\n".join(errors))
        else:
            self._set_status("已删除所选规则")

        self._refresh_rules()

    def _show_sublayers(self) -> None:
        if not self._engine.available:
            QMessageBox.critical(self, "引擎未找到", "未找到 wfpctl 可执行文件")
            return
        dlg = SublayersDialog(self._engine, parent=self)
        dlg.exec()

    def _cleanup_all(self) -> None:
        confirm = QMessageBox.question(
            self,
            "确认清理",
            "确定要清理全部规则吗？\n这将移除 wfpctl 的子层、提供者和所有规则。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            ok, msg = self._engine.delete_sublayer("")
            if ok:
                QMessageBox.information(self, "清理完成", msg or "清理完成")
            else:
                QMessageBox.critical(self, "清理失败", msg)
        except Exception as exc:
            QMessageBox.critical(self, "清理失败", str(exc))
        self._refresh_rules()

    def _show_about(self) -> None:
        dlg = AboutDialog(self._engine, parent=self)
        dlg.exec()

    def _context_menu(self, pos: Any) -> None:
        menu = QMenu(self)
        style = self.style()

        act_del = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "删除所选", self)
        act_del.triggered.connect(self._delete_selected)
        act_del.setEnabled(bool(self._table.selectionModel().selectedRows()))
        menu.addAction(act_del)

        menu.addSeparator()

        act_copy = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), "复制 GUID", self)
        act_copy.triggered.connect(self._copy_guid)
        act_copy.setEnabled(bool(self._table.selectionModel().selectedRows()))
        menu.addAction(act_copy)

        menu.addSeparator()

        act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "刷新", self)
        act_refresh.triggered.connect(self._refresh_rules)
        menu.addAction(act_refresh)

        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _copy_guid(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        key_item = self._table.item(rows[0].row(), 7)
        if key_item:
            guid = key_item.data(Qt.ItemDataRole.UserRole) or key_item.text()
            QApplication.clipboard().setText(guid)
            self._set_status("已复制 GUID")
