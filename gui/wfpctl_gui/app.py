from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPalette, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
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
    QWidget,
)

from wfpctl_gui.dialogs import AboutDialog, AddRuleDialog, SublayersDialog
from wfpctl_gui.engine import Engine


def _make_shield_icon() -> QIcon:
    size = 64
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QColor(0, 120, 215))
    p.setPen(QPen(QColor(0, 80, 160), 2))

    pts = [
        (32, 4),
        (56, 14),
        (56, 32),
        (56, 44),
        (44, 56),
        (32, 60),
        (20, 56),
        (8, 44),
        (8, 32),
        (8, 14),
    ]
    polygon = QPolygon([QPoint(x, y) for x, y in pts])
    p.drawPolygon(polygon)

    p.setPen(QColor(255, 255, 255))
    p.setBrush(QColor(255, 255, 255))
    font = p.font()
    font.setPixelSize(28)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    p.end()

    return QIcon(pix)


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
        self.setWindowIcon(_make_shield_icon())
        self.resize(960, 600)

        self._engine = Engine()

        self._build_menu()
        self._build_toolbar()
        self._build_table()
        self._build_statusbar()
        self._connect_signals()
        self._refresh_rules()

    def _build_menu(self) -> None:
        mb = self.menuBar()

        style = self.style()

        file_menu = mb.addMenu("文件")
        self._act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "刷新规则", self)
        self._act_refresh.setShortcut("F5")
        file_menu.addAction(self._act_refresh)
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
        tb.addAction(self._act_sublayers)
        tb.addAction(self._act_cleanup)

    def _build_table(self) -> None:
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["ID", "名称", "方向", "动作", "层", "权重", "GUID"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setCentralWidget(self._table)

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self._status_label = QLabel("规则数: 0")
        sb.addWidget(self._status_label)
        self._status_msg = QLabel("")
        sb.addPermanentWidget(self._status_msg)

    def _connect_signals(self) -> None:
        self._act_refresh.triggered.connect(self._refresh_rules)
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

    def _refresh_rules(self) -> None:
        if not self._engine.available:
            QMessageBox.critical(
                self,
                "引擎未找到",
                "未找到 wfpctl 可执行文件。\n请确保 wfpctl.exe 在程序目录或 PATH 中。",
            )
            return

        rules = self._engine.list_rules()
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
                r.get("weight", ""),
                r.get("key", ""),
            ]
            action_val = r.get("action", "")
            brush = allow_brush if action_val == "allow" else block_brush

            for j, text in enumerate(items):
                item = QTableWidgetItem(text)
                if j == 3:
                    item.setForeground(brush)
                if j == 6:
                    item.setData(Qt.ItemDataRole.UserRole, r.get("key", ""))
                self._table.setItem(i, j, item)

        self._set_status(f"规则数: {len(rules)}", temporary=False)

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
            key_item = self._table.item(idx.row(), 6)
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
        key_item = self._table.item(rows[0].row(), 6)
        if key_item:
            guid = key_item.data(Qt.ItemDataRole.UserRole) or key_item.text()
            QApplication.clipboard().setText(guid)
            self._set_status("已复制 GUID")
