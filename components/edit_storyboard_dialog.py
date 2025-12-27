"""
编辑分镜对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout
from qfluentwidgets import (
    TitleLabel, BodyLabel, PushButton, PrimaryPushButton, 
    TextEdit, LineEdit, CardWidget
)


class EditStoryboardDetailsDialog(QDialog):
    """编辑分镜详情对话框"""
    
    def __init__(self, storyboard_data, parent=None):
        super().__init__(parent)
        self.storyboard_data = storyboard_data
        self.setWindowTitle("编辑分镜详情")
        self.setModal(True)
        self.resize(600, 500)
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("编辑分镜详情")
        layout.addWidget(title)
        
        # 表单卡片
        form_card = CardWidget()
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        self.title_input = LineEdit()
        self.title_input.setPlaceholderText("输入分镜标题")
        form_layout.addRow("标题:", self.title_input)
        
        # 时长
        self.duration_input = LineEdit()
        self.duration_input.setPlaceholderText("例如: 10s 或 15s")
        form_layout.addRow("时长:", self.duration_input)
        
        # 文案/对白
        self.dialogue_input = TextEdit()
        self.dialogue_input.setPlaceholderText("输入文案/对白")
        self.dialogue_input.setMaximumHeight(100)
        form_layout.addRow("文案/对白:", self.dialogue_input)
        
        # 音效
        self.sound_effect_input = TextEdit()
        self.sound_effect_input.setPlaceholderText("输入音效描述")
        self.sound_effect_input.setMaximumHeight(80)
        form_layout.addRow("音效:", self.sound_effect_input)
        
        # 画面内容
        self.screen_content_input = TextEdit()
        self.screen_content_input.setPlaceholderText("输入画面内容描述")
        self.screen_content_input.setMaximumHeight(120)
        form_layout.addRow("画面内容:", self.screen_content_input)
        
        # 镜头移动
        self.camera_movement_input = TextEdit()
        self.camera_movement_input.setPlaceholderText("输入镜头移动描述")
        self.camera_movement_input.setMaximumHeight(100)
        form_layout.addRow("镜头移动:", self.camera_movement_input)
        
        layout.addWidget(form_card)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
    def load_data(self):
        """加载数据"""
        self.title_input.setText(self.storyboard_data.get('title', ''))
        self.duration_input.setText(self.storyboard_data.get('duration', ''))
        self.dialogue_input.setPlainText(self.storyboard_data.get('dialogue', ''))
        self.sound_effect_input.setPlainText(self.storyboard_data.get('sound_effect', ''))
        self.screen_content_input.setPlainText(self.storyboard_data.get('screen_content', ''))
        self.camera_movement_input.setPlainText(self.storyboard_data.get('camera_movement', ''))
        
    def get_data(self):
        """获取编辑后的数据"""
        return {
            'title': self.title_input.text().strip(),
            'duration': self.duration_input.text().strip(),
            'dialogue': self.dialogue_input.toPlainText().strip(),
            'sound_effect': self.sound_effect_input.toPlainText().strip(),
            'screen_content': self.screen_content_input.toPlainText().strip(),
            'camera_movement': self.camera_movement_input.toPlainText().strip(),
        }


class EditStoryboardPromptDialog(QDialog):
    """编辑分镜提示词对话框"""
    
    def __init__(self, prompt, parent=None):
        super().__init__(parent)
        self.prompt = prompt
        self.setWindowTitle("编辑分镜提示词")
        self.setModal(True)
        self.resize(600, 400)
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("编辑分镜提示词")
        layout.addWidget(title)
        
        # 提示词输入
        prompt_card = CardWidget()
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(20, 20, 20, 20)
        
        prompt_label = BodyLabel("提示词:")
        prompt_layout.addWidget(prompt_label)
        
        self.prompt_input = TextEdit()
        self.prompt_input.setPlaceholderText("输入分镜提示词")
        prompt_layout.addWidget(self.prompt_input)
        
        layout.addWidget(prompt_card)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
    def load_data(self):
        """加载数据"""
        self.prompt_input.setPlainText(self.prompt or '')
        
    def get_prompt(self):
        """获取编辑后的提示词"""
        return self.prompt_input.toPlainText().strip()

