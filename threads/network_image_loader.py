"""
网络图片加载线程
"""

import requests
from io import BytesIO
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
from loguru import logger

class NetworkImageLoader(QThread):
    """网络图片加载线程"""
    image_loaded = pyqtSignal(str, QPixmap)  # image_url, pixmap
    load_failed = pyqtSignal(str)  # image_url

    def __init__(self):
        super().__init__()
        self.load_queue = []
        self.loading = False

    def load_image(self, image_url):
        """添加图片到加载队列"""
        if image_url not in self.load_queue:
            self.load_queue.append(image_url)
            if not self.loading:
                self.start()

    def run(self):
        """处理图片加载队列"""
        self.loading = True
        while self.load_queue:
            image_url = self.load_queue.pop(0)
            try:
                # 使用requests下载图片
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    # 从字节数据创建QPixmap
                    image_data = BytesIO(response.content)
                    pixmap = QPixmap()
                    if pixmap.loadFromData(image_data.getvalue()):
                        # 缩放图片到合适大小
                        scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # type: ignore
                        self.image_loaded.emit(image_url, scaled_pixmap)
                    else:
                        self.load_failed.emit(image_url)
                else:
                    self.load_failed.emit(image_url)
            except Exception as e:
                logger.error(f"加载图片失败 {image_url}: {e}")
                self.load_failed.emit(image_url)
        self.loading = False