"""
设置界面 - 保留保存/加载逻辑
"""

import os
import platform
import subprocess
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QComboBox
from PyQt5.QtGui import QMouseEvent
from qfluentwidgets import (
    TitleLabel, BodyLabel, LineEdit, PushButton, PrimaryPushButton, CardWidget, CheckBox,
    InfoBar, InfoBarPosition
)

from database_manager import db_manager
from constants import APP_VERSION, DISPLAY_API_PROXY_URL, WECHAT_ID


class SettingsInterface(QWidget):
    """设置界面 - 保留保存/加载逻辑"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsInterface")
        self.init_ui()
        # 加载已保存的设置
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = TitleLabel('设置')
        layout.addWidget(title)

        # 版本信息卡片
        version_card = CardWidget()
        version_layout = QVBoxLayout(version_card)

        version_title = BodyLabel('关于')
        version_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        version_layout.addWidget(version_title)

        # 版本号
        version_label = BodyLabel(f'版本: v{APP_VERSION}')
        version_label.setStyleSheet("color: #666; font-size: 13px;")
        version_layout.addWidget(version_label)

        # API地址 - 可点击打开
        api_url_layout = QHBoxLayout()
        api_prefix = BodyLabel('API代理:')
        api_prefix.setStyleSheet("color: #666; font-size: 13px;")
        api_url_layout.addWidget(api_prefix)
        
        self.api_url_label = BodyLabel(DISPLAY_API_PROXY_URL)
        self.api_url_label.setStyleSheet("""
            color: #007AFF;
            font-size: 13px;
            text-decoration: underline;
        """)
        self.api_url_label.setToolTip('点击打开网址')
        self.api_url_label.mousePressEvent = self.open_api_url
        api_url_layout.addWidget(self.api_url_label)
        api_url_layout.addStretch()
        version_layout.addLayout(api_url_layout)

        # 作者联系方式
        contact_title = BodyLabel('作者联系方式:')
        contact_title.setStyleSheet("color: #666; font-size: 13px; font-weight: bold;")
        version_layout.addWidget(contact_title)

        # 微信号 - 可点击复制
        wechat_layout = QHBoxLayout()
        wechat_prefix = BodyLabel('微信:')
        wechat_prefix.setStyleSheet("color: #666; font-size: 12px;")
        wechat_layout.addWidget(wechat_prefix)
        
        self.wechat_label = BodyLabel(WECHAT_ID)
        self.wechat_label.setStyleSheet("""
            color: #007AFF;
            font-size: 12px;
            text-decoration: underline;
        """)
        self.wechat_label.setToolTip('点击复制微信号')
        self.wechat_label.mousePressEvent = self.copy_wechat_id
        wechat_layout.addWidget(self.wechat_label)
        wechat_layout.addStretch()
        version_layout.addLayout(wechat_layout)

        layout.addWidget(version_card)

        # API Key 设置
        api_card = CardWidget()
        api_layout = QVBoxLayout(api_card)

        api_title = BodyLabel('API 配置')
        api_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        api_layout.addWidget(api_title)

        # API Key输入
        api_key_label = BodyLabel('API Key:')
        api_layout.addWidget(api_key_label)
        self.api_key_input = LineEdit()
        self.api_key_input.setPlaceholderText('请输入您的 Sora API Key')
        self.api_key_input.textChanged.connect(self.save_api_key)
        api_layout.addWidget(self.api_key_input)

        # 视频保存路径
        video_path_label = BodyLabel('视频保存路径:')
        api_layout.addWidget(video_path_label)
        self.video_path_input = LineEdit()
        self.video_path_input.setPlaceholderText('选择视频保存路径，留空则使用默认路径')
        self.video_path_input.textChanged.connect(self.save_video_path)
        api_layout.addWidget(self.video_path_input)

        # 选择路径按钮
        self.browse_video_path_btn = PushButton("浏览")
        self.browse_video_path_btn.clicked.connect(self.browse_video_path)
        api_layout.addWidget(self.browse_video_path_btn)

        # 模型选择
        model_title = BodyLabel('模型选择')
        model_title.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        api_layout.addWidget(model_title)

        # 分析模型选择
        analysis_model_label = BodyLabel('分析模型:')
        api_layout.addWidget(analysis_model_label)
        self.analysis_model_combo = QComboBox()
        self.analysis_model_combo.addItems(['gemini-3-pro-preview', 'gpt-5-chat-latest'])
        self.analysis_model_combo.currentTextChanged.connect(self.save_analysis_model)
        api_layout.addWidget(self.analysis_model_combo)

        # 生图模型选择
        image_model_label = BodyLabel('生图模型:')
        api_layout.addWidget(image_model_label)
        self.image_model_combo = QComboBox()
        self.image_model_combo.addItems(['gemini-3-pro-image-preview', 'gemini-2.5-flash-image-preview'])
        self.image_model_combo.currentTextChanged.connect(self.save_image_model)
        api_layout.addWidget(self.image_model_combo)

        # 保存按钮
        self.save_settings_btn = PrimaryPushButton('保存设置')
        self.save_settings_btn.clicked.connect(self.save_settings)
        api_layout.addWidget(self.save_settings_btn)

        layout.addWidget(api_card)

        # 阿里云 OSS 配置卡片
        oss_card = CardWidget()
        oss_layout = QVBoxLayout(oss_card)

        oss_title = BodyLabel('阿里云 OSS 配置（可选）')
        oss_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        oss_layout.addWidget(oss_title)

        # OSS说明
        oss_desc = BodyLabel('配置后，图片和视频将上传到阿里云 OSS 存储。需要确保 Bucket 已开启公共读写权限。')
        oss_desc.setStyleSheet("color: #666; font-size: 12px;")
        oss_layout.addWidget(oss_desc)

        # OSS Bucket 域名输入
        oss_bucket_label = BodyLabel('Bucket 域名:')
        oss_layout.addWidget(oss_bucket_label)
        self.oss_bucket_input = LineEdit()
        self.oss_bucket_input.setPlaceholderText('例如: https://your-bucket.oss-cn-hangzhou.aliyuncs.com')
        self.oss_bucket_input.textChanged.connect(self.save_oss_bucket)
        oss_layout.addWidget(self.oss_bucket_input)

        layout.addWidget(oss_card)

        # 数据管理卡片
        data_card = CardWidget()
        data_layout = QVBoxLayout(data_card)

        data_title = BodyLabel('数据管理')
        data_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        data_layout.addWidget(data_title)

        # 日志管理按钮行
        log_layout = QHBoxLayout()
        self.open_log_folder_btn = PushButton('打开日志文件夹')
        self.open_log_folder_btn.clicked.connect(self.open_log_folder)
        log_layout.addWidget(self.open_log_folder_btn)
        self.pack_logs_btn = PushButton('打包日志')
        self.pack_logs_btn.clicked.connect(self.pack_logs)
        log_layout.addWidget(self.pack_logs_btn)
        data_layout.addLayout(log_layout)

        # 数据库管理按钮行
        db_layout = QHBoxLayout()
        self.open_db_folder_btn = PushButton('打开数据库文件夹')
        self.open_db_folder_btn.clicked.connect(self.open_database_folder)
        db_layout.addWidget(self.open_db_folder_btn)
        self.clear_data_btn = PushButton('清空所有数据')
        self.clear_data_btn.clicked.connect(self.clear_all_data)
        db_layout.addWidget(self.clear_data_btn)
        data_layout.addLayout(db_layout)

        layout.addWidget(data_card)
        layout.addStretch()

    def load_settings(self):
        """加载设置"""
        api_key = db_manager.load_config('api_key', '')
        self.api_key_input.setText(api_key)

        # 加载视频保存路径
        video_path = db_manager.load_config('video_save_path', '')
        self.video_path_input.setText(video_path)

        # 加载模型选择
        analysis_model = db_manager.load_config('analysis_model', 'gemini-3-pro-preview')
        index = self.analysis_model_combo.findText(analysis_model)
        if index >= 0:
            self.analysis_model_combo.setCurrentIndex(index)

        image_model = db_manager.load_config('image_model', 'gemini-3-pro-image-preview')
        index = self.image_model_combo.findText(image_model)
        if index >= 0:
            self.image_model_combo.setCurrentIndex(index)

        # 加载OSS配置
        oss_bucket = db_manager.load_config('oss_bucket_domain', '')
        self.oss_bucket_input.setText(oss_bucket)

    def save_settings(self):
        """保存设置"""
        api_key = self.api_key_input.text().strip()
        db_manager.save_config('api_key', api_key, 'string', 'Sora API Key')
        
        video_path = self.video_path_input.text().strip()
        db_manager.save_config('video_save_path', video_path, 'string', '视频保存路径')
        
        InfoBar.success(
            title='成功',
            content='设置已保存',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def save_api_key(self):
        """实时保存API Key"""
        api_key = self.api_key_input.text().strip()
        db_manager.save_config('api_key', api_key, 'string', 'Sora API Key')

    def save_video_path(self):
        """实时保存视频保存路径"""
        video_path = self.video_path_input.text().strip()
        db_manager.save_config('video_save_path', video_path, 'string', '视频保存路径')

    def save_analysis_model(self, model_name):
        """保存分析模型选择"""
        db_manager.save_config('analysis_model', model_name, 'string', '分析模型（用于分析简介、分镜、人物分析、提示词生成）')

    def save_image_model(self, model_name):
        """保存生图模型选择"""
        db_manager.save_config('image_model', model_name, 'string', '生图模型（用于生成角色图片和场景图片）')

    def save_oss_bucket(self):
        """保存OSS Bucket域名"""
        oss_bucket = self.oss_bucket_input.text().strip()
        db_manager.save_config('oss_bucket_domain', oss_bucket, 'string', '阿里云OSS Bucket域名')

    def browse_video_path(self):
        """浏览选择视频保存路径"""
        try:
            current_path = self.video_path_input.text().strip()
            if not current_path:
                current_path = str(Path.home() / "Downloads" / "Sora2Videos")

            selected_path = QFileDialog.getExistingDirectory(
                self,
                "选择视频保存路径",
                current_path,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )

            if selected_path:
                self.video_path_input.setText(selected_path)
                db_manager.save_config('video_save_path', selected_path, 'string', '视频保存路径')

                InfoBar.success(
                    title='成功',
                    content=f'视频保存路径已设置为: {selected_path}',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'选择路径失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def copy_wechat_id(self, ev: QMouseEvent | None):
        """复制微信号到剪贴板"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(WECHAT_ID)

            InfoBar.success(
                title='复制成功',
                content='微信号已复制到剪贴板',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            print(f"复制微信号失败: {e}")

    def open_api_url(self, ev: QMouseEvent | None):
        """打开API代理网址"""
        try:
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            url = QUrl(DISPLAY_API_PROXY_URL)
            QDesktopServices.openUrl(url)
            
            InfoBar.success(
                title='成功',
                content='已在浏览器中打开 API 代理网址',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            print(f"打开网址失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'打开网址失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def open_log_folder(self):
        """打开日志文件夹"""
        try:
            log_dir = Path(db_manager.logs_dir)
            log_dir.mkdir(exist_ok=True)

            system = platform.system()
            if system == "Windows":
                os.startfile(str(log_dir))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(log_dir)])
            else:  # Linux
                subprocess.run(["xdg-open", str(log_dir)])

            current_log = db_manager.get_current_log_file()
            if current_log:
                log_name = Path(current_log).name
                InfoBar.success(
                    title='成功',
                    content=f'日志文件夹已打开，当前日志: {log_name}',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            else:
                InfoBar.success(
                    title='成功',
                    content='日志文件夹已打开',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'打开日志文件夹失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def pack_logs(self):
        """打包日志文件"""
        try:
            import zipfile
            import datetime

            log_dir = Path(db_manager.logs_dir)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"sora2_logs_{timestamp}.zip"
            zip_path = Path(db_manager.app_data_dir) / zip_name

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for log_file in log_dir.glob("*.log"):
                    zipf.write(log_file, log_file.name)
                for log_file in log_dir.glob("*.log.zip"):
                    zipf.write(log_file, log_file.name)
                db_file = Path(db_manager.db_path)
                if db_file.exists():
                    zipf.write(db_file, "sora2.db")

            system = platform.system()
            if system == "Windows":
                os.startfile(str(Path(db_manager.app_data_dir)))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(Path(db_manager.app_data_dir))])
            else:  # Linux
                subprocess.run(["xdg-open", str(Path(db_manager.app_data_dir))])

            log_count = len(list(log_dir.glob("*.log"))) + len(list(log_dir.glob("*.log.zip")))
            InfoBar.success(
                title='成功',
                content=f'日志已打包为 {zip_name}（包含{log_count}个日志文件）',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'打包日志失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def open_database_folder(self):
        """打开数据库文件夹"""
        try:
            db_path = Path(db_manager.db_path)

            if not db_path.exists():
                InfoBar.warning(
                    title='提示',
                    content='数据库文件不存在',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", "/select,", str(db_path)])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", str(db_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(db_path.parent)])

            InfoBar.success(
                title='成功',
                content='数据库文件夹已打开',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'打开数据库文件夹失败: {str(e)}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def clear_all_data(self):
        """清空所有数据"""
        from qfluentwidgets import MessageBox
        dialog = MessageBox(
            title='确认清空',
            content='这将清空所有任务记录和设置。此操作不可恢复！\n\n确定要继续吗？',
            parent=self
        )
        dialog.yesButton.setText('确定清空')
        dialog.cancelButton.setText('取消')

        if dialog.exec():
            try:
                db_manager.clear_tasks()
                import sqlite3
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM config')
                conn.commit()
                conn.close()

                db_manager.create_config_table()

                InfoBar.success(
                    title='成功',
                    content='所有数据已清空',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                
                # 重新加载设置
                self.load_settings()
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'清空数据失败: {str(e)}',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
