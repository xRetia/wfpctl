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
from wfpctl_gui import i18n
from wfpctl_gui.i18n import tr


def layer_short(layer: str) -> str:
    return {
        "ALE_AUTH_CONNECT_V4": tr("layer_out4"),
        "ALE_AUTH_CONNECT_V6": tr("layer_out6"),
        "ALE_AUTH_RECV_ACCEPT_V4": tr("layer_in4"),
        "ALE_AUTH_RECV_ACCEPT_V6": tr("layer_in6"),
    }.get(layer, layer)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        i18n.set_language(i18n.load_language())
        self._rule_count = 0
        self.setWindowTitle(tr("app_title"))
        self.setWindowIcon(app_icon())
        self.resize(960, 600)

        self._engine = Engine()

        self._show_all = False
        self._sub_filter = ""

        self._build_menu()
        self._build_lang_menu()
        self._build_toolbar()
        self._build_table()
        self._build_statusbar()
        self._connect_signals()
        self._apply_language()
        self._refresh_sublayers()
        self._refresh_rules()

    def _apply_language(self) -> None:
        self.setWindowTitle(tr("app_title"))
        if hasattr(self, "_file_menu"):
            self._file_menu.setTitle(tr("file"))
            self._rule_menu.setTitle(tr("rules"))
            self._tool_menu.setTitle(tr("tools"))
            self._help_menu.setTitle(tr("help"))
            self._lang_menu.setTitle(tr("language"))
        for attr, key in (
            ("_act_refresh", "refresh_rules"),
            ("_act_export", "export_rules"),
            ("_act_import", "import_rules"),
            ("_act_quit", "quit"),
            ("_act_add_block", "add_block_rule"),
            ("_act_add_allow", "add_allow_rule"),
            ("_act_delete", "delete_selected"),
            ("_act_sublayers", "view_sublayers"),
            ("_act_cleanup", "clear_all_rules"),
            ("_act_about", "about"),
        ):
            if hasattr(self, attr):
                getattr(self, attr).setText(tr(key))
        if hasattr(self, "_tb"):
            self._tb.setWindowTitle(tr("toolbar"))
        if hasattr(self, "_table"):
            self._table.setHorizontalHeaderLabels(
                [tr(k) for k in ("col_id", "col_name", "col_dir", "col_action", "col_layer", "col_sublayer", "col_weight", "col_guid")]
            )
        if hasattr(self, "_filter_combo"):
            self._filter_combo.setItemText(0, tr("filter_only"))
            self._filter_combo.setItemText(1, tr("filter_all"))
            self._filter_combo.setToolTip(tr("filter_tip"))
        if hasattr(self, "_status_label"):
            self._status_label.setText(tr("status_rules").format(n=self._rule_count))
        if hasattr(self, "_lang_act_en"):
            self._lang_act_en.setText(tr("lang_english"))
            self._lang_act_zh.setText(tr("lang_chinese"))
            self._lang_act_en.setChecked(i18n.current_language() == i18n.EN)
            self._lang_act_zh.setChecked(i18n.current_language() == i18n.ZH)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        style = self.style()

        self._file_menu = mb.addMenu(tr("file"))
        self._act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), tr("refresh_rules"), self)
        self._act_refresh.setShortcut("F5")
        self._file_menu.addAction(self._act_refresh)
        self._file_menu.addSeparator()
        self._act_export = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), tr("export_rules"), self)
        self._act_export.setShortcut("Ctrl+E")
        self._file_menu.addAction(self._act_export)
        self._act_import = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), tr("import_rules"), self)
        self._act_import.setShortcut("Ctrl+I")
        self._file_menu.addAction(self._act_import)
        self._file_menu.addSeparator()
        self._act_quit = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), tr("quit"), self)
        self._act_quit.setShortcut("Alt+F4")
        self._act_quit.triggered.connect(self.close)
        self._file_menu.addAction(self._act_quit)

        self._rule_menu = mb.addMenu(tr("rules"))
        self._act_add_block = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical), tr("add_block_rule"), self)
        self._rule_menu.addAction(self._act_add_block)
        self._act_add_allow = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation), tr("add_allow_rule"), self)
        self._rule_menu.addAction(self._act_add_allow)
        self._rule_menu.addSeparator()
        self._act_delete = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), tr("delete_selected"), self)
        self._rule_menu.addAction(self._act_delete)

        self._tool_menu = mb.addMenu(tr("tools"))
        self._act_sublayers = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), tr("view_sublayers"), self)
        self._tool_menu.addAction(self._act_sublayers)
        self._tool_menu.addSeparator()
        self._act_cleanup = QAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton), tr("clear_all_rules"), self)
        self._tool_menu.addAction(self._act_cleanup)

        self._help_menu = mb.addMenu(tr("help"))
        self._act_about = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion), tr("about"), self)
        self._help_menu.addAction(self._act_about)

        self._lang_menu = mb.addMenu(tr("language"))

    def _build_lang_menu(self) -> None:
        self._lang_act_en = QAction(tr("lang_english"), self, checkable=True, checked=True)
        self._lang_act_zh = QAction(tr("lang_chinese"), self, checkable=True, checked=False)
        self._lang_act_en.triggered.connect(lambda: self._switch_language(i18n.EN))
        self._lang_act_zh.triggered.connect(lambda: self._switch_language(i18n.ZH))
        self._lang_menu.addAction(self._lang_act_en)
        self._lang_menu.addAction(self._lang_act_zh)

    def _switch_language(self, lang: str) -> None:
        i18n.set_language(lang)
        i18n.save_language(lang)
        self._apply_language()

    def _build_toolbar(self) -> None:
        self._tb = QToolBar(tr("toolbar"))
        self._tb.setMovable(False)
        self._tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(self._tb)

        style = self.style()

        self._tb.addAction(self._act_add_block)
        self._tb.addAction(self._act_add_allow)
        self._tb.addAction(self._act_delete)
        self._tb.addSeparator()
        self._tb.addAction(self._act_refresh)
        self._tb.addAction(self._act_export)
        self._tb.addAction(self._act_import)
        self._tb.addSeparator()
        self._tb.addAction(self._act_sublayers)
        self._tb.addAction(self._act_cleanup)

    def _build_table(self) -> None:
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(
            [tr(k) for k in ("col_id", "col_name", "col_dir", "col_action", "col_layer", "col_sublayer", "col_weight", "col_guid")]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.verticalHeader().setVisible(False)
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
        self._filter_combo.addItem(tr("filter_only"), "")
        self._filter_combo.addItem(tr("filter_all"), "__all__")
        self._filter_combo.setToolTip(tr("filter_tip"))
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(6, 4, 6, 0)
        vbox.addWidget(self._filter_combo)
        vbox.addWidget(self._table)
        self.setCentralWidget(container)

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self._status_label = QLabel(tr("status_rules").format(n=0))
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
        self._filter_combo.addItem(tr("filter_only"), "")
        self._filter_combo.addItem(tr("filter_all"), "__all__")
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
                tr("eng_not_found"),
                tr("eng_not_found_msg"),
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
                layer_short(r.get("layer", "")),
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

        self._rule_count = len(rules)
        self._set_status(tr("status_rules").format(n=self._rule_count), temporary=False)

    def _export_rules(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("export_title"),
            "wfpctl-rules.json",
            tr("export_filter"),
        )
        if not path:
            return
        try:
            count = self._engine.export_rules(path)
            QMessageBox.information(self, tr("export_done_title"), tr("export_done_msg").format(count=count, path=path))
            self._set_status(tr("export_status").format(count=count))
        except Exception as exc:
            QMessageBox.critical(self, tr("export_fail_title"), str(exc))

    def _import_rules(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("import_title"),
            "",
            tr("export_filter"),
        )
        if not path:
            return
        try:
            result = self._engine.import_rules(path)
            lines = [
                tr("import_added").format(n=result.get("added", 0)),
                tr("import_skipped").format(n=result.get("skipped", 0)),
                tr("import_failed").format(n=result.get("failed", 0)),
            ]
            errors = result.get("errors")
            if errors:
                lines.append(tr("error_details"))
                lines.append(str(errors))
            QMessageBox.information(self, tr("import_done_title"), "\n".join(lines))
            self._refresh_rules()
        except Exception as exc:
            QMessageBox.critical(self, tr("import_fail_title"), str(exc))

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
            QMessageBox.information(self, tr("op_success_title"), output)
            self._refresh_rules()
        except Exception as exc:
            QMessageBox.critical(self, tr("op_fail_title"), str(exc))

    def _delete_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        confirm = QMessageBox.question(
            self,
            tr("confirm_delete_title"),
            tr("confirm_delete_msg").format(n=len(rows)),
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
            QMessageBox.critical(self, tr("delete_error_title"), "\n".join(errors))
        else:
            self._set_status(tr("deleted_status"))

        self._refresh_rules()

    def _show_sublayers(self) -> None:
        if not self._engine.available:
            QMessageBox.critical(self, tr("eng_not_found"), tr("eng_not_found_msg"))
            return
        dlg = SublayersDialog(self._engine, parent=self)
        dlg.exec()

    def _cleanup_all(self) -> None:
        confirm = QMessageBox.question(
            self,
            tr("confirm_cleanup_title"),
            tr("confirm_cleanup_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            ok, msg = self._engine.delete_sublayer("")
            if ok:
                QMessageBox.information(self, tr("cleanup_done_title"), msg or tr("cleanup_done_title"))
            else:
                QMessageBox.critical(self, tr("cleanup_fail_title"), msg)
        except Exception as exc:
            QMessageBox.critical(self, tr("cleanup_fail_title"), str(exc))
        self._refresh_rules()

    def _show_about(self) -> None:
        dlg = AboutDialog(self._engine, parent=self)
        dlg.exec()

    def _context_menu(self, pos: Any) -> None:
        menu = QMenu(self)
        style = self.style()

        act_del = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), tr("delete_selected"), self)
        act_del.triggered.connect(self._delete_selected)
        act_del.setEnabled(bool(self._table.selectionModel().selectedRows()))
        menu.addAction(act_del)

        menu.addSeparator()

        act_copy = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), tr("copy_guid"), self)
        act_copy.triggered.connect(self._copy_guid)
        act_copy.setEnabled(bool(self._table.selectionModel().selectedRows()))
        menu.addAction(act_copy)

        menu.addSeparator()

        act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), tr("refresh_ctx"), self)
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
            self._set_status(tr("copied_guid"))
