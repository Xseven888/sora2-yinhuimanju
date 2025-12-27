"""
添加任务对话框
"""

import sys
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QFileDialog, QWidget
from qfluentwidgets import (
    TitleLabel, TextEdit, ComboBox, PushButton, PrimaryPushButton, BodyLabel, CardWidget
)

from database_manager import db_manager, model_manager
from utils.global_thread_pool import global_thread_pool
from threads.image_upload_thread import ImageUploadThread
from ui.drag_drop_text_edit import DragDropTextEdit

class AddTaskDialog(QDialog):
    """添加任务对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_urls = []
        self.selected_duration = db_manager.load_config('add_task_default_duration', 10)
        self.upload_threads = []  # 支持多个上传线程
        self.uploading_count = 0  # 正在上传的图片数量
        self.setWindowTitle("添加视频生成任务")
        self.setModal(True)
        self.resize(500, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = TitleLabel("创建视频生成任务")
        layout.addWidget(title)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)  # type: ignore
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore
        
        # 提示词
        self.prompt_input = TextEdit()
        self.prompt_input.setFixedHeight(100)
        self.prompt_input.setPlaceholderText("请输入视频生成的提示词，例如: make animate")
        form_layout.addRow("提示词:", self.prompt_input)
        
        # 分辨率选择
        self.resolution_combo = ComboBox()
        self.resolution_combo.addItem("横屏 (16:9)", None, "16:9")
        self.resolution_combo.addItem("竖屏 (9:16)", None, "9:16")
        _def_res = db_manager.load_config('add_task_default_resolution', '16:9')
        if _def_res == '16:9':
            self.resolution_combo.setCurrentIndex(0)
        elif _def_res == '9:16':
            self.resolution_combo.setCurrentIndex(1)
        else:
            self.resolution_combo.setCurrentIndex(0)
        form_layout.addRow("分辨率:", self.resolution_combo)
        
        # 时长选择 - 单选框
        self.duration_group = QWidget()
        duration_layout = QHBoxLayout(self.duration_group)

        self.duration_10 = PushButton("10秒")
        self.duration_10.setCheckable(True)
        self.duration_10.setChecked(True)
        self.duration_10.clicked.connect(lambda: self.set_duration(10))

        self.duration_15 = PushButton("15秒")
        self.duration_15.setCheckable(True)
        self.duration_15.clicked.connect(lambda: self.set_duration(15))

        # 按钮组样式
        button_style = """
            QPushButton {
                border: 2px solid #ccc;
                background-color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:checked {
                border-color: #007AFF;
                background-color: #007AFF;
                color: white;
            }
        """
        self.duration_10.setStyleSheet(button_style)
        self.duration_15.setStyleSheet(button_style)

        duration_layout.addWidget(self.duration_10)
        duration_layout.addWidget(self.duration_15)
        duration_layout.addStretch()

        form_layout.addRow("时长(秒):", self.duration_group)
        try:
            self.set_duration(int(self.selected_duration))
        except Exception:
            self.set_duration(10)
        
        layout.addLayout(form_layout)
        
        # 图片上传部分
        image_card = CardWidget()
        image_layout = QVBoxLayout(image_card)

        image_title = BodyLabel("图片上传 (支持多张)")
        image_title.setStyleSheet("font-weight: bold;")
        image_layout.addWidget(image_title)

        # 拖拽区域
        self.drop_area = DragDropTextEdit()
        self.drop_area.setFixedHeight(120)
        self.drop_area.setPlaceholderText("拖拽图片文件到这里\n支持 .png, .jpg, .jpeg, .gif, .webp, .bmp 等格式")
        self.drop_area.files_dropped.connect(self.handle_dropped_files)
        image_layout.addWidget(self.drop_area)

        # 已上传图片显示
        self.uploaded_images_label = BodyLabel("已添加图片: 0 张")
        image_layout.addWidget(self.uploaded_images_label)

        # 显示已上传的图片URL
        self.image_urls_display = DragDropTextEdit()
        self.image_urls_display.setReadOnly(True)
        self.image_urls_display.setFixedHeight(80)
        self.image_urls_display.files_dropped.connect(self.handle_dropped_files)
        image_layout.addWidget(self.image_urls_display)

        layout.addWidget(image_card)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_btn = PrimaryPushButton("创建任务")
        self.create_btn.clicked.connect(self.on_create_clicked)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
    def set_duration(self, duration):
        """设置时长"""
        self.selected_duration = duration
        # 更新按钮状态
        if duration == 10:
            self.duration_10.setChecked(True)
            self.duration_15.setChecked(False)
        else:
            self.duration_10.setChecked(False)
            self.duration_15.setChecked(True)

    def on_upload_progress(self, message):
        """上传进度回调"""
        print(message)  # 或者在界面上显示

    def on_upload_finished(self, success, message, image_url):
        """图片上传完成回调"""
        if success:
            self.image_urls.append(image_url)
            self.update_uploaded_images_display()
        else:
            print(f"上传失败: {message}")  # 或者在界面上显示错误
            
    def handle_dropped_files(self, file_paths):
        """处理拖拽的文件"""
        if not file_paths:
            return

        # 处理多个图片文件 - 并行上传
        uploaded_count = 0
        for file_path in file_paths:
            if self.is_image_file(file_path):
                # 并行上传图片
                self.upload_single_image(file_path)
                uploaded_count += 1

        if uploaded_count > 0:
            self.uploading_count = uploaded_count
            print(f"开始并行上传 {uploaded_count} 张图片")

    def upload_single_image(self, file_path):
        """上传单个图片"""
        # 使用预设的图床token
        token = "1c17b11693cb5ec63859b091c5b9c1b2"  # 预设token

        upload_thread = ImageUploadThread(file_path, token)
        upload_thread.progress.connect(self.on_upload_progress)
        upload_thread.finished.connect(self.on_upload_finished)
        global_thread_pool.submit(upload_thread)

        self.upload_threads.append(upload_thread)

    def update_uploaded_images_display(self):
        """更新已上传图片显示"""
        count = len(self.image_urls)
        self.uploaded_images_label.setText(f'已添加图片: {count} 张')

        if self.image_urls:
            urls_text = '\n'.join(self.image_urls)
            self.image_urls_display.setText(urls_text)
        else:
            self.image_urls_display.clear()

    def is_image_file(self, file_path):
        """检查是否是图片文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
        return Path(file_path).suffix.lower() in image_extensions

    def get_task_data(self):
        """获取任务数据"""
        # 获取当前选择的分辨率
        selected_index = self.resolution_combo.currentIndex()
        selected_resolution = self.resolution_combo.currentData()
        selected_text = self.resolution_combo.currentText()
        
        print(f"分辨率选择 - 索引: {selected_index}, 数据: {selected_resolution}, 文本: {selected_text}")
        
        # 如果 currentData() 返回 None，尝试通过索引获取
        if selected_resolution is None:
            # 根据索引获取对应的分辨率值
            if selected_index == 0:
                selected_resolution = "16:9"  # 横屏
            elif selected_index == 1:
                selected_resolution = "9:16"  # 竖屏
            else:
                selected_resolution = "16:9"  # 默认横屏
        
        print(f"最终选择的分辨率: {selected_resolution}")

        return {
            'prompt': self.prompt_input.toPlainText().strip(),
            'model': 'sora-2',  # 固定使用sora-2模型
            'aspect_ratio': selected_resolution,  # 添加分辨率参数
            'duration': self.selected_duration,
            'images': self.image_urls.copy()
        }

    def on_create_clicked(self):
        idx = self.resolution_combo.currentIndex()
        res = self.resolution_combo.currentData()
        if res is None:
            if idx == 0:
                res = "16:9"
            elif idx == 1:
                res = "9:16"
            else:
                res = "16:9"
        db_manager.save_config('add_task_default_resolution', res, 'string', '添加任务默认分辨率')
        db_manager.save_config('add_task_default_duration', int(self.selected_duration), 'integer', '添加任务默认时长')
        self.accept()
