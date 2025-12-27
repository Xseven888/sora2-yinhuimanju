"""
角色详情对话框
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import (
    TitleLabel, PushButton, PrimaryPushButton, BodyLabel, TextEdit, InfoBar, InfoBarPosition
)
from database_manager import db_manager
from pathlib import Path
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog
import sqlite3
from loguru import logger
from threads.character_image_generation_thread import CharacterImageGenerationThread
from threads.sora_character_upload_thread import SoraCharacterUploadThread
from components.voice_selection_dialog import VoiceSelectionDialog
from components.upload_sora_character_dialog import UploadSoraCharacterDialog


class CharacterDetailDialog(QDialog):
    """角色详情对话框"""
    
    def __init__(self, character_id, project_id, parent=None):
        super().__init__(parent)
        self.character_id = character_id
        self.project_id = project_id
        self.setWindowTitle("角色详情")
        self.setModal(True)
        self.resize(800, 600)
        self.generation_thread = None
        self.upload_thread = None
        self.init_ui()
        self.load_character_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)  # 上边距从30改为20，让元素往上移
        layout.setSpacing(15)  # 间距从20改为15，让元素更紧凑
        
        # 角色名字（左上角顶部）
        self.character_name_label = TitleLabel("")
        layout.addWidget(self.character_name_label)
        
        # Sora状态
        self.sora_status_label = BodyLabel("Sora状态: 未上传")
        self.sora_status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.sora_status_label)
        
        # 绑定音色状态
        self.voice_status_label = BodyLabel("绑定音色: 未绑定")
        self.voice_status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.voice_status_label)
        
        # 角色图片（16:9横屏形式）
        image_container = QHBoxLayout()
        # 16:9比例：高度350，宽度 = 350 * 16 / 9 ≈ 622
        # 直接使用QLabel来显示图片，避免ImageWidget的固定尺寸限制
        self.character_image_label = QLabel()
        self.character_image_label.setFixedSize(622, 350)  # 16:9比例
        self.character_image_label.setAlignment(Qt.AlignCenter)
        self.character_image_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                color: #999;
            }
        """)
        self.character_image_label.setText("无图片")
        image_container.addWidget(self.character_image_label)
        image_container.addStretch()
        layout.addLayout(image_container)
        
        # 描述
        desc_label = BodyLabel("描述:")
        layout.addWidget(desc_label)
        
        self.description_text = TextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMinimumHeight(200)  # 从最大高度150改为最小高度200，让框更高
        layout.addWidget(self.description_text)
        
        layout.addStretch()
        
        # 底部按钮区域（同一行）
        button_layout = QHBoxLayout()
        
        # 左下角：绑定音色按钮
        self.bind_voice_btn = PushButton("绑定音色")
        self.bind_voice_btn.clicked.connect(self.on_bind_voice)
        button_layout.addWidget(self.bind_voice_btn)
        
        button_layout.addStretch()
        
        # 右下角：其他按钮
        self.generate_image_btn = PrimaryPushButton("生成角色图")
        self.generate_image_btn.clicked.connect(self.on_generate_character_image)
        button_layout.addWidget(self.generate_image_btn)
        
        self.upload_sora_btn = PushButton("上传Sora2角色")
        self.upload_sora_btn.clicked.connect(self.on_upload_sora_character)
        button_layout.addWidget(self.upload_sora_btn)
        
        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
    def load_character_data(self):
        """加载角色数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, description, front_image, side_image, back_image, 
                       id_card_image, sora_character_id, sora_character_username, sora_status, voice_id
                FROM characters
                WHERE id = ?
            ''', (self.character_id,))
            character = cursor.fetchone()
            
            if character:
                # 更新界面
                self.character_name_label.setText(character[0] or "未命名角色")
                
                # 描述
                description = character[1] or ""
                self.description_text.setPlainText(description)
                
                # 角色图片（优先使用正面图）
                front_image = character[2] or ""
                if front_image:
                    self.load_character_image(front_image)
                
                # Sora状态
                sora_status = character[8] or "未上传"
                sora_username = character[7] or ""
                if sora_status == "已上传" and sora_username:
                    # 在用户名前添加@符号
                    display_username = f"@{sora_username}" if not sora_username.startswith("@") else sora_username
                    self.sora_status_label.setText(f"Sora状态: 已上传 ({display_username})")
                    self.sora_status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
                else:
                    self.sora_status_label.setText("Sora状态: 未上传")
                    self.sora_status_label.setStyleSheet("color: #666; font-size: 12px;")
                
                # 绑定音色状态
                voice_id = character[9] if len(character) > 9 else None
                if voice_id:
                    # 获取音色名称（使用同一个连接）
                    cursor.execute('''
                        SELECT name, sequence_number
                        FROM voice_library
                        WHERE id = ?
                    ''', (voice_id,))
                    voice_result = cursor.fetchone()
                    if voice_result:
                        voice_name, voice_sequence = voice_result
                        self.voice_status_label.setText(f"绑定音色: {voice_sequence}. {voice_name}")
                        self.voice_status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
                    else:
                        self.voice_status_label.setText("绑定音色: 未绑定（音色已删除）")
                        self.voice_status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
                else:
                    self.voice_status_label.setText("绑定音色: 未绑定")
                    self.voice_status_label.setStyleSheet("color: #666; font-size: 12px;")
            
            # 在所有操作完成后再关闭连接
            conn.close()
                    
        except Exception as e:
            logger.error(f"加载角色数据失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'加载角色数据失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
    def on_generate_character_image(self):
        """生成角色图"""
        # 检查API Key
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            InfoBar.warning(
                title='提示',
                content='请先在设置中配置API Key',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 检查是否已有生成任务在运行
        if self.generation_thread and self.generation_thread.isRunning():
            InfoBar.warning(
                title='提示',
                content='已有生成任务正在进行中，请稍候...',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 禁用按钮
        self.generate_image_btn.setEnabled(False)
        self.generate_image_btn.setText("生成中...")
        
        # 显示开始提示
        InfoBar.info(
            title='开始生成',
            content='正在生成角色图片，请稍候...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
        # 创建并启动生成线程
        self.generation_thread = CharacterImageGenerationThread(
            self.character_id,
            self.project_id,
            self
        )
        self.generation_thread.progress.connect(self.on_generation_progress)
        self.generation_thread.finished.connect(self.on_generation_finished)
        self.generation_thread.error.connect(self.on_generation_error)
        self.generation_thread.start()
    
    def on_generation_progress(self, message: str):
        """生成进度回调"""
        # 检查对话框是否还存在
        try:
            if self.isVisible():
                logger.info(f"生成进度: {message}")
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
    
    def on_generation_finished(self, image_path: str):
        """生成完成回调"""
        # 检查对话框是否还存在
        try:
            if not self.isVisible():
                return
        except RuntimeError:
            # 对话框已关闭，忽略
            return
        
        # 恢复按钮
        try:
            self.generate_image_btn.setEnabled(True)
            self.generate_image_btn.setText("生成角色图")
            
            # 显示成功提示
            InfoBar.success(
                title='生成成功',
                content='角色图片已生成',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 重新加载角色数据以显示新图片
            self.load_character_data()
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
    
    def on_generation_error(self, error_message: str):
        """生成错误回调"""
        # 检查对话框是否还存在
        try:
            if not self.isVisible():
                return
        except RuntimeError:
            # 对话框已关闭，忽略
            return
        
        # 恢复按钮
        try:
            self.generate_image_btn.setEnabled(True)
            self.generate_image_btn.setText("生成角色图")
            
            # 显示错误提示
            InfoBar.error(
                title='生成失败',
                content=error_message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
        
    def load_character_image(self, image_path):
        """加载角色图片"""
        if not image_path:
            self.character_image_label.setText("无图片")
            return
            
        file_path = Path(image_path)
        if file_path.exists() and file_path.is_file():
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                # 缩放图片以适应16:9的尺寸，保持宽高比
                scaled_pixmap = pixmap.scaled(622, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.character_image_label.setPixmap(scaled_pixmap)
                self.character_image_label.setText("")
            else:
                self.character_image_label.setText("无图片")
        else:
            self.character_image_label.setText("无图片")
            
    def on_upload_sora_character(self):
        """上传Sora2角色"""
        # 检查API Key
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            InfoBar.warning(
                title='提示',
                content='请先在设置中配置API Key',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 检查OSS配置
        oss_bucket = db_manager.load_config('oss_bucket_domain', '')
        if not oss_bucket:
            InfoBar.warning(
                title='提示',
                content='请先在设置中配置OSS Bucket域名',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 检查角色图片和音色
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT front_image, voice_id FROM characters WHERE id = ?', (self.character_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                raise RuntimeError("无法获取角色信息")
            
            image_path = result[0]
            voice_id = result[1]
            
            if not image_path or not Path(image_path).exists():
                InfoBar.warning(
                    title='提示',
                    content='请先生成角色图片',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            
            if not voice_id:
                InfoBar.warning(
                    title='提示',
                    content='请先绑定音色',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
                
        except Exception as e:
            logger.error(f"检查角色信息失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'检查角色信息失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        # 检查是否已有上传任务在运行
        if self.upload_thread and self.upload_thread.isRunning():
            InfoBar.warning(
                title='提示',
                content='已有上传任务正在进行中，请稍候...',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        # 禁用按钮
        self.upload_sora_btn.setEnabled(False)
        self.upload_sora_btn.setText("上传中...")
        
        # 显示开始提示
        InfoBar.info(
            title='开始上传',
            content='正在合并视频并上传Sora2角色，请稍候...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
        # 创建并启动上传线程（自动合并视频，默认时间戳1,3）
        self.upload_thread = SoraCharacterUploadThread(
            self.character_id,
            timestamps="1,3",  # 默认1-3秒
            parent=self
        )
        self.upload_thread.progress.connect(self.on_upload_progress)
        self.upload_thread.finished.connect(self.on_upload_finished)
        self.upload_thread.error.connect(self.on_upload_error)
        self.upload_thread.start()
    
    def on_upload_progress(self, message: str):
        """上传进度回调"""
        # 检查对话框是否还存在
        try:
            if self.isVisible():
                logger.info(f"上传进度: {message}")
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
    
    def on_upload_finished(self, character_info: dict):
        """上传完成回调"""
        # 检查对话框是否还存在
        try:
            if not self.isVisible():
                return
        except RuntimeError:
            # 对话框已关闭，忽略
            return
        
        # 恢复按钮
        try:
            self.upload_sora_btn.setEnabled(True)
            self.upload_sora_btn.setText("上传Sora2角色")
            
            # 显示成功提示
            username = character_info.get("username", "")
            # 在用户名前添加@符号
            display_username = f"@{username}" if username and not username.startswith("@") else username
            InfoBar.success(
                title='上传成功',
                content=f'Sora2角色已创建: {display_username}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 重新加载角色数据以更新显示
            self.load_character_data()
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
    
    def on_upload_error(self, error_message: str):
        """上传错误回调"""
        # 检查对话框是否还存在
        try:
            if not self.isVisible():
                return
        except RuntimeError:
            # 对话框已关闭，忽略
            return
        
        # 恢复按钮
        try:
            self.upload_sora_btn.setEnabled(True)
            self.upload_sora_btn.setText("上传Sora2角色")
            
            # 显示错误提示
            InfoBar.error(
                title='上传失败',
                content=error_message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except RuntimeError:
            # 对话框已关闭，忽略
            pass
    
    def on_bind_voice(self):
        """绑定音色"""
        try:
            # 获取当前绑定的音色ID
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT voice_id FROM characters WHERE id = ?', (self.character_id,))
            result = cursor.fetchone()
            current_voice_id = result[0] if result and result[0] else None
            conn.close()
            
            # 打开音色选择对话框
            dialog = VoiceSelectionDialog(current_voice_id, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_voice_id = dialog.selected_voice_id
                if selected_voice_id:
                    # 更新数据库
                    conn = sqlite3.connect(db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE characters
                        SET voice_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (selected_voice_id, self.character_id))
                    conn.commit()
                    conn.close()
                    
                    InfoBar.success(
                        title='绑定成功',
                        content='音色绑定成功',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    
                    # 重新加载角色数据以更新显示
                    self.load_character_data()
                else:
                    # 解绑音色
                    conn = sqlite3.connect(db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE characters
                        SET voice_id = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (self.character_id,))
                    conn.commit()
                    conn.close()
                    
                    InfoBar.success(
                        title='解绑成功',
                        content='音色已解绑',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    
                    # 重新加载角色数据以更新显示
                    self.load_character_data()
                    
        except Exception as e:
            logger.error(f"绑定音色失败: {e}")
            InfoBar.error(
                title='绑定失败',
                content=f'绑定音色失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def closeEvent(self, event):
        """对话框关闭事件"""
        # 停止生成线程
        if self.generation_thread and self.generation_thread.isRunning():
            # 先尝试请求停止（如果线程支持）
            if hasattr(self.generation_thread, 'requestInterruption'):
                self.generation_thread.requestInterruption()
            
            # 等待线程结束，最多等待3秒
            if not self.generation_thread.wait(3000):
                # 如果3秒后还没结束，强制终止
                logger.warning("生成线程未在3秒内结束，强制终止")
                self.generation_thread.terminate()
                self.generation_thread.wait(1000)  # 再等待1秒确保终止
        
        # 停止上传线程
        if self.upload_thread and self.upload_thread.isRunning():
            # 先尝试请求停止
            if hasattr(self.upload_thread, 'requestInterruption'):
                self.upload_thread.requestInterruption()
            
            # 等待线程结束，最多等待3秒
            if not self.upload_thread.wait(3000):
                logger.warning("上传线程未在3秒内结束，强制终止")
                self.upload_thread.terminate()
                self.upload_thread.wait(1000)
        
        # 断开信号连接，避免已销毁的对象接收信号
        if self.generation_thread:
            try:
                self.generation_thread.progress.disconnect()
                self.generation_thread.finished.disconnect()
                self.generation_thread.error.disconnect()
            except:
                pass
        
        if self.upload_thread:
            try:
                self.upload_thread.progress.disconnect()
                self.upload_thread.finished.disconnect()
                self.upload_thread.error.disconnect()
            except:
                pass
        
        super().closeEvent(event)
