"""
图片显示控件
"""

import sys
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap

class ImageWidget(QWidget):
    """图片显示控件"""
    def __init__(self, image_url=None, parent=None, size: int = 100):
        super().__init__(parent)
        self.image_url = image_url
        self.pixmap = None
        self._size = max(60, int(size))
        self.setFixedSize(self._size, self._size)
        self.init_ui()
        
        # 如果初始化时提供了图片路径，尝试加载
        if image_url:
            self.load_image(image_url)

    def init_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)

        self.image_label = QLabel()
        inner = max(40, self._size - 10)
        self.image_label.setFixedSize(inner, inner)
        self.image_label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9;")
        self._layout.addWidget(self.image_label)

        # 显示占位符
        self.show_placeholder()

    def show_placeholder(self):
        """显示占位符"""
        self.image_label.setText("无图片")
        self.image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9; color: #999;")

    def load_image(self, image_path):
        """从文件路径或URL加载图片"""
        if not image_path:
            self.show_placeholder()
            return
            
        # 检查是否是本地文件路径
        file_path = Path(image_path)
        if file_path.exists() and file_path.is_file():
            # 本地文件
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                self.set_image(image_path, pixmap)
            else:
                self.show_placeholder()
        elif image_path.startswith('http://') or image_path.startswith('https://'):
            # URL（暂时不支持，显示占位符）
            self.image_url = image_path
            self.show_placeholder()
        else:
            # 无效路径
            self.show_placeholder()

    def set_image(self, image_url, pixmap=None):
        """设置图片"""
        self.image_url = image_url
        
        # 如果没有提供pixmap，尝试从路径加载
        if not pixmap and image_url:
            file_path = Path(image_url)
            if file_path.exists() and file_path.is_file():
                pixmap = QPixmap(str(file_path))
                if pixmap.isNull():
                    self.show_placeholder()
                    return
            else:
                self.show_placeholder()
                return
        
        if pixmap:
            self.pixmap = pixmap
            # 缩放图片以适应标签大小
            target_w = self.image_label.width()
            target_h = self.image_label.height()
            scaled_pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setText("")
            self.image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 4px; background-color: white;")
        else:
            self.show_placeholder()

    def get_image_url(self):
        """获取图片URL"""
        return self.image_url
