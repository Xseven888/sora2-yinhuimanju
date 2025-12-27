"""
添加商品对话框（仅UI）

包含：商品标题输入、主图拖拽区域与预览、确定/取消按钮。
不实现保存或入库逻辑，仅用于界面展示。
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import TitleLabel, BodyLabel, TextEdit, PrimaryPushButton, PushButton, InfoBar, InfoBarPosition

from ui.drag_drop_text_edit import DragDropTextEdit


class GoodsAddDialog(QDialog):
    """添加商品对话框（UI骨架）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('添加商品')
        self.resize(520, 420)

        self.title_text = ''
        self.main_image_path = ''

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 标题
        layout.addWidget(TitleLabel('添加商品'))

        # 商品标题输入（多行）
        layout.addWidget(BodyLabel('商品标题'))
        self.title_input = TextEdit()
        self.title_input.setPlaceholderText('请输入商品标题（支持多行）')
        self.title_input.setMinimumHeight(80)
        self.title_input.textChanged.connect(self.on_title_changed)
        layout.addWidget(self.title_input)

        # 主图拖拽区域
        layout.addWidget(BodyLabel('主图（拖拽图片到此区域）'))
        self.drop_area = DragDropTextEdit()
        self.drop_area.files_dropped.connect(self.on_files_dropped)
        self.drop_area.setMinimumHeight(120)
        layout.addWidget(self.drop_area)

        # 预览
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet('border: 1px dashed #ccc;')
        self.preview_label.setFixedHeight(140)
        layout.addWidget(self.preview_label)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.ok_btn = PrimaryPushButton('确定')
        self.ok_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def on_title_changed(self):
        # TextEdit 的 textChanged 不携带文本参数
        self.title_text = self.title_input.toPlainText().strip()

    def on_files_dropped(self, files: list):
        if not files:
            return
        # 仅使用第一张图片
        path = files[0]
        self.main_image_path = path
        self.update_preview(path)

        InfoBar.success(
            title='已选择主图',
            content='图片已加载预览',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )

    def update_preview(self, path: str):
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.preview_label.width(), self.preview_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
        except Exception:
            # 忽略预览失败
            pass

    def on_confirm(self):
        # 仅UI占位，不保存数据
        InfoBar.info(
            title='提示',
            content='当前仅为UI演示，功能稍后实现',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        self.accept()

    # 供后续功能使用的数据访问器
    def get_title(self) -> str:
        return self.title_text

    def get_main_image(self) -> str:
        return self.main_image_path
