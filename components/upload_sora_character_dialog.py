"""
上传Sora2角色对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    TitleLabel, BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
    InfoBar, InfoBarPosition
)
from pathlib import Path
from loguru import logger
from threads.image_upload_thread import ImageUploadThread
from utils.oss_uploader import OSSUploader
from database_manager import db_manager


class UploadSoraCharacterDialog(QDialog):
    """上传Sora2角色对话框"""
    
    def __init__(self, character_id, character_image_path=None, parent=None):
        super().__init__(parent)
        self.character_id = character_id
        self.character_image_path = character_image_path
        self.video_url = None
        self.setWindowTitle("上传Sora2角色")
        self.setModal(True)
        self.resize(500, 400)
        self.upload_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("上传Sora2角色")
        layout.addWidget(title)
        
        # 说明
        desc = BodyLabel("需要先上传角色图片生成视频，然后从视频中提取角色。\n视频中不能出现真人，否则会失败。")
        desc.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(desc)
        
        # 视频URL输入（如果已有）
        video_url_label = BodyLabel("视频URL（可选，如果已有视频URL可直接使用）:")
        layout.addWidget(video_url_label)
        
        video_url_layout = QHBoxLayout()
        self.video_url_input = LineEdit()
        self.video_url_input.setPlaceholderText("例如: https://filesystem.site/cdn/20251030/xxx.mp4")
        video_url_layout.addWidget(self.video_url_input)
        
        self.upload_image_btn = PushButton("上传图片生成视频")
        self.upload_image_btn.clicked.connect(self.upload_image_to_video)
        video_url_layout.addWidget(self.upload_image_btn)
        
        layout.addLayout(video_url_layout)
        
        # 时间戳范围输入
        timestamps_label = BodyLabel("角色出现时间范围（秒，格式：开始,结束，例如：1,3）:")
        layout.addWidget(timestamps_label)
        
        timestamps_desc = BodyLabel("注意：结束时间-开始时间的范围必须在1-3秒之间")
        timestamps_desc.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(timestamps_desc)
        
        self.timestamps_input = LineEdit()
        self.timestamps_input.setPlaceholderText("例如: 1,3")
        layout.addWidget(self.timestamps_input)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = PrimaryPushButton("确定")
        confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def upload_image_to_video(self):
        """上传图片生成视频（这里需要先上传图片，然后生成视频）"""
        # 检查是否有角色图片
        if not self.character_image_path or not Path(self.character_image_path).exists():
            InfoBar.warning(
                title='提示',
                content='请先生成角色图片',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 这里应该调用视频生成API，但为了简化，先提示用户手动上传视频
        # 或者可以集成视频生成功能
        InfoBar.info(
            title='提示',
            content='请先使用视频生成功能生成包含角色的视频，然后在此输入视频URL',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def on_confirm(self):
        """确认上传"""
        video_url = self.video_url_input.text().strip()
        timestamps = self.timestamps_input.text().strip()
        
        if not video_url:
            InfoBar.warning(
                title='提示',
                content='请输入视频URL',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        if not timestamps:
            InfoBar.warning(
                title='提示',
                content='请输入时间戳范围',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 验证时间戳格式
        try:
            parts = timestamps.split(',')
            if len(parts) != 2:
                raise ValueError("时间戳格式错误")
            
            start = float(parts[0].strip())
            end = float(parts[1].strip())
            
            if start >= end:
                raise ValueError("开始时间必须小于结束时间")
            
            duration = end - start
            if duration < 1 or duration > 3:
                raise ValueError("时间范围必须在1-3秒之间")
            
        except ValueError as e:
            InfoBar.warning(
                title='格式错误',
                content=f'时间戳格式错误: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        self.video_url = video_url
        self.timestamps = timestamps
        self.accept()
    
    def closeEvent(self, event):
        """对话框关闭事件"""
        # 停止上传线程
        if self.upload_thread and self.upload_thread.isRunning():
            self.upload_thread.terminate()
            self.upload_thread.wait()
        super().closeEvent(event)

