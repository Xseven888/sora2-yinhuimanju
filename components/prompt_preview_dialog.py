"""
提示词预览对话框
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TitleLabel, TextEdit, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition
from PyQt5.QtCore import Qt


class PromptPreviewDialog(QDialog):
    """用于展示分析得到的提示词"""

    def __init__(self, prompt_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('提示词预览')
        self.resize(700, 500)
        self.prompt_text = prompt_text or ''
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = TitleLabel('提示词预览')
        layout.addWidget(title)

        self.text_edit = TextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(self.prompt_text)
        self.text_edit.setMinimumHeight(380)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        self.copy_btn = PushButton('复制到剪贴板')
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(self.copy_btn)

        btn_layout.addStretch()

        self.close_btn = PrimaryPushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def copy_to_clipboard(self):
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(self.prompt_text)
            InfoBar.success(
                title='已复制',
                content='提示词已复制到剪贴板',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception:
            InfoBar.error(
                title='错误',
                content='复制失败',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

