"""
设置对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout
from qfluentwidgets import (
    TitleLabel, LineEdit, PushButton, PrimaryPushButton, CheckBox
)

from database_manager import db_manager

class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(420, 360)
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = TitleLabel("应用设置")
        layout.addWidget(title)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)  # type: ignore
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore
        
        # API Key
        self.api_key_input = LineEdit()
        self.api_key_input.setPlaceholderText("请输入您的 Sora API Key")
        form_layout.addRow("API Key:", self.api_key_input)
        
        # 已移除单一ComfyUI服务器配置，改用批量高清界面“服务器配置”管理
        
        # 视频保存路径
        self.video_path_input = LineEdit()
        self.video_path_input.setPlaceholderText("选择视频保存路径，留空则使用默认路径")
        form_layout.addRow("视频保存路径:", self.video_path_input)

        # AI 标题开关
        self.ai_title_checkbox = CheckBox()
        self.ai_title_checkbox.setText('启用AI标题生成')
        form_layout.addRow("AI 标题:", self.ai_title_checkbox)

        # AI 标题提示词
        self.ai_title_prompt_input = LineEdit()
        self.ai_title_prompt_input.setPlaceholderText('请输入用于生成标题的提示词')
        form_layout.addRow("AI 标题提示词:", self.ai_title_prompt_input)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.clicked.connect(self.save_and_close)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """加载设置"""
        api_key = db_manager.load_config('api_key', '')
        self.api_key_input.setText(api_key)

        # ComfyUI服务器地址不再在此配置

        # 加载视频保存路径
        video_path = db_manager.load_config('video_save_path', '')
        self.video_path_input.setText(video_path)

        # 加载AI标题设置
        ai_enabled = db_manager.load_config('ai_title_enabled', False)
        try:
            self.ai_title_checkbox.setChecked(bool(ai_enabled))
        except Exception:
            pass
        ai_prompt = db_manager.load_config('ai_title_prompt', '只返回一个中文视频标题，不要返回任何解释或额外内容；不使用引号、编号、前后缀；不换行；不超过30字，风格有趣吸引人')
        self.ai_title_prompt_input.setText(ai_prompt)
        
    def save_and_close(self):
        """保存设置并关闭"""
        api_key = self.api_key_input.text().strip()
        db_manager.save_config('api_key', api_key, 'string', 'Sora API Key')
        
        # 不再保存ComfyUI服务器设置
        
        # 保存视频保存路径
        video_path = self.video_path_input.text().strip()
        db_manager.save_config('video_save_path', video_path, 'string', '视频保存路径')

        # 保存AI标题设置
        enabled = bool(self.ai_title_checkbox.isChecked())
        db_manager.save_config('ai_title_enabled', enabled, 'boolean', 'AI标题开关')
        prompt = self.ai_title_prompt_input.text().strip() or '只返回一个中文视频标题，不要返回任何解释或额外内容；不使用引号、编号、前后缀；不换行；不超过30字，风格有趣吸引人'
        db_manager.save_config('ai_title_prompt', prompt, 'string', 'AI标题提示词')

        self.accept()
        
    # 已移除实时保存ComfyUI服务器方法
        
    def get_settings(self):
        """获取设置"""
        return {
            'api_key': self.api_key_input.text().strip(),
            'video_save_path': self.video_path_input.text().strip()
        }
