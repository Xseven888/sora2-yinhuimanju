"""
视频克隆对话框
"""

import sys
from pathlib import Path
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QFormLayout, QWidget
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from qfluentwidgets import (
    TitleLabel, TextEdit, PushButton, BodyLabel, CardWidget, InfoBar, InfoBarPosition, ProgressBar
)

from threads.video_analysis_thread import VideoAnalysisThread
from database_manager import db_manager
from utils.file_utils import format_file_size
from components.prompt_preview_dialog import PromptPreviewDialog

class DragDropVideoWidget(TextEdit):
    """支持拖拽的视频文件区域"""
    files_dropped = pyqtSignal(list)  # 添加文件拖拽信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("拖拽视频文件到这里\n支持 .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v 等格式")
        self.setReadOnly(True)
        
    def dragEnterEvent(self, e):  # type: ignore
        """拖拽进入事件"""
        if e is not None and hasattr(e, 'mimeData'):
            mime_data = e.mimeData()
            if mime_data is not None and hasattr(mime_data, 'hasUrls') and mime_data.hasUrls():
                if hasattr(mime_data, 'urls'):
                    urls = mime_data.urls()
                    for url in urls:
                        if url.isLocalFile():
                            file_path = url.toLocalFile()
                            if self.is_video_file(file_path):
                                e.acceptProposedAction()
                                return
        if e is not None:
            e.ignore()
            
    def dragMoveEvent(self, e):  # type: ignore
        """拖拽移动事件"""
        if e is not None and hasattr(e, 'mimeData'):
            mime_data = e.mimeData()
            if mime_data is not None and hasattr(mime_data, 'hasUrls') and mime_data.hasUrls():
                e.acceptProposedAction()
        elif e is not None:
            e.ignore()

    def dropEvent(self, e):  # type: ignore
        """拖拽放下事件"""
        if e is None or not hasattr(e, 'mimeData'):
            return
        mime_data = e.mimeData()
        if mime_data is None or not hasattr(mime_data, 'urls'):
            return
        urls = mime_data.urls()
        video_files = []

        for url in urls:
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if self.is_video_file(file_path):
                    video_files.append(file_path)

        if video_files:
            self.files_dropped.emit(video_files)
            e.acceptProposedAction()
        elif e is not None:
            # 显示错误提示
            InfoBar.warning(
                title='提示',
                content='请选择视频文件（支持 .mp4, .avi, .mov, .mkv, .wmv, .flv, .webm, .m4v 格式）',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self.parent() if self.parent() else None
            )
            e.ignore()

    def is_video_file(self, file_path):
        """检查是否是视频文件"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        return Path(file_path).suffix.lower() in video_extensions

class VideoCloneDialog(QDialog):
    """视频克隆对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_path = None
        self.analysis_thread = None
        self.setWindowTitle("视频克隆")
        self.setModal(True)
        self.resize(500, 420)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = TitleLabel("视频克隆")
        layout.addWidget(title)
        
        # 说明文本
        description = BodyLabel("拖拽视频文件到下方区域进行分析，分析结果将自动复制到剪切板")
        description.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(description)
        
        # 视频拖拽区域
        video_card = CardWidget()
        video_layout = QVBoxLayout(video_card)
        
        video_title = BodyLabel("拖拽视频文件到这里")
        video_title.setStyleSheet("font-weight: bold;")
        video_layout.addWidget(video_title)
        
        # 拖拽区域
        self.drop_area = DragDropVideoWidget(self)
        self.drop_area.setFixedHeight(120)
        self.drop_area.files_dropped.connect(self.handle_dropped_files)  # 连接信号
        video_layout.addWidget(self.drop_area)
        
        # 浏览按钮
        self.browse_btn = PushButton("浏览视频文件")
        self.browse_btn.clicked.connect(self.browse_video_file)
        video_layout.addWidget(self.browse_btn)
        
        layout.addWidget(video_card)
        
        # 移除分辨率与时长选择（根据需求）
        
        # 加载状态区域
        self.loading_widget = CardWidget()
        self.loading_widget.setVisible(False)  # 默认隐藏
        loading_layout = QVBoxLayout(self.loading_widget)
        
        loading_title = BodyLabel("正在处理视频...")
        loading_title.setStyleSheet("font-weight: bold;")
        loading_layout.addWidget(loading_title)
        
        # 进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        loading_layout.addWidget(self.progress_bar)
        
        # 进度文本
        self.progress_label = BodyLabel("准备中...")
        self.progress_label.setStyleSheet("color: #666; font-size: 12px;")
        loading_layout.addWidget(self.progress_label)
        
        layout.addWidget(self.loading_widget)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("关闭")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    # 移除时长设置方法

    def handle_dropped_files(self, file_paths):
        """处理拖拽的文件"""
        if not file_paths:
            return
            
        # 只处理第一个视频文件
        file_path = file_paths[0]
        
        # 检查文件大小
        if not self.check_file_size(file_path):
            return
            
        self.video_path = file_path
        file_size = os.path.getsize(file_path)
        self.drop_area.setText(f"已选择视频文件:\n{Path(file_path).name}\n\n路径: {file_path}\n大小: {format_file_size(file_size)}")
        # 自动开始分析
        self.start_analysis()
        
    def check_file_size(self, file_path):
        """检查视频文件大小"""
        try:
            file_size = os.path.getsize(file_path)
            # 20MB = 20 * 1024 * 1024 bytes
            max_size = 20 * 1024 * 1024
            
            if file_size > max_size:
                InfoBar.error(
                    title='文件过大',
                    content=f'视频文件大小为 {format_file_size(file_size)}，超过20MB限制',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return False
            return True
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'检查文件大小失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return False
        
    def browse_video_file(self):
        """浏览选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            str(Path.home()),
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v)"
        )
        
        if file_path:
            # 检查文件大小
            if not self.check_file_size(file_path):
                return
                
            self.video_path = file_path
            file_size = os.path.getsize(file_path)
            self.drop_area.setText(f"已选择视频文件:\n{Path(file_path).name}\n\n路径: {file_path}\n大小: {format_file_size(file_size)}")
            # 自动开始分析
            self.start_analysis()
            
    def start_analysis(self):
        """开始分析视频"""
        # 检查视频文件
        if not self.video_path:
            InfoBar.warning(
                title='提示',
                content='请先选择视频文件',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
            
        # 从设置中获取API Key
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            InfoBar.warning(
                title='提示',
                content='请先在设置中配置API Key',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
            
        # 移除分辨率选择逻辑
            
        # 显示加载状态
        self.show_loading_state()
            
        # 创建分析线程
        self.analysis_thread = VideoAnalysisThread(
            self.video_path,
            api_key
        )
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.result.connect(self.on_analysis_result)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()
        
    def show_loading_state(self):
        """显示加载状态"""
        # 禁用操作按钮
        self.browse_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.drop_area.setReadOnly(True)
        # 无分辨率/时长控件
        
        # 显示加载组件
        self.loading_widget.setVisible(True)
        self.progress_label.setText("准备中...")
        
    def hide_loading_state(self):
        """隐藏加载状态"""
        # 启用操作按钮
        self.browse_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.drop_area.setReadOnly(False)
        # 无分辨率/时长控件
        
        # 隐藏加载组件
        self.loading_widget.setVisible(False)
        
    def on_analysis_progress(self, message):
        """分析进度更新"""
        self.progress_label.setText(message)
        
    def on_analysis_result(self, result):
        """分析结果回调"""
        # 隐藏加载状态
        self.hide_loading_state()
        
        # 处理结果
        if isinstance(result, list):
            result_text = ""
            for item in result:
                # 构建按场景的详细文本（仅解析内容，无额外说明）
                result_text += f"时间: {item.get('time', '')}\n"
                result_text += f"内容: {item.get('content', '')}\n"
                if item.get('style'):
                    result_text += f"风格: {item.get('style', '')}\n"
                if item.get('narration'):
                    result_text += f"旁白: {item.get('narration', '')}\n"
                if item.get('dialogue'):
                    result_text += f"人物对话: {item.get('dialogue', '')}\n"
                if item.get('audio'):
                    result_text += f"音频/音乐: {item.get('audio', '')}\n"
                result_text += "\n"
                
            # 复制到剪切板
            self.copy_to_clipboard(result_text)
                
            InfoBar.success(
                title='成功',
                content=f'视频分析完成，结果已复制到剪切板',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 打开提示词预览对话框（不自动创建任务）
            try:
                preview = PromptPreviewDialog(result_text, self)
                preview.exec_()
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'打开预览失败: {str(e)}',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        else:
            InfoBar.warning(
                title='提示',
                content='分析完成但未返回有效结果',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
    # 取消自动任务创建逻辑，保留为预览展示
            
    def on_analysis_error(self, error_message):
        """分析错误回调"""
        # 隐藏加载状态
        self.hide_loading_state()
        
        # 显示错误信息
        InfoBar.error(
            title='错误',
            content=f'视频分析失败: {error_message}',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
    def copy_to_clipboard(self, text):
        """复制文本到剪切板"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
        except Exception as e:
            print(f"复制到剪切板失败: {e}")
