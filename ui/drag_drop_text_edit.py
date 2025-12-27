"""
支持拖拽的TextEdit
"""

from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import TextEdit

class DragDropTextEdit(TextEdit):
    """支持拖拽的TextEdit"""
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(True)
        self.setPlaceholderText("点击下方按钮选择图片，或直接拖拽图片到这里")

    def dragEnterEvent(self, e):
        """拖拽进入事件"""
        if e is not None and hasattr(e, 'mimeData'):
            mime_data = e.mimeData()
            if mime_data is not None and hasattr(mime_data, 'hasUrls') and mime_data.hasUrls():
                if hasattr(mime_data, 'urls'):
                    urls = mime_data.urls()
                    for url in urls:
                        if url.isLocalFile():
                            file_path = url.toLocalFile()
                            if self.is_image_file(file_path):
                                e.acceptProposedAction()
                                return
        if e is not None:
            e.ignore()

    def dragMoveEvent(self, e):
        """拖拽移动事件"""
        if e is not None and hasattr(e, 'mimeData'):
            mime_data = e.mimeData()
            if mime_data is not None and hasattr(mime_data, 'hasUrls') and mime_data.hasUrls():
                e.acceptProposedAction()
        elif e is not None:
            e.ignore()

    def dropEvent(self, e):
        """拖拽放下事件"""
        if e is None or not hasattr(e, 'mimeData'):
            return
        mime_data = e.mimeData()
        if mime_data is None or not hasattr(mime_data, 'urls'):
            return
        urls = mime_data.urls()
        image_files = []

        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if self.is_image_file(file_path):
                    image_files.append(file_path)

        if image_files:
            self.files_dropped.emit(image_files)
            e.acceptProposedAction()
        elif e is not None:
            e.ignore()

    def is_image_file(self, file_path):
        """检查是否是图片文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
        return Path(file_path).suffix.lower() in image_extensions