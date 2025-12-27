"""
剧集编辑页面：展示单集分镜列表，并支持
- AI编剧
- 一键场景图（为所有分镜生成纯场景图）
- 单行生成场景图

本文件是根据之前的实现描述重新整理创建的，保留了原有的核心功能与布局。
"""

import os
import sqlite3
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, QUrl
from PyQt5.QtGui import QPixmap, QWheelEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QDialog,
)

from qfluentwidgets import (
    BodyLabel,
    PrimaryPushButton,
    PushButton,
    InfoBar,
    InfoBarPosition,
)

from database_manager import db_manager
from threads.ai_script_thread import AIScriptThread
from threads.scene_image_generation_thread import SceneImageGenerationThread


class EpisodeDetailWidget(QWidget):
    """剧集编辑详情页"""

    # 注意：第一个参数是 episode_id，第二个参数是 project_id
    # 这样与 MainWindow.add_episode_detail_page 中的调用顺序保持一致
    def __init__(self, episode_id: int, project_id: int, main_window=None, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.episode_id = episode_id
        self.main_window = main_window

        self.episode_data = None
        self.project_data = None

        self.ai_script_thread: QThread | None = None
        self.scene_generation_threads = []
        # 行选中指示条（左侧蓝色条）
        self._row_indicator_bars: dict[int, QLabel] = {}

        self._init_ui()
        self.load_data()

    # ---------------- UI ----------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 头部：标题 + 按钮
        header_widget = QWidget(self)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.title_label = BodyLabel("项目标题-第X集", self)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.ai_script_btn = PrimaryPushButton("AI编剧", self)
        self.ai_script_btn.clicked.connect(self.on_ai_script)
        header_layout.addWidget(self.ai_script_btn)

        self.generate_scene_btn = PushButton("一键场景图", self)
        self.generate_scene_btn.clicked.connect(self.on_generate_scene_batch)
        header_layout.addWidget(self.generate_scene_btn)

        self.generate_prompt_btn = PushButton("生成视频提示词", self)
        self.generate_prompt_btn.clicked.connect(self.on_generate_prompt)
        header_layout.addWidget(self.generate_prompt_btn)

        self.generate_video_btn = PushButton("生成视频", self)
        self.generate_video_btn.clicked.connect(self.on_generate_video)
        header_layout.addWidget(self.generate_video_btn)
        
        self.refresh_status_btn = PushButton("刷新状态", self)
        self.refresh_status_btn.clicked.connect(self.on_refresh_video_status)
        header_layout.addWidget(self.refresh_status_btn)

        self.clear_prompt_btn = PushButton("清除提示词", self)
        self.clear_prompt_btn.clicked.connect(self.on_clear_prompt)
        header_layout.addWidget(self.clear_prompt_btn)

        self.clear_details_btn = PushButton("清除分镜详情", self)
        self.clear_details_btn.clicked.connect(self.on_clear_details)
        header_layout.addWidget(self.clear_details_btn)

        self.export_btn = PushButton("导出", self)
        self.export_btn.clicked.connect(self.on_export_videos)
        header_layout.addWidget(self.export_btn)

        layout.addWidget(header_widget)

        # 分镜表格
        self.storyboards_table = QTableWidget(self)
        self.storyboards_table.setColumnCount(5)
        self.storyboards_table.setHorizontalHeaderLabels(
            ["分镜序号", "分镜详情", "场景图", "分镜提示词", "视频"]
        )
        header = self.storyboards_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        # 设置视频列宽度为300px（约为原来的两倍）
        self.storyboards_table.setColumnWidth(4, 300)

        self.storyboards_table.verticalHeader().setVisible(False)
        self.storyboards_table.setAlternatingRowColors(True)
        self.storyboards_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.storyboards_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.storyboards_table.setWordWrap(True)
        # 完全模仿侧边栏效果：左侧蓝色条 + 轻微灰色背景
        # 禁用默认选中背景，使用自定义样式
        self.storyboards_table.setStyleSheet(
            """
            QTableWidget {
                border: none;
                background-color: white;
            }
            QTableWidget::item {
                border: none;
                padding: 0px;
                color: #000000;
            }
            QTableWidget::item:selected {
                background-color: transparent;
                color: #000000;
            }
            """
        )
        # 存储每行的背景widget，用于选中时显示灰色背景
        self._row_background_widgets = {}
        # 监听当前行变化，用来更新左侧蓝色条和灰色背景
        self.storyboards_table.currentCellChanged.connect(
            self._on_current_cell_changed
        )
        # 监听双击事件，用于编辑分镜详情和提示词
        self.storyboards_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        # 存储行号到storyboard_id的映射
        self._row_to_storyboard_id = {}

        layout.addWidget(self.storyboards_table)

    # 让整个页面的滚轮事件优先交给表格处理（之前为解决滚动过快问题的逻辑保留）
    def wheelEvent(self, event: QWheelEvent):
        if self.storyboards_table is not None:
            self.storyboards_table.wheelEvent(event)
            event.accept()
        else:
            super().wheelEvent(event)

    def _on_current_cell_changed(self, currentRow, currentColumn, previousRow, previousColumn):
        """更新左侧蓝色指示条和灰色背景，完全模仿侧边栏效果"""
        # 先全部置为透明（指示条）
        for row, bar in self._row_indicator_bars.items():
            if bar is not None:
                bar.setStyleSheet("background-color: transparent;")
        
        # 通过设置每行所有单元格的背景色来实现灰色背景（模仿侧边栏）
        from PyQt5.QtGui import QBrush, QColor
        gray_brush = QBrush(QColor("#F5F5F5"))
        transparent_brush = QBrush(Qt.transparent)
        default_text_color = QColor("#000000")  # 默认黑色文字
        
        # 先清除所有行的背景色，并恢复默认文字颜色
        for row in range(self.storyboards_table.rowCount()):
            for col in range(self.storyboards_table.columnCount()):
                item = self.storyboards_table.item(row, col)
                if item:
                    item.setBackground(transparent_brush)
                    # 恢复默认文字颜色，确保不会因为选中而变白
                    item.setForeground(default_text_color)
        
        # 当前行高亮：左侧蓝色条 + 轻微灰色背景（和侧边栏一样）
        if currentRow >= 0 and currentRow < self.storyboards_table.rowCount():
            # 设置左侧蓝色条
            if currentRow in self._row_indicator_bars:
                bar = self._row_indicator_bars[currentRow]
                if bar is not None:
                    bar.setStyleSheet("background-color: #0078D7;")
            
            # 为整行设置浅灰色背景（和侧边栏一样）
            from PyQt5.QtGui import QColor
            text_color = QColor("#000000")  # 黑色文字
            for col in range(self.storyboards_table.columnCount()):
                item = self.storyboards_table.item(currentRow, col)
                if item:
                    item.setBackground(gray_brush)
                    # 确保文字颜色是黑色，不会因为选中而变白
                    item.setForeground(text_color)
                else:
                    # 如果item不存在，创建一个（用于背景色）
                    item = QTableWidgetItem()
                    item.setBackground(gray_brush)
                    item.setForeground(text_color)
                    self.storyboards_table.setItem(currentRow, col, item)

    # ---------------- 数据加载 ----------------

    def load_data(self):
        """加载剧集和项目数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, episode_number, episode_name, file_path
                FROM episodes
                WHERE id = ?
                """,
                (self.episode_id,),
            )
            episode = cursor.fetchone()

            if not episode:
                conn.close()
                # 剧集不存在，显示错误提示并关闭页面
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title='提示',
                    content='该剧集数据已不存在，页面将自动关闭',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                # 延迟关闭页面，让用户看到提示
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, self._close_page)
                return

            cursor.execute(
                """
                SELECT id, title
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,),
            )
            project = cursor.fetchone()

            conn.close()

            if episode and project:
                self.episode_data = {
                    "id": episode[0],
                    "episode_number": episode[1],
                    "episode_name": episode[2],
                    "file_path": episode[3],
                }
                self.project_data = {
                    "id": project[0],
                    "title": project[1],
                }

                self.update_ui()
                self.load_storyboards()
            else:
                # 项目不存在
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title='提示',
                    content='该剧集或项目数据已不存在，页面将自动关闭',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(2000, self._close_page)
        except Exception as e:
            from loguru import logger
            logger.error(f"加载剧集数据失败: {e}")
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title='错误',
                content=f'加载剧集数据失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _close_page(self):
        """关闭当前页面（当数据不存在时）"""
        try:
            # 获取主窗口并移除当前页面
            main_window = self.window()
            if hasattr(main_window, 'remove_episode_detail_page'):
                main_window.remove_episode_detail_page(self.episode_id, delete_data=False)
            else:
                # 如果没有主窗口方法，直接关闭widget
                self.close()
        except Exception as e:
            from loguru import logger
            logger.error(f"关闭页面失败: {e}")

    def update_ui(self):
        if not self.episode_data or not self.project_data:
            return
        project_title = self.project_data.get("title", "未命名项目")
        episode_number = self.episode_data.get("episode_number", 0)
        self.title_label.setText(f"{project_title}-第{episode_number}集")

    def load_storyboards(self):
        """加载分镜到表格"""
        self.storyboards_table.setRowCount(0)
        self._row_indicator_bars.clear()
        self._row_background_widgets.clear()
        self._row_to_storyboard_id.clear()
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, sequence_number, title, screen_content,
                       sound_effect, dialogue, duration,
                       thumbnail_path, video_file, prompt, camera_movement,
                       video_url, video_task_id, video_status
                FROM storyboards
                WHERE episode_id = ?
                ORDER BY sequence_number ASC
                """,
                (self.episode_id,),
            )
            storyboards = cursor.fetchall()
            conn.close()
        except Exception as e:
            from loguru import logger

            logger.error(f"加载分镜列表失败: {e}")
            return

        for storyboard in storyboards:
            (
                storyboard_id,
                sequence_number,
                title,
                screen_content,
                sound_effect,
                dialogue,
                duration,
                thumbnail_path,
                video_file,
                prompt,
                camera_movement,
                video_url,
                video_task_id,
                video_status,
            ) = storyboard

            title = title or ""
            screen_content = screen_content or ""
            sound_effect = sound_effect or ""
            dialogue = dialogue or ""
            duration = duration or ""
            thumbnail_path = thumbnail_path or ""
            video_file = video_file or ""
            prompt = prompt or ""
            camera_movement = camera_movement or ""

            row = self.storyboards_table.rowCount()
            self.storyboards_table.insertRow(row)
            # 存储行号到storyboard_id的映射
            self._row_to_storyboard_id[row] = storyboard_id

            # 分镜序号列：左侧蓝色指示条 + 序号文本
            index_widget = QWidget(self)
            index_layout = QHBoxLayout(index_widget)
            index_layout.setContentsMargins(0, 0, 0, 0)
            index_layout.setSpacing(0)

            # 左侧指示条，默认透明，选中行时改成蓝色
            indicator_bar = QLabel(self)
            indicator_bar.setFixedWidth(4)
            indicator_bar.setStyleSheet("background-color: transparent;")

            index_label = BodyLabel(str(sequence_number), self)
            index_label.setAlignment(Qt.AlignCenter)
            index_label.setMinimumWidth(32)

            index_layout.addWidget(indicator_bar)
            index_layout.addWidget(index_label)
            index_layout.addStretch()

            self.storyboards_table.setCellWidget(row, 0, index_widget)
            self._row_indicator_bars[row] = indicator_bar

            # 分镜详情（标题、时长、对白、音效、画面内容、镜头移动）
            details_widget = QWidget(self)
            # 为widget添加双击事件处理
            details_widget.mouseDoubleClickEvent = lambda event, sid=storyboard_id, r=row: self.edit_storyboard_details(sid, r)
            details_layout = QVBoxLayout(details_widget)
            details_layout.setContentsMargins(10, 10, 10, 10)
            details_layout.setSpacing(6)

            if title:
                lbl = BodyLabel(f"【标题】{title}")
                lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
                details_layout.addWidget(lbl)

            if duration:
                lbl = BodyLabel(f"【时长】{duration}")
                lbl.setStyleSheet("color: #666; font-size: 12px;")
                details_layout.addWidget(lbl)

            if dialogue:
                lbl = BodyLabel(f"【文案/对白】{dialogue}")
                lbl.setWordWrap(True)
                lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                details_layout.addWidget(lbl)

            if sound_effect:
                lbl = BodyLabel(f"【音效】{sound_effect}")
                lbl.setWordWrap(True)
                lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                details_layout.addWidget(lbl)

            if screen_content:
                lbl = BodyLabel(f"【画面内容】{screen_content}")
                lbl.setWordWrap(True)
                lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                details_layout.addWidget(lbl)

            if camera_movement:
                lbl = BodyLabel(f"【镜头移动】{camera_movement}")
                lbl.setWordWrap(True)
                lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                details_layout.addWidget(lbl)

            details_layout.addStretch()
            self.storyboards_table.setCellWidget(row, 1, details_widget)

            # 动态计算行高，确保文字不被截断（简单实现）
            base_height = 140
            extra = (
                len(dialogue) // 30
                + len(sound_effect) // 30
                + len(screen_content) // 30
                + len(camera_movement) // 30
            )
            row_height = max(300, min(1000, base_height + extra * 24))
            self.storyboards_table.setRowHeight(row, row_height)

            # 场景图区域（16:9）
            scene_widget = QWidget(self)
            scene_layout = QVBoxLayout(scene_widget)
            scene_layout.setContentsMargins(10, 10, 10, 10)
            scene_layout.setSpacing(8)

            image_label = QLabel(self)
            available_height = max(200, row_height - 100)
            image_height = min(available_height, 400)
            image_width = int(image_height * 16 / 9)
            image_label.setFixedSize(image_width, image_height)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet(
                "background-color: #f5f5f5; border-radius: 4px; color: #999;"
            )

            if thumbnail_path and Path(thumbnail_path).exists():
                pix = QPixmap(thumbnail_path)
                if not pix.isNull():
                    scaled = pix.scaled(
                        image_width,
                        image_height,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    image_label.setPixmap(scaled)
                else:
                    image_label.setText("无图片")
            else:
                image_label.setText("无图片")

            scene_layout.addWidget(image_label)

            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(10)

            gen_btn = PushButton("生成场景图", self)
            gen_btn.setMinimumSize(110, 35)
            gen_btn.setMaximumSize(140, 35)
            gen_btn.clicked.connect(
                lambda _checked, sid=storyboard_id: self.on_generate_scene_single(sid)
            )
            btn_layout.addWidget(gen_btn)

            upload_btn = PushButton("上传", self)
            upload_btn.setMinimumSize(90, 35)
            upload_btn.setMaximumSize(120, 35)
            upload_btn.clicked.connect(
                lambda _checked, sid=storyboard_id: self.on_upload_scene(sid)
            )
            btn_layout.addWidget(upload_btn)

            download_btn = PushButton("下载", self)
            download_btn.setMinimumSize(90, 35)
            download_btn.setMaximumSize(120, 35)
            download_btn.clicked.connect(
                lambda _checked, sid=storyboard_id: self.on_download_scene(sid)
            )
            btn_layout.addWidget(download_btn)

            scene_layout.addLayout(btn_layout)
            scene_layout.addStretch()
            self.storyboards_table.setCellWidget(row, 2, scene_widget)

            # 分镜提示词（第4列，索引3）
            # 先删除旧的 item（如果存在）
            old_item = self.storyboards_table.item(row, 3)
            if old_item:
                self.storyboards_table.takeItem(row, 3)
            # 创建新的 item 并设置
            prompt_item = QTableWidgetItem(prompt or "无提示词")
            prompt_item.setToolTip(prompt or "无提示词")
            # 设置文本换行，确保长文本可以显示
            prompt_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            # 明确设置文字颜色为黑色，确保选中时不会变白
            from PyQt5.QtGui import QColor
            prompt_item.setForeground(QColor("#000000"))
            # 启用文本换行
            self.storyboards_table.setItem(row, 3, prompt_item)

            # 视频列（第5列，索引4）
            video_widget = QWidget()
            video_layout = QVBoxLayout(video_widget)
            video_layout.setContentsMargins(5, 5, 5, 5)
            video_layout.setSpacing(5)
            
            # 根据视频状态显示不同内容
            if video_url:
                # 已生成视频，显示状态和重新生成按钮
                status_label = BodyLabel("已生成")
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet("color: #4CAF50;")
                video_layout.addWidget(status_label)
                
                # 显示重新生成按钮
                regenerate_btn = PrimaryPushButton("重新生成")
                regenerate_btn.setMaximumSize(100, 30)
                regenerate_btn.clicked.connect(
                    lambda checked, sid=storyboard_id: self.on_generate_single_video(sid, regenerate=True)
                )
                video_layout.addWidget(regenerate_btn)
            elif video_task_id:
                # 有任务ID，检查状态
                if video_status == '生成失败':
                    # 生成失败，显示失败状态和重新生成按钮
                    status_label = BodyLabel("生成失败")
                    status_label.setAlignment(Qt.AlignCenter)
                    status_label.setStyleSheet("color: #D32F2F;")
                    video_layout.addWidget(status_label)
                    
                    # 显示生成视频按钮（重新生成）
                    generate_btn = PrimaryPushButton("生成视频")
                    generate_btn.setMaximumSize(100, 30)
                    generate_btn.clicked.connect(
                        lambda checked, sid=storyboard_id: self.on_generate_single_video(sid, regenerate=True)
                    )
                    video_layout.addWidget(generate_btn)
                else:
                    # 正在生成中或等待中
                    status_label = BodyLabel(video_status or "生成中")
                    status_label.setAlignment(Qt.AlignCenter)
                    status_label.setStyleSheet("color: #0078D7;")
                    video_layout.addWidget(status_label)
            else:
                # 未生成，显示生成按钮
                status_label = BodyLabel("未生成")
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet("color: #999;")
                video_layout.addWidget(status_label)
                
                # 检查是否有场景图和提示词
                # storyboard 元组结构: (id, sequence_number, title, screen_content, sound_effect, 
                #                      dialogue, duration, thumbnail_path, video_file, prompt, camera_movement,
                #                      video_url, video_task_id, video_status)
                thumbnail_path = storyboard[7] if len(storyboard) > 7 else None  # thumbnail_path 在索引7
                prompt = storyboard[9] if len(storyboard) > 9 else None  # prompt 在索引9
                
                if thumbnail_path and prompt:
                    # 有场景图和提示词，显示生成按钮
                    generate_btn = PrimaryPushButton("生成视频")
                    generate_btn.setMaximumSize(100, 30)
                    generate_btn.clicked.connect(
                        lambda checked, sid=storyboard_id: self.on_generate_single_video(sid)
                    )
                    video_layout.addWidget(generate_btn)
                else:
                    # 缺少场景图或提示词
                    hint_label = BodyLabel("缺少场景图\n或提示词")
                    hint_label.setAlignment(Qt.AlignCenter)
                    hint_label.setStyleSheet("color: #999; font-size: 11px;")
                    video_layout.addWidget(hint_label)
            
            self.storyboards_table.setCellWidget(row, 4, video_widget)

    # ---------------- AI 编剧 ----------------

    def on_ai_script(self):
        """AI编剧 - 调用模型生成分镜，并写入 storyboards 表"""
        if not self.episode_data:
            return
        if self.ai_script_thread and self.ai_script_thread.isRunning():
            InfoBar.info(
                title="提示",
                content="AI编剧正在执行中，请稍候",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        file_path = self.episode_data.get("file_path") or ""
        if not file_path or not os.path.exists(file_path):
            InfoBar.warning(
                title="提示",
                content="找不到剧集文件，无法执行AI编剧",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        self.ai_script_thread = AIScriptThread(self.episode_id, file_path, self)
        self.ai_script_thread.progress.connect(self.on_ai_script_progress)
        self.ai_script_thread.finished.connect(self.on_ai_script_finished)
        self.ai_script_thread.error.connect(self.on_ai_script_error)
        self.ai_script_thread.start()

    def on_ai_script_progress(self, message: str):
        InfoBar.info(
            title="AI编剧",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self,
        )

    def on_ai_script_finished(self, storyboards: list):
        """AI编剧完成后，把分镜写入 storyboards 表"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            for sb in storyboards:
                cursor.execute(
                    """
                    INSERT INTO storyboards
                    (episode_id, sequence_number, title, duration,
                     dialogue, screen_content, camera_movement)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.episode_id,
                        sb.get("sequence_number", 0),
                        sb.get("title", ""),
                        sb.get("duration", ""),
                        sb.get("dialogue", ""),
                        sb.get("screen_content", ""),
                        sb.get("camera_movement", ""),
                    ),
                )
            conn.commit()
            conn.close()

            self.load_storyboards()

            InfoBar.success(
                title="成功",
                content=f"已生成 {len(storyboards)} 个分镜",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            from loguru import logger

            logger.error(f"保存分镜数据失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"保存分镜数据失败: {e}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_ai_script_error(self, error_message: str):
        InfoBar.error(
            title="AI编剧失败",
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    # ---------------- 场景图生成 ----------------

    def on_generate_scene_batch(self):
        """一键场景图：为当前剧集所有有画面内容的分镜生成场景图"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, sequence_number, screen_content
                FROM storyboards
                WHERE episode_id = ?
                ORDER BY sequence_number ASC
                """,
                (self.episode_id,),
            )
            storyboards = cursor.fetchall()
            conn.close()

            if not storyboards:
                InfoBar.warning(
                    title="提示",
                    content="当前没有分镜数据，请先使用AI编剧生成分镜",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return

            self.scene_generation_threads = []
            valid_count = 0
            skipped = 0

            from loguru import logger

            for sid, seq, screen_content in storyboards:
                text = (screen_content or "").strip()
                if not text:
                    skipped += 1
                    logger.warning(f"分镜序号 {seq} (ID={sid}) 没有画面内容，跳过一键场景图")
                    continue

                thread = SceneImageGenerationThread(sid, self.project_id, self)
                thread.progress.connect(
                    lambda msg, storyboard_id=sid: self.on_scene_generation_progress(
                        storyboard_id, msg
                    )
                )
                thread.finished.connect(self.on_scene_generation_finished)
                thread.error.connect(self.on_scene_generation_error)
                self.scene_generation_threads.append(thread)
                thread.start()
                valid_count += 1

            if valid_count == 0:
                InfoBar.warning(
                    title="提示",
                    content="所有分镜都没有画面内容，无法生成场景图",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )
            else:
                msg = f"正在为 {valid_count} 个分镜生成场景图，请稍候…"
                if skipped:
                    msg += f"（已跳过 {skipped} 个无画面内容的分镜）"
                InfoBar.info(
                    title="提示",
                    content=msg,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"生成场景图失败: {e}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_generate_scene_single(self, storyboard_id: int):
        """单行生成场景图（行内按钮）"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT screen_content
                FROM storyboards
                WHERE id = ?
                """,
                (storyboard_id,),
            )
            result = cursor.fetchone()
            conn.close()

            if not result or not (result[0] or "").strip():
                InfoBar.warning(
                    title="提示",
                    content="当前分镜没有画面内容，无法生成场景图",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return

            thread = SceneImageGenerationThread(storyboard_id, self.project_id, self)
            thread.progress.connect(
                lambda msg, sid=storyboard_id: self.on_scene_generation_progress(
                    sid, msg
                )
            )
            thread.finished.connect(self.on_scene_generation_finished)
            thread.error.connect(self.on_scene_generation_error)
            thread.start()

            InfoBar.info(
                title="提示",
                content="正在生成场景图，请稍候…",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"生成场景图失败: {e}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_scene_generation_progress(self, storyboard_id: int, message: str):
        # 这里简单用日志；如需弹提示可按需打开
        from loguru import logger

        logger.info(f"分镜 {storyboard_id} 场景图生成进度: {message}")

    def on_scene_generation_finished(self, storyboard_id: int, image_path: str):
        """场景图生成完成后刷新表格"""
        from loguru import logger

        logger.info(f"分镜 {storyboard_id} 场景图生成完成: {image_path}")
        self.load_storyboards()
        InfoBar.success(
            title="成功",
            content="场景图生成完成",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self,
        )

    def on_scene_generation_error(self, storyboard_id: int, error_msg: str):
        InfoBar.error(
            title="错误",
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    # ---------------- 其他占位功能 ----------------

    def on_generate_prompt(self):
        """生成视频提示词：根据分镜详情和项目风格，为每个分镜生成用于 Sora2 的提示词"""
        try:
            # 1. 读取当前剧集的所有分镜数据
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, sequence_number, title, duration, dialogue, screen_content, camera_movement
                FROM storyboards
                WHERE episode_id = ?
                ORDER BY sequence_number ASC
                """,
                (self.episode_id,),
            )
            storyboards = cursor.fetchall()

            if not storyboards:
                conn.close()
                InfoBar.warning(
                    title="提示",
                    content="当前没有分镜数据，请先使用AI编剧生成分镜",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return

            # 2. 获取项目风格
            cursor.execute(
                """
                SELECT style
                FROM projects
                WHERE id = ?
                """,
                (self.project_id,),
            )
            project_row = cursor.fetchone()
            style = (project_row[0] or "").strip() if project_row else ""

            # 3. 获取已绑定 Sora2 角色用户名的角色映射 {角色名: @username}
            cursor.execute(
                """
                SELECT name, sora_character_username
                FROM characters
                WHERE project_id = ?
                  AND sora_character_username IS NOT NULL
                  AND sora_character_username != ''
                """,
                (self.project_id,),
            )
            name_to_sora = {}
            for name, sora_username in cursor.fetchall():
                if not name:
                    continue
                display = sora_username.strip()
                if not display:
                    continue
                if not display.startswith("@"):
                    display = "@" + display
                name_to_sora[name.strip()] = display
            
            # 调试日志：记录获取到的角色映射
            from loguru import logger
            if name_to_sora:
                logger.info(f"获取到 {len(name_to_sora)} 个角色的Sora用户名映射: {name_to_sora}")
            else:
                logger.warning(f"项目 {self.project_id} 没有找到已绑定Sora用户名的角色")

            # 4. 为每个分镜生成提示词并写回数据库的 prompt 字段
            updated_count = 0
            for (
                sid,
                seq,
                title,
                duration,
                dialogue,
                screen_content,
                camera_movement,
            ) in storyboards:
                prompt_text = self._build_video_prompt_for_storyboard(
                    sequence_number=seq,
                    title=title or "",
                    duration=duration or "",
                    dialogue=dialogue or "",
                    screen_content=screen_content or "",
                    camera_movement=camera_movement or "",
                    style=style,
                    name_to_sora=name_to_sora,
                )
                # 更新数据库
                cursor.execute(
                    "UPDATE storyboards SET prompt = ? WHERE id = ?",
                    (prompt_text, sid),
                )
                updated_count += 1

            # 提交事务
            conn.commit()
            
            # 验证更新是否成功（可选，用于调试）
            from loguru import logger
            logger.info(f"已更新 {updated_count} 个分镜的提示词")
            
            conn.close()

            # 5. 刷新界面中的"分镜提示词"列
            # 强制刷新表格，确保显示最新数据
            self.load_storyboards()
            # 强制刷新表格显示，确保更新后的内容可见
            self.storyboards_table.viewport().update()
            self.storyboards_table.repaint()

            InfoBar.success(
                title="成功",
                content=f"已为 {updated_count} 个分镜生成视频提示词",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
        except Exception as e:
            from loguru import logger

            logger.error(f"生成视频提示词失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"生成视频提示词失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def _build_video_prompt_for_storyboard(
        self,
        sequence_number: int,
        title: str,
        duration: str,
        dialogue: str,
        screen_content: str,
        camera_movement: str,
        style: str,
        name_to_sora: dict,
    ) -> str:
        """根据单个分镜信息构建用于 Sora2 的提示词"""
        # 替换所有字段中的角色名为 Sora2 角色用户名
        title_with_sora = self._replace_character_names_in_text(title, name_to_sora)
        dialogue_with_sora = self._replace_dialogue_character_names(
            dialogue, name_to_sora
        )
        screen_content_with_sora = self._replace_character_names_in_text(
            screen_content, name_to_sora
        )
        camera_movement_with_sora = self._replace_character_names_in_text(
            camera_movement, name_to_sora
        )

        parts = []
        if title_with_sora:
            parts.append(f"【镜头{sequence_number}】{title_with_sora}")
        else:
            parts.append(f"【镜头{sequence_number}】")

        if duration:
            parts.append(f"时长：{duration}")

        if screen_content_with_sora:
            if style:
                parts.append(f"画面内容：{screen_content_with_sora}；整体风格：{style}")
            else:
                parts.append(f"画面内容：{screen_content_with_sora}")
        elif style:
            parts.append(f"整体风格：{style}")

        if dialogue_with_sora:
            parts.append(f"角色对白与音效：{dialogue_with_sora}")

        if camera_movement_with_sora:
            parts.append(f"镜头运动：{camera_movement_with_sora}")

        # 合并成一段连续的中文提示词，便于直接作为 Sora2 的 prompt
        return "  ".join(parts)

    def _replace_character_names_in_text(self, text: str, name_to_sora: dict) -> str:
        """在普通文本中替换角色名为 Sora2 角色用户名（直接替换，不添加"说："）"""
        if not text or not name_to_sora:
            return text

        result = text
        # 按角色名长度从长到短排序，避免短名字被长名字包含的情况
        sorted_names = sorted(name_to_sora.items(), key=lambda x: len(x[0]), reverse=True)
        
        import re
        for name, sora_name in sorted_names:
            if not name:
                continue
            # 直接替换角色名（保持上下文，不改变语法结构）
            # 由于已经按长度从长到短排序，长名字会先匹配，所以短名字不会匹配到长名字中的部分
            # 使用简单的字符串替换即可，但要确保是完整匹配
            # 对于中文角色名，直接替换所有出现的完整角色名
            # 使用正则确保是完整匹配（不是其他词的一部分）
            escaped_name = re.escape(name)
            # 匹配规则：允许在中文上下文中匹配，但确保不是其他词的一部分
            # 方法：使用负向前后查找，但只检查是否是更长角色名的一部分
            # 由于已按长度排序，这里直接替换即可
            # 但为了安全，我们使用正则确保是完整匹配（前后可以是任何字符，包括中文）
            # 简单方式：直接替换，因为已经排序，不会出现部分匹配问题
            result = result.replace(name, sora_name)

        return result

    def _replace_dialogue_character_names(self, dialogue: str, name_to_sora: dict) -> str:
        """将对白中的角色名替换为绑定的 Sora2 角色用户名表达，例如：@xxx 说：\"...\""""
        if not dialogue or not name_to_sora:
            return dialogue

        text = dialogue
        # 简单基于"角色名+冒号"模式替换，支持 中文冒号/英文冒号
        # 按角色名长度从长到短排序，避免短名字被长名字包含的情况
        sorted_names = sorted(name_to_sora.items(), key=lambda x: len(x[0]), reverse=True)
        
        for name, sora_name in sorted_names:
            if not name:
                continue
            for colon in ("：", ":"):
                pattern = f"{name}{colon}"
                replacement = f"{sora_name} 说{colon}"
                if pattern in text:
                    text = text.replace(pattern, replacement)

        return text

    def on_generate_video(self):
        """生成视频：为所有有场景图和提示词的分镜创建视频任务"""
        try:
            # 获取所有分镜
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, thumbnail_path, prompt, video_status
                FROM storyboards
                WHERE episode_id = ?
                ORDER BY sequence_number ASC
            """, (self.episode_id,))
            storyboards = cursor.fetchall()
            conn.close()
            
            if not storyboards:
                InfoBar.warning(
                    title="提示",
                    content="当前剧集没有分镜数据",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 过滤出有场景图和提示词的分镜
            valid_storyboards = []
            skipped_count = 0
            for storyboard in storyboards:
                storyboard_id, thumbnail_path, prompt, video_status = storyboard
                if not thumbnail_path or not prompt:
                    skipped_count += 1
                    continue
                # 如果已经有视频或正在生成，跳过
                if video_status in ['已完成', '生成中']:
                    skipped_count += 1
                    continue
                valid_storyboards.append(storyboard_id)
            
            if not valid_storyboards:
                InfoBar.warning(
                    title="提示",
                    content=f"没有可生成视频的分镜（已跳过 {skipped_count} 个）",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 为每个分镜创建视频生成线程
            from threads.video_generation_sora2_thread import VideoGenerationSora2Thread
            from threads.video_status_check_thread import VideoStatusCheckThread
            
            self.video_threads = getattr(self, 'video_threads', {})
            self.status_threads = getattr(self, 'status_threads', {})
            
            created_count = 0
            for storyboard_id in valid_storyboards:
                # 创建视频生成线程
                video_thread = VideoGenerationSora2Thread(storyboard_id, self.project_id, self)
                video_thread.progress.connect(
                    lambda sid, msg, sbid=storyboard_id: self.on_video_progress(sbid, msg)
                )
                video_thread.finished.connect(
                    lambda sid, task_id, sbid=storyboard_id: self.on_video_finished(sbid, task_id)
                )
                video_thread.error.connect(
                    lambda sid, error, sbid=storyboard_id: self.on_video_error(sbid, error)
                )
                self.video_threads[storyboard_id] = video_thread
                video_thread.start()
                created_count += 1
            
            InfoBar.success(
                title="提示",
                content=f"已为 {created_count} 个分镜创建视频生成任务",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            
        except Exception as e:
            from loguru import logger
            logger.error(f"生成视频失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"生成视频失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
    
    def on_video_progress(self, storyboard_id, message):
        """视频生成进度回调"""
        from loguru import logger
        logger.info(f"分镜 {storyboard_id} 视频生成进度: {message}")
    
    def on_video_finished(self, storyboard_id, task_id):
        """视频生成任务创建完成回调"""
        from loguru import logger
        logger.info(f"分镜 {storyboard_id} 视频任务已创建: {task_id}")
        
        # 启动状态查询线程
        from threads.video_status_check_thread import VideoStatusCheckThread
        self.status_threads = getattr(self, 'status_threads', {})
        
        status_thread = VideoStatusCheckThread(storyboard_id, task_id, self)
        status_thread.status_updated.connect(
            lambda sid, status, url, sbid=storyboard_id: self.on_video_status_updated(sbid, status, url)
        )
        status_thread.error.connect(
            lambda sid, error, sbid=storyboard_id: self.on_video_status_error(sbid, error)
        )
        self.status_threads[storyboard_id] = status_thread
        status_thread.start()
        
        # 刷新表格显示
        self.load_storyboards()
    
    def on_video_error(self, storyboard_id, error_message):
        """视频生成错误回调"""
        from loguru import logger
        logger.error(f"分镜 {storyboard_id} 视频生成失败: {error_message}")
        
        InfoBar.error(
            title="错误",
            content=f"分镜 {storyboard_id} 视频生成失败: {error_message}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )
        
        # 更新数据库状态
        db_manager.update_storyboard_video_info(
            storyboard_id=storyboard_id,
            video_status='生成失败'
        )
        
        # 刷新表格显示
        self.load_storyboards()
    
    def on_video_status_updated(self, storyboard_id, status, video_url):
        """视频状态更新回调"""
        from loguru import logger
        logger.info(f"分镜 {storyboard_id} 视频状态更新: {status}, URL: {video_url}")
        
        # 刷新表格显示
        try:
            self.load_storyboards()
        except Exception as e:
            logger.error(f"刷新表格显示失败: {e}")
    
    def on_video_status_error(self, storyboard_id, error_message):
        """视频状态查询错误回调"""
        from loguru import logger
        logger.error(f"分镜 {storyboard_id} 视频状态查询失败: {error_message}")
        
        # 刷新表格显示
        try:
            self.load_storyboards()
        except Exception as e:
            logger.error(f"刷新表格显示失败: {e}")
    
    def on_export_videos(self):
        """导出所有已生成的视频，合并成一个视频"""
        try:
            from components.export_video_dialog import ExportVideoDialog
            
            # 检查是否有已生成的视频
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM storyboards
                WHERE episode_id = ? 
                  AND video_url IS NOT NULL 
                  AND video_url != ''
            """, (self.episode_id,))
            count = cursor.fetchone()[0]
            conn.close()
            
            if count == 0:
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.warning(
                    title="提示",
                    content="没有已生成的视频可以导出",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 打开导出对话框
            dialog = ExportVideoDialog(
                self.episode_id,
                self.episode_data,
                self.project_data,
                self
            )
            dialog.start_export()
            dialog.exec_()
            
        except Exception as e:
            from loguru import logger
            logger.error(f"导出视频异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="错误",
                content=f"导出视频失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self,
            )
    
    def on_item_double_clicked(self, item):
        """处理表格项双击事件"""
        try:
            row = item.row()
            col = item.column()
            
            # 获取storyboard_id
            storyboard_id = self._row_to_storyboard_id.get(row)
            if not storyboard_id:
                return
            
            # 分镜详情列（索引1）
            if col == 1:
                self.edit_storyboard_details(storyboard_id, row)
            # 分镜提示词列（索引3）
            elif col == 3:
                self.edit_storyboard_prompt(storyboard_id, row)
                
        except Exception as e:
            from loguru import logger
            logger.error(f"处理双击事件失败: {e}")
    
    def edit_storyboard_details(self, storyboard_id, row):
        """编辑分镜详情"""
        try:
            from components.edit_storyboard_dialog import EditStoryboardDetailsDialog
            from qfluentwidgets import InfoBar, InfoBarPosition
            from loguru import logger
            
            # 获取当前分镜数据
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, duration, dialogue, sound_effect, 
                       screen_content, camera_movement
                FROM storyboards
                WHERE id = ?
            """, (storyboard_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                InfoBar.warning(
                    title="提示",
                    content="无法获取分镜数据",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 构建数据字典
            storyboard_data = {
                'id': result[0],
                'title': result[1] or '',
                'duration': result[2] or '',
                'dialogue': result[3] or '',
                'sound_effect': result[4] or '',
                'screen_content': result[5] or '',
                'camera_movement': result[6] or '',
            }
            
            # 打开编辑对话框
            dialog = EditStoryboardDetailsDialog(storyboard_data, self)
            if dialog.exec_() == QDialog.Accepted:
                # 保存修改
                new_data = dialog.get_data()
                
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE storyboards
                    SET title = ?, duration = ?, dialogue = ?, 
                        sound_effect = ?, screen_content = ?, camera_movement = ?
                    WHERE id = ?
                """, (
                    new_data['title'] or None,
                    new_data['duration'] or None,
                    new_data['dialogue'] or None,
                    new_data['sound_effect'] or None,
                    new_data['screen_content'] or None,
                    new_data['camera_movement'] or None,
                    storyboard_id
                ))
                conn.commit()
                conn.close()
                
                # 刷新表格
                self.load_storyboards()
                
                InfoBar.success(
                    title="成功",
                    content="分镜详情已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                
        except Exception as e:
            from loguru import logger
            logger.error(f"编辑分镜详情失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="错误",
                content=f"编辑分镜详情失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
    
    def edit_storyboard_prompt(self, storyboard_id, row):
        """编辑分镜提示词"""
        try:
            from components.edit_storyboard_dialog import EditStoryboardPromptDialog
            from qfluentwidgets import InfoBar, InfoBarPosition
            from loguru import logger
            
            # 获取当前提示词
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT prompt
                FROM storyboards
                WHERE id = ?
            """, (storyboard_id,))
            result = cursor.fetchone()
            conn.close()
            
            current_prompt = result[0] if result and result[0] else ''
            
            # 打开编辑对话框
            dialog = EditStoryboardPromptDialog(current_prompt, self)
            if dialog.exec_() == QDialog.Accepted:
                # 保存修改
                new_prompt = dialog.get_prompt()
                
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE storyboards
                    SET prompt = ?
                    WHERE id = ?
                """, (new_prompt or None, storyboard_id))
                conn.commit()
                conn.close()
                
                # 刷新表格
                self.load_storyboards()
                
                InfoBar.success(
                    title="成功",
                    content="分镜提示词已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                
        except Exception as e:
            from loguru import logger
            logger.error(f"编辑分镜提示词失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title="错误",
                content=f"编辑分镜提示词失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
    
    def on_refresh_video_status(self):
        """手动刷新所有正在生成中的视频状态"""
        try:
            # 获取所有有video_task_id但状态为"生成中"或"等待中"的分镜
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, video_task_id
                FROM storyboards
                WHERE episode_id = ? 
                  AND video_task_id IS NOT NULL 
                  AND video_task_id != ''
                  AND (video_status = '生成中' OR video_status = '等待中' OR video_url IS NULL)
            """, (self.episode_id,))
            storyboards = cursor.fetchall()
            conn.close()
            
            if not storyboards:
                InfoBar.info(
                    title="提示",
                    content="没有需要刷新的视频任务",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 为每个分镜创建状态查询线程
            from threads.video_status_check_thread import VideoStatusCheckThread
            
            self.status_threads = getattr(self, 'status_threads', {})
            
            refreshed_count = 0
            for storyboard_id, video_task_id in storyboards:
                # 如果已有线程在运行，先停止它
                if storyboard_id in self.status_threads:
                    old_thread = self.status_threads[storyboard_id]
                    if old_thread.isRunning():
                        old_thread.stop()
                        old_thread.wait(1000)  # 等待1秒
                
                # 创建新的状态查询线程
                status_thread = VideoStatusCheckThread(storyboard_id, video_task_id, self)
                # 使用lambda但确保正确捕获storyboard_id（信号参数顺序：storyboard_id, status, video_url）
                status_thread.status_updated.connect(
                    lambda sid, status, url, sbid=storyboard_id: self.on_video_status_updated(sbid, status, url)
                )
                # 错误信号参数顺序：storyboard_id, error_message
                status_thread.error.connect(
                    lambda sid, error, sbid=storyboard_id: self.on_video_status_error(sbid, error)
                )
                self.status_threads[storyboard_id] = status_thread
                status_thread.start()
                refreshed_count += 1
            
            InfoBar.success(
                title="提示",
                content=f"已开始刷新 {refreshed_count} 个视频任务的状态",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            
        except Exception as e:
            from loguru import logger
            logger.error(f"刷新视频状态失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"刷新视频状态失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
    
    def on_generate_single_video(self, storyboard_id, regenerate=False):
        """为单个分镜生成视频
        
        Args:
            storyboard_id: 分镜ID
            regenerate: 是否重新生成（覆盖旧视频）
        """
        try:
            # 获取分镜信息
            storyboard_data = db_manager.get_storyboard_by_id(storyboard_id)
            if not storyboard_data:
                InfoBar.warning(
                    title="提示",
                    content="无法获取分镜信息",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 检查必要字段
            thumbnail_path = storyboard_data.get('thumbnail_path')
            prompt = storyboard_data.get('prompt')
            
            if not thumbnail_path:
                InfoBar.warning(
                    title="提示",
                    content="分镜没有场景图，无法生成视频",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            if not prompt:
                InfoBar.warning(
                    title="提示",
                    content="分镜没有提示词，无法生成视频",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
            # 检查是否正在生成中（不允许重复生成，除非是重新生成）
            video_status = storyboard_data.get('video_status')
            if video_status == '生成中' and not regenerate:
                InfoBar.info(
                    title="提示",
                    content="该分镜视频正在生成中，请稍候",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
                return
            
                # 如果是重新生成，清除旧的视频数据
                if regenerate:
                    db_manager.update_storyboard_video_info(
                        storyboard_id=storyboard_id,
                        video_task_id=None,
                        video_url=None,
                        video_status='未生成'
                    )
                    # 停止旧的状态查询线程
                    if hasattr(self, 'status_threads') and storyboard_id in self.status_threads:
                        old_thread = self.status_threads[storyboard_id]
                        if old_thread.isRunning():
                            old_thread.stop()
                            old_thread.wait(1000)
                        del self.status_threads[storyboard_id]
                    # 停止旧的视频生成线程
                    if hasattr(self, 'video_threads') and storyboard_id in self.video_threads:
                        old_thread = self.video_threads[storyboard_id]
                        if old_thread.isRunning():
                            old_thread.requestInterruption()
                            old_thread.wait(1000)
                        del self.video_threads[storyboard_id]
                    # 刷新界面
                    self.load_storyboards()
            
            # 创建视频生成线程
            from threads.video_generation_sora2_thread import VideoGenerationSora2Thread
            from threads.video_status_check_thread import VideoStatusCheckThread
            
            self.video_threads = getattr(self, 'video_threads', {})
            self.status_threads = getattr(self, 'status_threads', {})
            
            # 如果该分镜已有线程在运行，不重复创建
            if storyboard_id in self.video_threads:
                existing_thread = self.video_threads[storyboard_id]
                if existing_thread.isRunning():
                    InfoBar.info(
                        title="提示",
                        content="该分镜视频正在生成中，请稍候",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self,
                    )
                    return
            
            # 创建新的视频生成线程
            video_thread = VideoGenerationSora2Thread(storyboard_id, self.project_id, self)
            video_thread.progress.connect(
                lambda msg, sid=storyboard_id: self.on_video_progress(sid, msg)
            )
            video_thread.finished.connect(
                lambda task_id, sid=storyboard_id: self.on_video_finished(sid, task_id)
            )
            video_thread.error.connect(
                lambda error, sid=storyboard_id: self.on_video_error(sid, error)
            )
            self.video_threads[storyboard_id] = video_thread
            video_thread.start()
            
            InfoBar.success(
                title="提示",
                content="已开始生成视频",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            
        except Exception as e:
            from loguru import logger
            logger.error(f"生成单个视频失败: {e}")
            InfoBar.error(
                title="错误",
                content=f"生成视频失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def on_clear_prompt(self):
        """清除分镜提示词"""
        from qfluentwidgets import MessageBox
        
        dialog = MessageBox(
            title='确认清除',
            content='确定要清除所有分镜的提示词吗？\n此操作不可恢复！',
            parent=self
        )
        dialog.yesButton.setText('确定清除')
        dialog.cancelButton.setText('取消')
        
        if dialog.exec():
            try:
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                
                # 清除当前剧集所有分镜的提示词
                cursor.execute(
                    """
                    UPDATE storyboards 
                    SET prompt = NULL
                    WHERE episode_id = ?
                    """,
                    (self.episode_id,),
                )
                
                affected_rows = cursor.rowcount
                conn.commit()
                conn.close()
                
                # 刷新界面
                self.load_storyboards()
                
                InfoBar.success(
                    title="成功",
                    content=f"已清除 {affected_rows} 个分镜的提示词",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            except Exception as e:
                from loguru import logger
                logger.error(f"清除提示词失败: {e}")
                InfoBar.error(
                    title="错误",
                    content=f"清除提示词失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )

    def on_clear_details(self):
        """清除分镜详情"""
        from qfluentwidgets import MessageBox
        
        dialog = MessageBox(
            title='确认清除',
            content='确定要清除所有分镜的详情吗？\n（包括标题、对白、画面内容、镜头移动、音效、时长）\n此操作不可恢复！',
            parent=self
        )
        dialog.yesButton.setText('确定清除')
        dialog.cancelButton.setText('取消')
        
        if dialog.exec():
            try:
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                
                # 清除当前剧集所有分镜的详情（不包括提示词）
                cursor.execute(
                    """
                    UPDATE storyboards 
                    SET title = NULL,
                        dialogue = NULL,
                        screen_content = NULL,
                        camera_movement = NULL,
                        sound_effect = NULL,
                        duration = NULL
                    WHERE episode_id = ?
                    """,
                    (self.episode_id,),
                )
                
                affected_rows = cursor.rowcount
                conn.commit()
                conn.close()
                
                # 刷新界面
                self.load_storyboards()
                
                InfoBar.success(
                    title="成功",
                    content=f"已清除 {affected_rows} 个分镜的详情",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self,
                )
            except Exception as e:
                from loguru import logger
                logger.error(f"清除分镜详情失败: {e}")
                InfoBar.error(
                    title="错误",
                    content=f"清除分镜详情失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self,
                )

    def on_upload_scene(self, storyboard_id: int):
        InfoBar.info(
            title="提示",
            content="上传场景图功能待实现",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def on_download_scene(self, storyboard_id: int):
        InfoBar.info(
            title="提示",
            content="下载场景图功能待实现",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )


