"""
主页界面
"""

from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog, QDialog
from qfluentwidgets import (
    TitleLabel, TextEdit, PushButton, PrimaryPushButton, RadioButton, BodyLabel, FluentIcon
)

from ui.flow_layout import FlowLayout
from ui.drag_drop_text_edit import DragDropTextEdit
from threads.image_upload_thread import ImageUploadThread

class HomeInterface(QWidget):
    """主页界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.image_urls = []
        self.selected_duration = 10  # 默认10秒
        self.selected_orientation = 'portrait'  # 默认竖屏
        self.upload_threads = []  # 支持多个上传线程
        self.setObjectName("homeInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        # 标题
        title = TitleLabel('Sora 2 视频生成')
        title.setAlignment(Qt.AlignCenter)  # type: ignore
        layout.addWidget(title)

        # 提示词输入区域
        prompt_group = QGroupBox("提示词")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_input = TextEdit()
        self.prompt_input.setPlaceholderText("请输入视频生成提示词...\n例如：一只可爱的小猫在花园里玩耍")
        self.prompt_input.setMaximumHeight(120)
        prompt_layout.addWidget(self.prompt_input)

        layout.addWidget(prompt_group)

        # 图片上传区域
        image_group = QGroupBox("图片（可选）")
        image_layout = QVBoxLayout(image_group)

        # 图片显示区域
        self.image_display = FlowLayout()

        # 图片上传控件
        upload_layout = QHBoxLayout()
        self.upload_btn = PushButton(FluentIcon.ADD, '添加图片')
        self.upload_btn.clicked.connect(self.select_images)
        upload_layout.addWidget(self.upload_btn)

        self.clear_images_btn = PushButton(FluentIcon.DELETE, '清空图片')
        self.clear_images_btn.clicked.connect(self.clear_images)
        self.clear_images_btn.setEnabled(False)
        upload_layout.addWidget(self.clear_images_btn)
        upload_layout.addStretch()

        image_layout.addLayout(upload_layout)
        image_layout.addLayout(self.image_display)

        # 已上传图片数量显示
        self.uploaded_images_label = BodyLabel('已添加图片: 0 张')
        self.uploaded_images_label.setStyleSheet("color: #666; font-size: 12px;")
        image_layout.addWidget(self.uploaded_images_label)

        layout.addWidget(image_group)

        # 参数设置区域
        settings_group = QGroupBox("生成参数")
        settings_layout = QVBoxLayout(settings_group)

        # 横竖屏选择
        orientation_layout = QHBoxLayout()
        orientation_label = BodyLabel("屏幕方向:")
        orientation_layout.addWidget(orientation_label)

        self.portrait_radio = RadioButton("竖屏 (9:16)")
        self.landscape_radio = RadioButton("横屏 (16:9)")
        
        # 默认选中竖屏
        self.portrait_radio.setChecked(True)
        
        # 连接信号
        self.portrait_radio.toggled.connect(self.on_orientation_changed)
        
        orientation_layout.addWidget(self.portrait_radio)
        orientation_layout.addWidget(self.landscape_radio)
        orientation_layout.addStretch()
        settings_layout.addLayout(orientation_layout)

        # 时长选择
        duration_layout = QHBoxLayout()
        duration_label = BodyLabel("视频时长:")
        duration_layout.addWidget(duration_label)

        self.duration_10_radio = RadioButton("10秒")
        self.duration_15_radio = RadioButton("15秒")
        
        # 默认选中10秒
        self.duration_10_radio.setChecked(True)
        
        # 连接信号
        self.duration_10_radio.toggled.connect(self.on_duration_changed)
        
        duration_layout.addWidget(self.duration_10_radio)
        duration_layout.addWidget(self.duration_15_radio)
        duration_layout.addStretch()
        settings_layout.addLayout(duration_layout)

        layout.addWidget(settings_group)

        # 批量添加按钮（位于生成视频按钮上方）
        self.batch_add_btn = PushButton('批量添加')
        self.batch_add_btn.clicked.connect(self.show_image_batch_add_dialog)
        self.batch_add_btn.setFixedHeight(36)
        layout.addWidget(self.batch_add_btn)

        # 生成按钮
        self.add_task_btn = PrimaryPushButton(FluentIcon.PLAY, '生成视频')
        self.add_task_btn.clicked.connect(self.add_task)
        self.add_task_btn.setFixedHeight(40)
        layout.addWidget(self.add_task_btn)

        layout.addStretch()

    def on_orientation_changed(self):
        """横竖屏选择改变"""
        if self.portrait_radio.isChecked():
            self.selected_orientation = 'portrait'
        else:
            self.selected_orientation = 'landscape'

    def on_duration_changed(self):
        """时长选择改变"""
        if self.duration_10_radio.isChecked():
            self.selected_duration = 10
        else:
            self.selected_duration = 15

    def select_images(self):
        """选择图片文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )

        if file_paths:
            # 上传所有选中的图片
            for file_path in file_paths:
                self.upload_single_image(file_path)

    def upload_single_image(self, file_path):
        """上传单个图片"""
        # 使用预设的图床token
        token = "1c17b11693cb5ec63859b091c5b9c1b2"  # 预设token

        upload_thread = ImageUploadThread(file_path, token)
        upload_thread.progress.connect(self.on_upload_progress)
        upload_thread.finished.connect(self.on_upload_finished)
        upload_thread.start()

        self.upload_threads.append(upload_thread)

    def on_upload_progress(self, message):
        """上传进度回调"""
        print(message)

    def on_upload_finished(self, success, message, url):
        """上传完成回调"""
        if success:
            self.image_urls.append(url)
            self.update_uploaded_images_display()
            
            # 添加图片预览
            from ui.image_widget import ImageWidget
            image_widget = ImageWidget(url)
            self.image_display.addWidget(image_widget)
            
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title='成功',
                content=f'图片上传成功',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title='失败',
                content=f'图片上传失败: {message}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

        # 清理完成的线程
        sender = self.sender()
        if sender in self.upload_threads:
            self.upload_threads.remove(sender)

    def update_uploaded_images_display(self):
        """更新已上传图片显示"""
        count = len(self.image_urls)
        self.uploaded_images_label.setText(f'已添加图片: {count} 张')
        self.clear_images_btn.setEnabled(count > 0)

        if self.image_urls:
            urls_text = '\n'.join(self.image_urls)
        else:
            urls_text = ''

    def clear_images(self):
        """清空图片"""
        self.image_urls.clear()
        self.update_uploaded_images_display()
        
        # 清空图片显示区域
        while self.image_display.count():
            widget = self.image_display.takeAt(0)
            if widget and widget.widget():
                widget.widget().deleteLater()
                
        self.clear_images_btn.setEnabled(False)
        
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title='成功',
            content='已清空所有图片',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def add_task(self):
        """添加任务"""
        prompt = self.prompt_input.toPlainText().strip()
        
        if not prompt:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title='提示',
                content='请输入提示词',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        # 准备任务数据
        # 根据选择的方向确定参数
        if self.selected_orientation == 'landscape':
            model = 'sora-2'
            aspect_ratio = '16:9'
        else:
            model = 'sora-2'
            aspect_ratio = '9:16'
            
        task_data = {
            'prompt': prompt,
            'model': model,
            'aspect_ratio': aspect_ratio,
            'duration': self.selected_duration,
            'images': self.image_urls.copy()
        }

        # 调用父窗口的生成方法
        if self._parent:
            self._parent.generate_video(task_data)
        
        # 清空输入
        self.prompt_input.clear()
        self.clear_images()

    def show_image_batch_add_dialog(self):
        """显示拖拽图片的批量添加对话框"""
        try:
            from components.image_batch_add_dialog import ImageBatchAddDialog
            # 根据当前选择设置默认值
            default_prompt = self.prompt_input.toPlainText().strip()
            default_resolution = '9:16' if self.selected_orientation == 'portrait' else '16:9'
            default_duration = self.selected_duration

            dialog = ImageBatchAddDialog(self.window(), default_prompt, default_resolution, default_duration)
            if dialog.exec_() == QDialog.Accepted:
                tasks = dialog.get_tasks_data()
                if not tasks:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.warning(
                        title='提示',
                        content='没有可创建的任务（请拖拽图片且上传成功）',
                        orient=Qt.Horizontal,  # type: ignore
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return

                parent_window = self._parent
                if parent_window and hasattr(parent_window, 'generate_video'):
                    for t in tasks:
                        task_data = {
                            'prompt': t.get('prompt', ''),
                            'model': 'sora-2',
                            'aspect_ratio': t.get('resolution', default_resolution),
                            'duration': t.get('duration', default_duration),
                            'images': t.get('images', [])
                        }
                        parent_window.generate_video(task_data)
        except Exception as e:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title='错误',
                content=f'打开批量添加对话框失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
