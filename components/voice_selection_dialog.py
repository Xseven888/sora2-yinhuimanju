"""
音色选择对话框
"""

import sqlite3
from pathlib import Path
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from qfluentwidgets import (
    TitleLabel, BodyLabel, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition
)
from database_manager import db_manager
from loguru import logger


class VoiceSelectionDialog(QDialog):
    """音色选择对话框"""
    
    def __init__(self, current_voice_id=None, parent=None):
        super().__init__(parent)
        self.selected_voice_id = None
        self.current_voice_id = current_voice_id
        self.current_playing_id = None
        self.media_player = QMediaPlayer(self)
        self.setWindowTitle("选择音色")
        self.setModal(True)
        self.resize(600, 500)
        self.init_ui()
        self.load_voices()
        
        # 连接媒体播放器信号
        self.media_player.stateChanged.connect(self.on_player_state_changed)
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = TitleLabel("选择音色")
        layout.addWidget(title)
        
        # 提示信息
        hint = BodyLabel("请从下方列表中选择一个音色")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        
        # 音色列表表格
        self.voice_table = QTableWidget()
        self.voice_table.setColumnCount(4)
        self.voice_table.setHorizontalHeaderLabels(['序号', '名称', '播放', '操作'])
        self.voice_table.verticalHeader().setVisible(False)
        self.voice_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.voice_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.voice_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.voice_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.voice_table.setAlternatingRowColors(True)
        self.voice_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.voice_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = PrimaryPushButton("确定")
        confirm_btn.clicked.connect(self.on_confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def update_play_button(self, voice_id):
        """更新指定音色的播放按钮状态"""
        for row in range(self.voice_table.rowCount()):
            item = self.voice_table.item(row, 0)
            if item:
                voice_id_from_item = item.data(Qt.UserRole)
                if voice_id_from_item == voice_id:
                    # 更新播放按钮
                    play_btn = self.voice_table.cellWidget(row, 2)
                    if play_btn:
                        if self.current_playing_id == voice_id and self.media_player.state() == QMediaPlayer.PlayingState:
                            play_btn.setText("停止")
                        else:
                            play_btn.setText("播放")
                    break
    
    def closeEvent(self, event):
        """对话框关闭事件"""
        # 停止播放
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.stop()
        super().closeEvent(event)
    
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
                sequence_item.setData(Qt.UserRole, voice_id)  # 存储voice_id
                self.voice_table.setItem(row, 0, sequence_item)
                
                # 名称
                name_item = QTableWidgetItem(name)
                self.voice_table.setItem(row, 1, name_item)
                
                # 播放按钮
                play_btn = PushButton("播放" if self.current_playing_id != voice_id else "停止")
                play_btn.clicked.connect(lambda checked, vid=voice_id, fp=file_path: self.toggle_play(vid, fp))
                self.voice_table.setCellWidget(row, 2, play_btn)
                
                # 选择按钮
                select_btn = PrimaryPushButton("选择" if self.current_voice_id != voice_id else "已绑定")
                if self.current_voice_id == voice_id:
                    select_btn.setEnabled(False)
                # 使用functools.partial或者直接传递voice_id
                select_btn.clicked.connect(lambda checked, vid=voice_id: self.select_voice(vid))
                self.voice_table.setCellWidget(row, 3, select_btn)
                
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
        # 保存当前滚动位置
        scrollbar = self.voice_table.verticalScrollBar()
        scroll_position = scrollbar.value()
        
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
        
        # 更新按钮文本（只更新当前行，不重新加载整个表格）
        self.update_play_button(voice_id)
        
        # 恢复滚动位置
        scrollbar.setValue(scroll_position)
    
    def on_player_state_changed(self, state):
        """播放器状态改变"""
        # 保存当前滚动位置
        scrollbar = self.voice_table.verticalScrollBar()
        scroll_position = scrollbar.value()
        
        # 更新按钮文本
        if state == QMediaPlayer.StoppedState:
            if self.current_playing_id:
                # 只更新之前播放的行
                self.update_play_button(self.current_playing_id)
            self.current_playing_id = None
        
        # 恢复滚动位置
        scrollbar.setValue(scroll_position)
    
    def select_voice(self, voice_id):
        """选择音色"""
        self.selected_voice_id = voice_id
        # 更新按钮状态
        for row in range(self.voice_table.rowCount()):
            btn = self.voice_table.cellWidget(row, 3)  # 选择按钮在第4列（索引3）
            if btn:
                # 从序号列获取voice_id
                item = self.voice_table.item(row, 0)
                if item:
                    voice_id_from_item = item.data(Qt.UserRole)
                    
                    if voice_id_from_item == voice_id:
                        btn.setText("已选择")
                        btn.setEnabled(False)
                    elif voice_id_from_item == self.current_voice_id:
                        btn.setText("已绑定")
                        btn.setEnabled(False)
                    else:
                        btn.setText("选择")
                        btn.setEnabled(True)
    
    def on_confirm(self):
        """确认选择"""
        if self.selected_voice_id is None:
            InfoBar.warning(
                title='提示',
                content='请先选择一个音色',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        self.accept()

