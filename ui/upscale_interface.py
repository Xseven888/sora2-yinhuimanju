"""
高清放大界面 - 空白框架
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    PushButton, PrimaryPushButton, TitleLabel, BodyLabel, TableWidget
)


class UpscaleInterface(QWidget):
    """高清放大界面 - 空白框架"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("upscaleInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 控制按钮区域
        control_layout = QHBoxLayout()
        
        self.import_btn = PushButton('导入视频文件夹')
        control_layout.addWidget(self.import_btn)
        
        self.settings_btn = PushButton('设置')
        control_layout.addWidget(self.settings_btn)
        
        self.server_btn = PushButton('服务器配置')
        control_layout.addWidget(self.server_btn)
        
        self.process_btn = PrimaryPushButton('开始处理')
        self.process_btn.setEnabled(False)
        control_layout.addWidget(self.process_btn)
        
        self.stop_btn = PushButton('停止处理')
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 视频文件表格（空白）
        self.video_table = TableWidget()
        self.setup_video_table()
        layout.addWidget(self.video_table)
        
        # 状态标签
        self.status_label = BodyLabel("请先导入视频文件夹")
        self.status_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(self.status_label)

    def setup_video_table(self):
        """设置视频表格"""
        headers = ['文件名', '状态', '大小', '路径']
        self.video_table.setColumnCount(len(headers))
        self.video_table.setHorizontalHeaderLabels(headers)
        self.video_table.setRowCount(0)

        # 设置列宽
        self.video_table.setColumnWidth(0, 200)
        self.video_table.setColumnWidth(1, 100)
        self.video_table.setColumnWidth(2, 100)
        self.video_table.setColumnWidth(3, 300)

        # 设置表格属性
        self.video_table.setAlternatingRowColors(True)
        vertical_header = self.video_table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
        horizontal_header = self.video_table.horizontalHeader()
        if horizontal_header:
            horizontal_header.setStretchLastSection(True)
