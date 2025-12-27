"""
批量克隆界面 - 空白框架
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    PushButton, PrimaryPushButton, TitleLabel, BodyLabel, TableWidget
)


class BatchCloneInterface(QWidget):
    """批量克隆界面 - 空白框架"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("batchCloneInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题与说明
        header_layout = QHBoxLayout()
        title = TitleLabel('批量克隆')
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        description = BodyLabel('批量克隆功能')
        description.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(description)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.import_btn = PushButton('导入视频文件夹')
        control_layout.addWidget(self.import_btn)

        self.start_btn = PrimaryPushButton('开始执行')
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = PushButton('停止')
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        self.export_btn = PushButton('导出表格')
        control_layout.addWidget(self.export_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 列表表格（空白）
        self.table = TableWidget()
        self.setup_table()
        layout.addWidget(self.table)

        # 状态标签
        self.status_label = BodyLabel('请导入视频文件夹')
        self.status_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.status_label)

    def setup_table(self):
        headers = ['文件名', '大小', '提示词', '状态', '路径']
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(0)
        self.table.horizontalHeader().setStretchLastSection(True)
