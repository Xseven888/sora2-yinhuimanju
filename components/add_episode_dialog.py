"""
添加剧集对话框
"""

import sqlite3
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel
from qfluentwidgets import (
    TitleLabel, BodyLabel, LineEdit, PushButton, PrimaryPushButton, 
    InfoBar, InfoBarPosition, TextEdit
)
from database_manager import db_manager
from loguru import logger


class DragDropDocumentWidget(TextEdit):
    """支持拖拽的文档文件区域"""
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("拖拽文档文件到这里\n支持 .txt, .md 格式")
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setStyleSheet("background-color: #fafafa; border: 2px dashed #ddd; border-radius: 4px; padding: 20px; text-align: center;")
        
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
                            if self.is_document_file(file_path):
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
        document_files = []
        
        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if self.is_document_file(file_path):
                    document_files.append(file_path)
        
        if document_files:
            self.files_dropped.emit(document_files)
            e.acceptProposedAction()
        elif e is not None:
            e.ignore()
    
    def is_document_file(self, file_path):
        """检查是否是文档文件"""
        document_extensions = {'.txt', '.md'}
        return Path(file_path).suffix.lower() in document_extensions


class AddEpisodeDialog(QDialog):
    """添加剧集对话框"""
    
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.document_path = None
        self.setWindowTitle("添加剧集")
        self.setModal(True)
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("添加剧集")
        layout.addWidget(title)
        
        # 第几集输入
        episode_number_label = BodyLabel("第几集:")
        layout.addWidget(episode_number_label)
        
        self.episode_number_input = LineEdit()
        self.episode_number_input.setPlaceholderText("例如: 1 或 第一集")
        layout.addWidget(self.episode_number_input)
        
        # 文档上传区域
        document_label = BodyLabel("上传文档:")
        layout.addWidget(document_label)
        
        # 拖拽区域
        self.drag_drop_area = DragDropDocumentWidget(self)
        self.drag_drop_area.files_dropped.connect(self.on_files_dropped)
        layout.addWidget(self.drag_drop_area)
        
        # 选择文件按钮
        file_button_layout = QHBoxLayout()
        file_button_layout.addStretch()
        
        self.select_file_btn = PushButton("选择文件")
        self.select_file_btn.clicked.connect(self.select_file)
        file_button_layout.addWidget(self.select_file_btn)
        
        layout.addLayout(file_button_layout)
        
        # 文件路径显示
        self.file_path_label = BodyLabel("")
        self.file_path_label.setStyleSheet("color: #666; font-size: 12px;")
        self.file_path_label.setWordWrap(True)
        layout.addWidget(self.file_path_label)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = PrimaryPushButton("确定")
        confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文档文件",
            str(Path.home()),
            "文档文件 (*.txt *.md)"
        )
        if file_path:
            self.set_document_path(file_path)
    
    def on_files_dropped(self, file_paths):
        """处理拖拽的文件"""
        if file_paths:
            # 只取第一个文件
            self.set_document_path(file_paths[0])
    
    def set_document_path(self, file_path):
        """设置文档路径"""
        self.document_path = file_path
        file_name = Path(file_path).name
        # 显示文件名和路径
        display_text = f"已选择文件:\n{file_name}\n\n文件路径:\n{file_path}"
        self.drag_drop_area.setPlainText(display_text)
        self.drag_drop_area.setStyleSheet("background-color: #f5f5f5; border: 2px dashed #ccc; border-radius: 4px; padding: 10px;")
        self.file_path_label.setText(f"文件: {file_name}")
    
    def _chinese_to_number(self, text):
        """将中文数字转换为阿拉伯数字"""
        # 移除"集"字
        text = text.replace('集', '').strip()
        
        # 中文数字映射
        chinese_digits = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
            '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10
        }
        
        # 如果是纯中文数字（如"第一"、"第二"）
        if text.startswith('第'):
            text = text[1:]  # 移除"第"字
        
        # 处理"十"的特殊情况
        if text == '十':
            return 10
        elif text.startswith('十'):
            # 如"十一"、"十二"
            if len(text) == 2:
                return 10 + chinese_digits.get(text[1], 0)
            else:
                # 如"二十"、"三十"
                return chinese_digits.get(text[0], 0) * 10
        elif text.endswith('十'):
            # 如"二十"、"三十"
            return chinese_digits.get(text[0], 0) * 10
        elif '十' in text:
            # 如"二十一"、"三十二"
            parts = text.split('十')
            if len(parts) == 2:
                tens = chinese_digits.get(parts[0], 0) * 10 if parts[0] else 10
                ones = chinese_digits.get(parts[1], 0) if parts[1] else 0
                return tens + ones
        
        # 单个中文数字
        if text in chinese_digits:
            return chinese_digits[text]
        
        return None
    
    def on_confirm(self):
        """确认添加"""
        # 验证集数
        episode_number_text = self.episode_number_input.text().strip()
        if not episode_number_text:
            InfoBar.warning(
                title='提示',
                content='请输入第几集（例如：1 或 第一集）',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 尝试解析集数
        episode_number = None
        
        # 先尝试直接转换为数字
        try:
            episode_number = int(episode_number_text)
        except ValueError:
            # 如果不是数字，尝试解析中文数字
            episode_number = self._chinese_to_number(episode_number_text)
        
        # 如果仍然无法解析
        if episode_number is None:
            InfoBar.warning(
                title='格式错误',
                content='请输入有效的集数（例如：1、2、3 或 第一集、第二集、第三集）',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 验证集数范围
        if episode_number <= 0:
            InfoBar.warning(
                title='格式错误',
                content='集数必须大于0',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 验证文档
        if not self.document_path or not Path(self.document_path).exists():
            InfoBar.warning(
                title='提示',
                content='请选择或拖拽文档文件',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 检查集数是否已存在
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM episodes
                WHERE project_id = ? AND episode_number = ?
            ''', (self.project_id, episode_number))
            existing = cursor.fetchone()
            conn.close()
            
            if existing:
                InfoBar.warning(
                    title='提示',
                    content=f'第{episode_number}集已存在',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
        except Exception as e:
            logger.error(f"检查集数失败: {e}")
        
        # 保存到数据库
        try:
            # 复制文件到项目目录
            project_dir = Path(db_manager.app_data_dir) / "projects" / str(self.project_id) / "episodes"
            project_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = Path(self.document_path).name
            dest_path = project_dir / f"episode_{episode_number}_{file_name}"
            
            import shutil
            shutil.copy2(self.document_path, dest_path)
            
            # 保存到数据库
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO episodes (project_id, episode_number, episode_name, file_path)
                VALUES (?, ?, ?, ?)
            ''', (
                self.project_id,
                episode_number,
                f"第{episode_number}集",
                str(dest_path)
            ))
            conn.commit()
            conn.close()
            
            InfoBar.success(
                title='成功',
                content=f'第{episode_number}集已添加',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"添加剧集失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'添加剧集失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

