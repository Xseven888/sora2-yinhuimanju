"""
角色卡片组件
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from qfluentwidgets import CardWidget, BodyLabel
from ui.image_widget import ImageWidget


class CharacterCard(CardWidget):
    """角色卡片"""
    character_clicked = pyqtSignal(int)  # 角色ID
    
    def __init__(self, character_data, parent=None):
        super().__init__(parent)
        self.character_id = character_data.get('id')
        self.character_data = character_data
        self.setFixedSize(150, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 角色图片（使用正面图，如果没有则显示占位符）
        front_image = self.character_data.get('front_image', '')
        self.image_widget = ImageWidget(front_image, size=130)
        self.image_widget.setFixedSize(130, 130)
        layout.addWidget(self.image_widget)
        
        # 角色名字
        name = BodyLabel(self.character_data.get('name', '未命名角色'))
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-weight: bold; font-size: 12px;")
        name.setWordWrap(True)
        layout.addWidget(name)
        
        # Sora角色名（如果有）
        sora_username = self.character_data.get('sora_character_username', '')
        if sora_username:
            sora_label = BodyLabel(f"Sora: {sora_username}")
            sora_label.setAlignment(Qt.AlignCenter)
            sora_label.setStyleSheet("color: #666; font-size: 10px;")
            sora_label.setWordWrap(True)
            layout.addWidget(sora_label)
        
        layout.addStretch()
        
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        try:
            if event.button() == Qt.LeftButton:
                self.character_clicked.emit(self.character_id)
            super().mouseReleaseEvent(event)
        except RuntimeError:
            # 对象已被删除，忽略错误
            pass

