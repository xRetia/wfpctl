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


class AddRuleDialog(QDialog):
    def __init__(self, default_action: str = "block", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加规则")
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.name_edit = QLineEdit("wfpctl-rule")
        form.addRow("规则名称:", self.name_edit)

        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("例如 192.168.1.0/24")
        form.addRow("目标 IP/CIDR:", self.target_edit)

        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("例如 80 或 80-443")
        form.addRow("端口/区间:", self.port_edit)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["(任一)", "TCP", "UDP"])
        form.addRow("协议:", self.protocol_combo)

        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["出站", "入站"])
        form.addRow("方向:", self.direction_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItems(["阻止", "允许"])
        self.action_combo.setCurrentIndex(0 if default_action == "block" else 1)
        form.addRow("动作:", self.action_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["最高", "最低", "自定义"])
        form.addRow("优先级:", self.priority_combo)

        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(0, 2147483647)
        self.weight_spin.setValue(0)
        self._weight_row = form.rowCount()
        form.addRow("自定义权重:", self.weight_spin)
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
            QMessageBox.warning(self, "验证错误", "目标 IP/CIDR 不能为空")
            return
        self.accept()

    def values(self) -> dict[str, str | int]:
        proto_map = {"(任一)": "", "TCP": "tcp", "UDP": "udp"}
        prio_map = {"最高": "highest", "最低": "lowest", "自定义": "custom"}
        act_map = {"阻止": "block", "允许": "allow"}
        dir_map = {"出站": "out", "入站": "in"}
        return {
            "name": self.name_edit.text().strip() or "wfpctl-rule",
            "target": self.target_edit.text().strip(),
            "port": self.port_edit.text().strip(),
            "protocol": proto_map.get(self.protocol_combo.currentText(), ""),
            "direction": dir_map.get(self.direction_combo.currentText(), "out"),
            "action": act_map.get(self.action_combo.currentText(), "block"),
            "priority": prio_map.get(self.priority_combo.currentText(), "highest"),
            "weight": self.weight_spin.value(),
        }


class SublayersDialog(QDialog):
    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self.setWindowTitle("子层信息")
        self.setMinimumSize(650, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["权重", "名称", "GUID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: #0078D7; color: white; }"
        )
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        del_btn = QPushButton(" 删除选中子层")
        del_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        del_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(del_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(" 关闭")
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
            "确认删除",
            f"确定要删除选中的 {len(rows)} 个子层吗？\n这将移除子层中的所有规则。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        for idx in rows:
            guid = self.table.item(idx.row(), 2)
            if guid:
                ok, msg = self._engine.delete_sublayer(guid.text())
                if not ok:
                    QMessageBox.critical(self, "删除失败", msg)
        self._load()


class AboutDialog(QDialog):
    def __init__(self, engine: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("关于 wfpctl")
        self.setFixedSize(420, 200)

        layout = QVBoxLayout(self)

        title = QLabel("wfpctl - Windows 防火墙控制台")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = engine.version()
        ver_label = QLabel(f"引擎版本: {version}")
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
