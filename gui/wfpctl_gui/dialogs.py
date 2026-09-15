from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from wfpctl_gui.i18n import tr


class AddRuleDialog(QDialog):
    def __init__(self, default_action: str = "block", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("add_rule_title"))
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.name_edit = QLineEdit("wfpctl-rule")
        form.addRow(tr("rule_name_label"), self.name_edit)

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText(tr("target_ph"))
        form.addRow(tr("target_label"), self.target_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText(tr("port_ph"))
        form.addRow(tr("port_label"), self.port_edit)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems([tr("proto_any"), "TCP", "UDP"])
        form.addRow(tr("protocol_label"), self.protocol_combo)

        self.direction_combo = QComboBox()
        self.direction_combo.addItems([tr("dir_out"), tr("dir_in")])
        form.addRow(tr("direction_label"), self.direction_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItems([tr("act_block"), tr("act_allow")])
        self.action_combo.setCurrentIndex(0 if default_action == "block" else 1)
        form.addRow(tr("action_label"), self.action_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems([tr("prio_highest"), tr("prio_lowest"), tr("prio_custom")])
        form.addRow(tr("priority_label"), self.priority_combo)

        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(0, 2147483647)
        self.weight_spin.setValue(0)
        self._weight_row = form.rowCount()
        form.addRow(tr("weight_label"), self.weight_spin)
        self._update_weight_visibility()

        self.priority_combo.currentIndexChanged.connect(self._update_weight_visibility)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = bbox.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        cancel_btn = bbox.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self.reject)
        form.addRow(bbox)

    def _update_weight_visibility(self) -> None:
        custom = self.priority_combo.currentIndex() == 2
        self.weight_spin.setVisible(custom)
        self.weight_spin.setEnabled(custom)

    def _on_accept(self) -> None:
        if not self.target_edit.text().strip():
            QMessageBox.warning(self, tr("validate_title"), tr("target_required"))
            return
        self.accept()

    def values(self) -> dict[str, str | int]:
        proto_map = ["", "tcp", "udp"]
        prio_map = ["highest", "lowest", "custom"]
        act_map = ["block", "allow"]
        dir_map = ["out", "in"]
        return {
            "name": self.name_edit.text().strip() or "wfpctl-rule",
            "target": self.target_edit.text().strip(),
            "port": self.port_edit.text().strip(),
            "protocol": proto_map[self.protocol_combo.currentIndex()],
            "direction": dir_map[self.direction_combo.currentIndex()],
            "action": act_map[self.action_combo.currentIndex()],
            "priority": prio_map[self.priority_combo.currentIndex()],
            "weight": self.weight_spin.value(),
        }


class SublayersDialog(QDialog):
    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self.setWindowTitle(tr("sublayer_info"))
        self.setMinimumSize(650, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("col_weight"), tr("col_name"), tr("col_guid")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: #0078D7; color: white; }"
        )
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        del_btn = QPushButton(tr("del_sublayer_btn"))
        del_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        del_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(del_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(tr("close_btn"))
        close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self._load()

    def _load(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sublayers = self._engine.list_sublayers()
        finally:
            QApplication.restoreOverrideCursor()

        self.table.setRowCount(0)
        if not sublayers:
            return

        self.table.setRowCount(len(sublayers))
        for i, s in enumerate(sublayers):
            self.table.setItem(i, 0, QTableWidgetItem(str(s.get("weight", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(str(s.get("name", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(s.get("key", ""))))

    def _delete_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        confirm = QMessageBox.question(
            self,
            tr("confirm_delete_sub_title"),
            tr("confirm_delete_sub_msg").format(n=len(rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        for idx in rows:
            guid = self.table.item(idx.row(), 2)
            if guid:
                ok, msg = self._engine.delete_sublayer(guid.text())
                if not ok:
                    QMessageBox.critical(self, tr("delete_fail_title"), msg)
        self._load()


class AboutDialog(QDialog):
    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about_title"))
        self.setFixedSize(420, 200)

        layout = QVBoxLayout(self)

        title = QLabel(tr("about_main_title"))
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = engine.version()
        ver_label = QLabel(tr("engine_ver").format(ver=version))
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)

        layout.addSpacing(10)

        copyright_label = QLabel("Copyright (c) 2026 xRetia Labs")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        link = QLabel('<a href="https://github.com/xRetia/wfpctl">https://github.com/xRetia/wfpctl</a>')
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        layout.addSpacing(15)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        ok_btn = bbox.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        bbox.accepted.connect(self.accept)
        layout.addWidget(bbox)
