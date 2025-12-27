"""
高清放大服务器配置对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from qfluentwidgets import (
    TitleLabel, TableWidget, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition, CheckBox
)

from database_manager import db_manager


class UpscaleServersDialog(QDialog):
    """管理高清放大服务器的对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高清放大服务器配置")
        self.setModal(True)
        self.resize(700, 420)
        self._server_rows = []  # 缓存行对应的服务器ID
        self.init_ui()
        self.load_servers()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = TitleLabel("管理可并发调用的ComfyUI服务器")
        layout.addWidget(title)

        # 表格
        self.table = TableWidget()
        # 4列：序号、名称、地址、启用
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["序号", "名称", "地址", "启用"])
        header = self.table.horizontalHeader()
        if header:
            # 使用固定列宽，由我们按比例设置
            from PyQt5.QtWidgets import QHeaderView
            header.setStretchLastSection(False)
            header.setSectionResizeMode(QHeaderView.Fixed)

        # 允许编辑名称和地址
        from PyQt5.QtWidgets import QAbstractItemView
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)

        layout.addWidget(self.table)
        # 初始化列宽比例：1:3:13:3
        self.update_column_widths()

        # 操作按钮
        btn_bar = QHBoxLayout()
        self.add_btn = PushButton("添加服务器")
        self.add_btn.clicked.connect(self.add_row)
        btn_bar.addWidget(self.add_btn)

        self.remove_btn = PushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        btn_bar.addWidget(self.remove_btn)

        btn_bar.addStretch()

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(self.cancel_btn)

        self.save_btn = PrimaryPushButton("保存并关闭")
        self.save_btn.clicked.connect(self.save_and_close)
        btn_bar.addWidget(self.save_btn)

        layout.addLayout(btn_bar)

    def load_servers(self):
        servers = db_manager.get_upscale_servers()
        self.table.setRowCount(0)
        self._server_rows = []

        for s in servers:
            self._append_server_row(s.get('id'), s.get('name'), s.get('url'), bool(s.get('enabled')))
        # 重新编号与列宽
        self.renumber_rows()
        self.update_column_widths()

    def _append_server_row(self, server_id, name, url, enabled):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._server_rows.append(server_id)

        # 序号（只读居中）
        index_item = QTableWidgetItem(str(row + 1))
        index_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        # 设置为不可编辑
        index_item.setFlags(index_item.flags() & ~Qt.ItemIsEditable)  # type: ignore
        self.table.setItem(row, 0, index_item)

        name_item = QTableWidgetItem(name or "")
        self.table.setItem(row, 1, name_item)

        url_item = QTableWidgetItem(url or "")
        self.table.setItem(row, 2, url_item)

        # 启用复选框
        checkbox = CheckBox()
        checkbox.setChecked(bool(enabled))
        from PyQt5.QtWidgets import QWidget, QHBoxLayout
        cell_widget = QWidget()
        cell_layout = QHBoxLayout(cell_widget)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.addWidget(checkbox)
        cell_layout.addStretch()
        self.table.setCellWidget(row, 3, cell_widget)
        # 保存checkbox引用以便读取
        cell_widget._checkbox = checkbox  # type: ignore

    def add_row(self):
        # 追加空白行供用户填写
        self._append_server_row(None, "服务器", "http://localhost:8188", True)
        self.renumber_rows()
        self.update_column_widths()

    def remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            InfoBar.warning(
                title='提示',
                content='请先选择要删除的行',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        server_id = self._server_rows[row]
        # 先从表中删除
        self.table.removeRow(row)
        self._server_rows.pop(row)

        # 删除后重新编号与列宽
        self.renumber_rows()
        self.update_column_widths()

        if server_id:
            # 如果是已有记录，删除数据库
            db_manager.delete_upscale_server(server_id)

    def save_and_close(self):
        rows = self.table.rowCount()
        for row in range(rows):
            # 名称、地址、启用对应列索引调整为 1、2、3
            name_item = self.table.item(row, 1)
            url_item = self.table.item(row, 2)
            cell_widget = self.table.cellWidget(row, 3)
            enabled = True
            if cell_widget and hasattr(cell_widget, '_checkbox'):
                enabled = bool(cell_widget._checkbox.isChecked())  # type: ignore

            name = name_item.text().strip() if name_item else ''
            url = url_item.text().strip() if url_item else ''

            if not url or not (url.startswith('http://') or url.startswith('https://')):
                InfoBar.error(
                    title='错误',
                    content=f'第{row+1}行服务器地址无效，请以http(s)开头',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return

            server_id = self._server_rows[row]
            if server_id:
                db_manager.update_upscale_server(server_id, name=name or url, url=url, enabled=enabled)
            else:
                # 新增，若未填名称则用地址作为名称
                db_manager.add_upscale_server(name or url, url, enabled)

        InfoBar.success(
            title='成功',
            content='服务器配置已保存',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

        self.accept()

    def renumber_rows(self):
        """按当前行顺序重新设置序号列"""
        rows = self.table.rowCount()
        for r in range(rows):
            item = self.table.item(r, 0)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(r, 0, item)
            item.setText(str(r + 1))
            item.setTextAlignment(Qt.AlignCenter)  # type: ignore
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # type: ignore

    def update_column_widths(self):
        """按比例 1:3:13:3 设置列宽"""
        try:
            total = 1 + 3 + 13 + 3
            content_width = max(self.table.viewport().width(), 400)
            parts = [1, 3, 13, 3]
            widths = [int(content_width * p / total) for p in parts]
            for i, w in enumerate(widths):
                self.table.setColumnWidth(i, max(w, 40))
        except Exception:
            pass

    def resizeEvent(self, event):  # type: ignore
        super().resizeEvent(event)
        # 当对话框或表格尺寸变化时，更新列宽
        self.update_column_widths()
