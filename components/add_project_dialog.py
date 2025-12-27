"""
添加项目对话框 - 改进样式
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QFileDialog, QComboBox, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor
from qfluentwidgets import (
    TitleLabel, LineEdit, PushButton, PrimaryPushButton, TextEdit, BodyLabel
)
from pathlib import Path
import sqlite3
from database_manager import db_manager
from loguru import logger
from threads.novel_analysis_thread import NovelAnalysisThread
from qfluentwidgets import InfoBar, InfoBarPosition


class CoverImageWidget(QLabel):
    """封面图片预览控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        self.image_path = ''
        self.update_display()
        
    def set_image(self, image_path):
        """设置图片"""
        self.image_path = image_path
        self.update_display()
        
    def update_display(self):
        """更新显示"""
        if self.image_path and Path(self.image_path).exists():
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                # 缩放以适应大小
                scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.setPixmap(scaled_pixmap)
                return
        
        # 显示占位符
        self.clear()
        self.setText("封面\n图片")


class AddProjectDialog(QDialog):
    """添加项目对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加项目")
        self.setModal(True)
        self.resize(600, 700)
        self.cover_image_path = ''
        self.novel_file_path = ''
        self.novel_folder_path = ''
        self.analysis_thread = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("创建新项目")
        layout.addWidget(title)
        
        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        # 封面图片
        cover_layout = QHBoxLayout()
        cover_layout.setSpacing(15)
        cover_label = BodyLabel("封面图片:")
        cover_label.setFixedWidth(120)
        cover_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        cover_layout.addWidget(cover_label)
        
        cover_right_layout = QHBoxLayout()
        cover_right_layout.setSpacing(10)
        self.cover_widget = CoverImageWidget()
        cover_right_layout.addWidget(self.cover_widget)
        self.browse_cover_btn = PushButton("选择封面")
        self.browse_cover_btn.clicked.connect(self.browse_cover_image)
        cover_right_layout.addWidget(self.browse_cover_btn)
        cover_right_layout.addStretch()
        cover_layout.addLayout(cover_right_layout)
        form_layout.addLayout(cover_layout)
        
        # 项目标题
        title_layout = QHBoxLayout()
        title_label = BodyLabel("项目标题:")
        title_label.setFixedWidth(120)
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(title_label)
        self.title_input = LineEdit()
        self.title_input.setPlaceholderText("请输入项目标题")
        title_layout.addWidget(self.title_input)
        form_layout.addLayout(title_layout)
        
        # 小说文件/文件夹
        novel_layout = QHBoxLayout()
        novel_label = BodyLabel("小说文件/文件夹:")
        novel_label.setFixedWidth(120)
        novel_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        novel_layout.addWidget(novel_label)
        self.novel_path_input = LineEdit()
        self.novel_path_input.setPlaceholderText("请选择小说文件或文件夹")
        self.novel_path_input.setReadOnly(True)
        novel_layout.addWidget(self.novel_path_input)
        self.browse_novel_btn = PushButton("选择路径")
        self.browse_novel_btn.clicked.connect(self.browse_novel)
        novel_layout.addWidget(self.browse_novel_btn)
        form_layout.addLayout(novel_layout)
        
        # 换风格
        style_layout = QHBoxLayout()
        style_label = BodyLabel("换风格:")
        style_label.setFixedWidth(120)
        style_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        style_layout.addWidget(style_label)
        self.style_input = LineEdit()
        self.style_input.setPlaceholderText("请输入换风格提示词")
        style_layout.addWidget(self.style_input)
        form_layout.addLayout(style_layout)
        
        # 视频比例
        ratio_layout = QHBoxLayout()
        ratio_label = BodyLabel("视频比例:")
        ratio_label.setFixedWidth(120)
        ratio_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ratio_layout.addWidget(ratio_label)
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(['9:16', '16:9'])
        self.aspect_ratio_combo.setCurrentText('9:16')
        ratio_layout.addWidget(self.aspect_ratio_combo)
        ratio_layout.addStretch()
        form_layout.addLayout(ratio_layout)
        
        # 简介
        desc_layout = QHBoxLayout()
        desc_layout.setAlignment(Qt.AlignTop)
        desc_label = BodyLabel("简介:")
        desc_label.setFixedWidth(120)
        desc_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        desc_layout.addWidget(desc_label)
        self.description_input = TextEdit()
        self.description_input.setPlaceholderText("请输入项目简介，或留空AI自动生成")
        self.description_input.setMaximumHeight(100)
        desc_layout.addWidget(self.description_input)
        form_layout.addLayout(desc_layout)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.confirm_btn = PrimaryPushButton("确定")
        self.confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addWidget(self.confirm_btn)
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
    def browse_cover_image(self):
        """浏览封面图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择封面图片",
            str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )
        if file_path:
            self.cover_image_path = file_path
            self.cover_widget.set_image(file_path)
            
    def browse_novel(self):
        """浏览小说文件或文件夹"""
        # 先尝试选择文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择小说文件",
            str(Path.home()),
            "文本文件 (*.txt *.md)"
        )
        if file_path:
            self.novel_file_path = file_path
            self.novel_folder_path = ''
            self.novel_path_input.setText(file_path)
            # 自动分析生成简介
            self.auto_generate_description(file_path)
        else:
            # 如果取消，尝试选择文件夹
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "选择小说文件夹",
                str(Path.home())
            )
            if folder_path:
                self.novel_folder_path = folder_path
                self.novel_file_path = ''
                self.novel_path_input.setText(folder_path)
                # 文件夹暂不支持自动分析，需要用户手动输入简介
                InfoBar.info(
                    title='提示',
                    content='选择文件夹后，请手动输入简介或留空让AI自动生成',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                
    def auto_generate_description(self, file_path: str):
        """自动分析生成简介"""
        # 检查API Key
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            InfoBar.warning(
                title='提示',
                content='请先在设置中配置API Key才能自动生成简介',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        # 停止之前的分析线程（如果存在）
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.terminate()
            self.analysis_thread.wait()

        # 显示分析提示
        InfoBar.info(
            title='分析中',
            content='正在分析小说内容，生成简介...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

        # 创建并启动分析线程
        self.analysis_thread = NovelAnalysisThread(file_path, self)
        self.analysis_thread.progress.connect(self.on_analysis_progress)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.error.connect(self.on_analysis_error)
        self.analysis_thread.start()

    def on_analysis_progress(self, message: str):
        """分析进度回调"""
        logger.info(f"分析进度: {message}")

    def on_analysis_finished(self, description: str):
        """分析完成回调"""
        # 将简介填入输入框
        self.description_input.setPlainText(description)
        
        InfoBar.success(
            title='成功',
            content='简介已自动生成',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def on_analysis_error(self, error_message: str):
        """分析错误回调"""
        InfoBar.error(
            title='分析失败',
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
    def on_confirm(self):
        """确认创建项目"""
        title = self.title_input.text().strip()
        if not title:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title='提示',
                content='请输入项目标题',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
            
        # 保存到数据库
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO projects 
                (title, cover_image, novel_file_path, novel_folder_path, style, aspect_ratio, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                title,
                self.cover_image_path,
                self.novel_file_path,
                self.novel_folder_path,
                self.style_input.text().strip(),
                self.aspect_ratio_combo.currentText(),
                self.description_input.toPlainText().strip()
            ))
            conn.commit()
            conn.close()
            
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title='成功',
                content='项目创建成功',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            self.accept()
        except Exception as e:
            logger.error(f"创建项目失败: {e}")
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title='错误',
                content=f'创建项目失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def closeEvent(self, event):
        """对话框关闭事件"""
        # 停止分析线程
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.terminate()
            self.analysis_thread.wait()
        super().closeEvent(event)
