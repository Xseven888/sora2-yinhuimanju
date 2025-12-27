"""
高清放大设置对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QDialogButtonBox
from qfluentwidgets import (
    TitleLabel, RadioButton, PushButton, PrimaryPushButton
)

from database_manager import db_manager

class UpscaleSettingsDialog(QDialog):
    """高清放大设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高清放大设置")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = TitleLabel("高清放大设置")
        layout.addWidget(title)
        
        # 模式选择组
        mode_group = QGroupBox("模式选择")
        mode_layout = QVBoxLayout(mode_group)
        
        # 模式选项
        self.tiny_radio = RadioButton("快速 (tiny)")
        self.tiny_long_radio = RadioButton("快速-长视频 (tiny-long)")
        self.full_radio = RadioButton("超清 (full)")
        
        # 设置中文标签
        self.tiny_radio.setText("快速 (tiny)")
        self.tiny_long_radio.setText("快速-长视频 (tiny-long)")
        self.full_radio.setText("超清 (full)")
        
        # 默认选中tiny
        self.tiny_radio.setChecked(True)
        
        mode_layout.addWidget(self.tiny_radio)
        mode_layout.addWidget(self.tiny_long_radio)
        mode_layout.addWidget(self.full_radio)
        
        layout.addWidget(mode_group)
        
        # 放大系数选择组
        scale_group = QGroupBox("放大系数")
        scale_layout = QVBoxLayout(scale_group)
        
        # 放大系数选项
        self.scale_2_radio = RadioButton("2倍")
        self.scale_3_radio = RadioButton("3倍")
        self.scale_4_radio = RadioButton("4倍")
        
        # 默认选中2倍
        self.scale_2_radio.setChecked(True)
        
        scale_layout.addWidget(self.scale_2_radio)
        scale_layout.addWidget(self.scale_3_radio)
        scale_layout.addWidget(self.scale_4_radio)
        
        layout.addWidget(scale_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = PrimaryPushButton("确定")
        self.save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """加载设置"""
        # 从数据库加载上次保存的设置
        mode = db_manager.load_config('upscale_mode', 'tiny')  # 默认tiny
        scale = db_manager.load_config('upscale_scale', 2)
        
        # 设置模式选择
        if mode == 'tiny':
            self.tiny_radio.setChecked(True)
        elif mode == 'tiny-long':
            self.tiny_long_radio.setChecked(True)
        elif mode == 'full':
            self.full_radio.setChecked(True)
            
        # 设置放大系数
        if scale == 2:
            self.scale_2_radio.setChecked(True)
        elif scale == 3:
            self.scale_3_radio.setChecked(True)
        elif scale == 4:
            self.scale_4_radio.setChecked(True)

    def save_and_close(self):
        """保存设置并关闭"""
        # 获取选中的模式
        if self.tiny_radio.isChecked():
            mode = 'tiny'
        elif self.tiny_long_radio.isChecked():
            mode = 'tiny-long'
        elif self.full_radio.isChecked():
            mode = 'full'
        else:
            mode = 'tiny-long'  # 默认值
            
        # 获取选中的放大系数
        if self.scale_2_radio.isChecked():
            scale = 2
        elif self.scale_3_radio.isChecked():
            scale = 3
        elif self.scale_4_radio.isChecked():
            scale = 4
        else:
            scale = 2  # 默认值
            
        # 保存到数据库
        db_manager.save_config('upscale_mode', mode, 'string', '高清放大模式')
        db_manager.save_config('upscale_scale', scale, 'integer', '高清放大系数')
        
        self.accept()
        
    def get_settings(self):
        """获取设置"""
        # 获取选中的模式
        if self.tiny_radio.isChecked():
            mode = 'tiny'
        elif self.tiny_long_radio.isChecked():
            mode = 'tiny-long'
        elif self.full_radio.isChecked():
            mode = 'full'
        else:
            mode = 'tiny-long'
            
        # 获取选中的放大系数
        if self.scale_2_radio.isChecked():
            scale = 2
        elif self.scale_3_radio.isChecked():
            scale = 3
        elif self.scale_4_radio.isChecked():
            scale = 4
        else:
            scale = 2
            
        return {
            'mode': mode,
            'scale': scale
        }