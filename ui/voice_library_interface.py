"""
音色库界面
"""

import os
import sqlite3
import shutil
from pathlib import Path
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
from qfluentwidgets import (
    TitleLabel, BodyLabel, PrimaryPushButton, PushButton, CardWidget, 
    InfoBar, InfoBarPosition
)
from database_manager import db_manager
from loguru import logger


class VoiceLibraryInterface(QWidget):
    """音色库界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("voiceLibraryInterface")
        self.media_player = QMediaPlayer(self)
        self.current_playing_id = None
        self.init_ui()
        self.load_voices()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题和导入按钮（水平布局）
        header_layout = QHBoxLayout()
        title = TitleLabel("音色库")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 导入按钮（右上角）
        self.import_btn = PrimaryPushButton("导入")
        self.import_btn.clicked.connect(self.import_voice)
        header_layout.addWidget(self.import_btn)
        
        layout.addLayout(header_layout)
        
        # 音色列表表格
        self.voice_table = QTableWidget()
        self.voice_table.setColumnCount(5)
        self.voice_table.setHorizontalHeaderLabels(['序号', '名称', '文件路径', '操作', ''])
        # 隐藏垂直表头（行号），避免显示两个序号
        self.voice_table.verticalHeader().setVisible(False)
        self.voice_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 序号列自适应
        self.voice_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 名称列拉伸
        self.voice_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # 文件路径列拉伸
        self.voice_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 操作列自适应
        self.voice_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 删除列自适应
        self.voice_table.setAlternatingRowColors(True)
        self.voice_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.voice_table)
        
        # 连接媒体播放器信号
        self.media_player.stateChanged.connect(self.on_player_state_changed)
    
    def import_voice(self):
        """导入音色文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音色文件",
            str(Path.home()),
            "音频文件 (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.wma)"
        )
        
        if not file_paths:
            return
        
        # 创建音色文件存储目录
        voice_dir = Path(db_manager.app_data_dir) / "voice_library"
        voice_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        for file_path in file_paths:
            try:
                # 获取下一个序号
                next_sequence = self.get_next_sequence_number()
                
                # 复制文件到音色库目录
                source_path = Path(file_path)
                file_name = source_path.name
                dest_path = voice_dir / file_name
                
                # 如果文件已存在，添加序号后缀
                counter = 1
                while dest_path.exists():
                    stem = source_path.stem
                    suffix = source_path.suffix
                    dest_path = voice_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                shutil.copy2(source_path, dest_path)
                
                # 获取文件大小
                file_size = os.path.getsize(dest_path)
                
                # 保存到数据库
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO voice_library (sequence_number, name, file_path, file_size)
                    VALUES (?, ?, ?, ?)
                ''', (next_sequence, source_path.stem, str(dest_path), file_size))
                conn.commit()
                conn.close()
                
                success_count += 1
                logger.info(f"导入音色成功: {file_name} -> {dest_path}")
                
            except Exception as e:
                logger.error(f"导入音色失败 {file_path}: {e}")
                InfoBar.error(
                    title='导入失败',
                    content=f'导入 {Path(file_path).name} 失败: {str(e)}',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        
        if success_count > 0:
            InfoBar.success(
                title='导入成功',
                content=f'成功导入 {success_count} 个音色文件',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            # 重新加载列表
            self.load_voices()
    
    def get_next_sequence_number(self):
        """获取下一个序号"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(sequence_number) FROM voice_library')
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return result[0] + 1
            else:
                return 1
        except Exception as e:
            logger.error(f"获取下一个序号失败: {e}")
            return 1
    
    def load_voices(self):
        """加载音色列表"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, sequence_number, name, file_path
                FROM voice_library
                ORDER BY sequence_number ASC
            ''')
            voices = cursor.fetchall()
            conn.close()
            
            # 清空表格
            self.voice_table.setRowCount(0)
            
            # 填充表格
            for voice in voices:
                voice_id, sequence, name, file_path = voice
                row = self.voice_table.rowCount()
                self.voice_table.insertRow(row)
                
                # 序号
                sequence_item = QTableWidgetItem(str(sequence))
                sequence_item.setTextAlignment(Qt.AlignCenter)
                self.voice_table.setItem(row, 0, sequence_item)
                
                # 名称
                name_item = QTableWidgetItem(name)
                self.voice_table.setItem(row, 1, name_item)
                
                # 文件路径
                path_item = QTableWidgetItem(file_path)
                path_item.setToolTip(file_path)
                self.voice_table.setItem(row, 2, path_item)
                
                # 播放按钮
                play_btn = PushButton("播放" if self.current_playing_id != voice_id else "停止")
                play_btn.clicked.connect(lambda checked, vid=voice_id, fp=file_path: self.toggle_play(vid, fp))
                self.voice_table.setCellWidget(row, 3, play_btn)
                
                # 删除按钮
                delete_btn = PushButton("删除")
                delete_btn.setStyleSheet("color: red;")
                delete_btn.clicked.connect(lambda checked, vid=voice_id, fp=file_path: self.delete_voice(vid, fp))
                self.voice_table.setCellWidget(row, 4, delete_btn)
                
        except Exception as e:
            logger.error(f"加载音色列表失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'加载音色列表失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def toggle_play(self, voice_id, file_path):
        """切换播放/停止"""
        if self.current_playing_id == voice_id and self.media_player.state() == QMediaPlayer.PlayingState:
            # 停止播放
            self.media_player.stop()
            self.current_playing_id = None
        else:
            # 开始播放
            if self.current_playing_id is not None:
                # 停止当前播放
                self.media_player.stop()
            
            # 播放新文件
            if Path(file_path).exists():
                url = QUrl.fromLocalFile(file_path)
                content = QMediaContent(url)
                self.media_player.setMedia(content)
                self.media_player.play()
                self.current_playing_id = voice_id
            else:
                InfoBar.warning(
                    title='文件不存在',
                    content=f'音色文件不存在: {file_path}',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        
        # 更新按钮文本
        self.load_voices()
    
    def on_player_state_changed(self, state):
        """播放器状态改变"""
        # 更新按钮文本
        if state == QMediaPlayer.StoppedState:
            self.current_playing_id = None
            self.load_voices()
    
    def delete_voice(self, voice_id, file_path):
        """删除音色"""
        try:
            # 如果正在播放，先停止
            if self.current_playing_id == voice_id:
                self.media_player.stop()
                self.current_playing_id = None
            
            # 删除文件
            if Path(file_path).exists():
                os.remove(file_path)
            
            # 获取当前序号
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT sequence_number FROM voice_library WHERE id = ?', (voice_id,))
            result = cursor.fetchone()
            deleted_sequence = result[0] if result else None
            
            # 从数据库删除
            cursor.execute('DELETE FROM voice_library WHERE id = ?', (voice_id,))
            
            # 重新排序序号（删除后，后面的序号都要减1）
            if deleted_sequence:
                cursor.execute('''
                    UPDATE voice_library
                    SET sequence_number = sequence_number - 1
                    WHERE sequence_number > ?
                ''', (deleted_sequence,))
            
            conn.commit()
            conn.close()
            
            InfoBar.success(
                title='删除成功',
                content='音色已删除',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            
            # 重新加载列表
            self.load_voices()
            
        except Exception as e:
            logger.error(f"删除音色失败: {e}")
            InfoBar.error(
                title='删除失败',
                content=f'删除音色失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
