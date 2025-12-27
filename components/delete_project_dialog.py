"""
删除项目确认对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    TitleLabel, LineEdit, PushButton, PrimaryPushButton, BodyLabel, InfoBar, InfoBarPosition
)


class DeleteProjectDialog(QDialog):
    """删除项目确认对话框"""
    
    CONFIRM_TEXT = "确认删除项目"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("删除项目")
        self.setModal(True)
        self.resize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 警告标题
        title = TitleLabel("确认删除项目")
        title.setStyleSheet("color: #d32f2f;")
        layout.addWidget(title)
        
        # 提示信息
        info_label = BodyLabel(f"此操作不可恢复！\n\n请输入 \"{self.CONFIRM_TEXT}\" 以确认删除：")
        layout.addWidget(info_label)
        
        # 输入框
        self.confirm_input = LineEdit()
        self.confirm_input.setPlaceholderText(f"请输入：{self.CONFIRM_TEXT}")
        self.confirm_input.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.confirm_input)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        self.delete_btn = PrimaryPushButton("删除")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.on_confirm_delete)
        # 设置删除按钮为危险样式（红色）
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        button_layout.addWidget(self.delete_btn)
        layout.addLayout(button_layout)
        
    def on_text_changed(self, text):
        """输入文本变化时检查"""
        if text.strip() == self.CONFIRM_TEXT:
            self.delete_btn.setEnabled(True)
        else:
            self.delete_btn.setEnabled(False)
            
    def on_confirm_delete(self):
        """确认删除"""
        if self.confirm_input.text().strip() == self.CONFIRM_TEXT:
            self.accept()
        else:
            InfoBar.warning(
                title='提示',
                content=f'请输入正确的确认文字：{self.CONFIRM_TEXT}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

