"""
带货界面 - 空白框架
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView
from qfluentwidgets import (
    TitleLabel, BodyLabel, PushButton, PrimaryPushButton, TableWidget
)


class GoodsInterface(QWidget):
    """带货列表界面 - 空白框架"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("goodsInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 顶部标题与操作区
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        title = TitleLabel('商品列表')
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.prompt_btn = PushButton('提示词设置')
        self.prompt_btn.setFixedWidth(100)
        header_layout.addWidget(self.prompt_btn)

        self.add_btn = PrimaryPushButton('添加')
        self.add_btn.setFixedWidth(100)
        header_layout.addWidget(self.add_btn)
        layout.addLayout(header_layout)

        # 列表表格（空白）
        self.table = TableWidget()
        self.setup_table()
        layout.addWidget(self.table)

        # 分页控件（空白）
        self.create_pagination_controls(layout)

    def setup_table(self):
        headers = ['商品标题', '主图', '白底图', '状态']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(0)
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.setSelectionBehavior(self.table.SelectRows)  # type: ignore
        self.table.setSelectionMode(self.table.MultiSelection)  # type: ignore
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        v_header = self.table.verticalHeader()
        if v_header:
            v_header.setVisible(False)
            v_header.setDefaultSectionSize(160)

        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 170)

    def create_pagination_controls(self, layout):
        pagination_layout = QHBoxLayout()
        pagination_layout.setContentsMargins(0, 0, 0, 0)
        pagination_layout.setSpacing(8)

        self.prev_btn = PushButton("上一页")
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)

        self.page_label = BodyLabel("第 1 页 / 共 1 页")
        self.page_label.setStyleSheet("color: #666; font-size: 13px;")
        pagination_layout.addWidget(self.page_label)

        self.next_btn = PushButton("下一页")
        pagination_layout.addWidget(self.next_btn)

        pagination_layout.addStretch()

        self.total_label = BodyLabel("共 0 条记录")
        self.total_label.setStyleSheet("color: #666; font-size: 13px;")
        pagination_layout.addWidget(self.total_label)

        layout.addLayout(pagination_layout)
