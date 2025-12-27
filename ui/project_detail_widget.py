"""
项目详情界面 - 包含章节名、剧集管理、角色库
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget, QGridLayout, QDialog, QMenu
from PyQt5.QtGui import QContextMenuEvent
from qfluentwidgets import (
    TitleLabel, PushButton, PrimaryPushButton, CardWidget, BodyLabel, 
    SegmentedWidget, Pivot
)
from database_manager import db_manager
import sqlite3


class EpisodeCard(CardWidget):
    """剧集卡片"""
    edit_clicked = pyqtSignal(int)  # 剧集ID
    delete_clicked = pyqtSignal(int)  # 删除信号
    
    def __init__(self, episode_data, parent=None):
        super().__init__(parent)
        self.episode_id = episode_data.get('id')
        self.episode_data = episode_data
        # 设置固定大小，与角色卡片类似（但可以稍微大一点以显示更多信息）
        self.setFixedSize(200, 250)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 剧集标题（顶部，加粗）
        episode_number = self.episode_data.get('episode_number', 0)
        title = BodyLabel(f"第{episode_number}集")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 剧集名称
        episode_name = self.episode_data.get('episode_name', '')
        if episode_name and episode_name != f"第{episode_number}集":
            name_label = BodyLabel(f"标题: {episode_name}")
            name_label.setWordWrap(True)
            name_label.setStyleSheet("font-size: 12px;")
            layout.addWidget(name_label)
        
        # 文件信息（简化显示）
        file_path = self.episode_data.get('file_path', '')
        if file_path:
            from pathlib import Path
            file_name = Path(file_path).name
            path_label = BodyLabel(f"文件: {file_name}")
            path_label.setStyleSheet("color: #666; font-size: 10px;")
            path_label.setWordWrap(True)
            layout.addWidget(path_label)
        
        layout.addStretch()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 编辑按钮
        edit_btn = PushButton("编辑")
        edit_btn.setFixedHeight(30)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.episode_id))
        button_layout.addWidget(edit_btn)
        
        # 删除按钮
        from PyQt5.QtWidgets import QMenu
        from PyQt5.QtGui import QContextMenuEvent
        layout.addLayout(button_layout)
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """右键菜单事件"""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        delete_action = menu.addAction("删除剧集")
        delete_action.triggered.connect(lambda: self.delete_clicked.emit(self.episode_id))
        menu.exec_(event.globalPos())


class ProjectDetailWidget(QWidget):
    """项目详情界面"""
    
    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_data = None
        self.init_ui()
        self.load_project_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部标题和标签页导航（水平布局）
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(20)
        
        # 项目标题（左侧）
        self.project_title_label = TitleLabel("")
        self.project_title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.project_title_label)
        
        # 标签页导航（标题右侧）
        self.pivot = Pivot(self)
        self.pivot.setStyleSheet("""
            Pivot {
                font-size: 13px;
            }
        """)
        header_layout.addWidget(self.pivot)
        header_layout.addStretch()
        
        # 新增按钮和识别角色按钮（右上角，根据当前标签页显示不同的按钮）
        self.header_add_btn = PrimaryPushButton("新增")
        self.header_add_btn.hide()  # 默认隐藏
        header_layout.addWidget(self.header_add_btn)
        
        # 识别角色按钮（仅角色库标签页显示）
        self.identify_characters_btn = PushButton("识别角色")
        self.identify_characters_btn.hide()  # 默认隐藏
        header_layout.addWidget(self.identify_characters_btn)
        
        # 一键生成角色图按钮（仅角色库标签页显示）
        self.batch_generate_images_btn = PrimaryPushButton("一键生成角色图")
        self.batch_generate_images_btn.hide()  # 默认隐藏
        header_layout.addWidget(self.batch_generate_images_btn)
        
        layout.addWidget(header_widget)
        
        # 内容区域 - 使用StackedWidget
        self.stacked_widget = QStackedWidget()
        
        # 创建三个标签页内容
        self.chapter_widget = self.create_chapter_tab()
        self.episodes_widget = self.create_episodes_tab()
        self.characters_widget = self.create_characters_tab()
        
        self.stacked_widget.addWidget(self.chapter_widget)
        self.stacked_widget.addWidget(self.episodes_widget)
        self.stacked_widget.addWidget(self.characters_widget)
        
        layout.addWidget(self.stacked_widget)
        
    def create_chapter_tab(self):
        """创建章节名标签页"""
        chapter_widget = QWidget()
        chapter_layout = QVBoxLayout(chapter_widget)
        chapter_layout.setContentsMargins(20, 20, 20, 20)
        chapter_layout.setSpacing(15)
        
        # 章节名输入
        chapter_label = BodyLabel("章节名:")
        chapter_layout.addWidget(chapter_label)
        
        from qfluentwidgets import LineEdit
        self.chapter_name_input = LineEdit()
        self.chapter_name_input.setPlaceholderText("请输入章节名")
        self.chapter_name_input.textChanged.connect(self.save_chapter_name)
        chapter_layout.addWidget(self.chapter_name_input)
        
        chapter_layout.addStretch()
        return chapter_widget
        
    def create_episodes_tab(self):
        """创建剧集管理标签页"""
        episodes_widget = QWidget()
        episodes_layout = QVBoxLayout(episodes_widget)
        episodes_layout.setContentsMargins(20, 20, 20, 20)
        episodes_layout.setSpacing(15)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 剧集容器（使用网格布局，每行6个）
        self.episodes_container = QWidget()
        self.episodes_grid = QGridLayout(self.episodes_container)
        self.episodes_grid.setSpacing(15)
        self.episodes_grid.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.episodes_container)
        episodes_layout.addWidget(scroll)
        
        return episodes_widget
        
    def create_characters_tab(self):
        """创建角色库标签页"""
        characters_widget = QWidget()
        characters_layout = QVBoxLayout(characters_widget)
        characters_layout.setContentsMargins(20, 20, 20, 20)
        characters_layout.setSpacing(15)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 角色容器（网格布局）
        self.characters_container = QWidget()
        self.characters_grid = QGridLayout(self.characters_container)
        self.characters_grid.setSpacing(15)
        self.characters_grid.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.characters_container)
        characters_layout.addWidget(scroll)
        
        return characters_widget
        
    def load_project_data(self):
        """加载项目数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, cover_image, novel_file_path, novel_folder_path, 
                       style, aspect_ratio, description, chapter_name
                FROM projects
                WHERE id = ?
            ''', (self.project_id,))
            project = cursor.fetchone()
            conn.close()
            
            if project:
                self.project_data = {
                    'id': project[0],
                    'title': project[1],
                    'cover_image': project[2],
                    'novel_file_path': project[3],
                    'novel_folder_path': project[4],
                    'style': project[5],
                    'aspect_ratio': project[6],
                    'description': project[7],
                    'chapter_name': project[8]
                }
                
                # 更新界面
                self.update_ui()
        except Exception as e:
            from loguru import logger
            logger.error(f"加载项目数据失败: {e}")
            
    def update_ui(self):
        """更新界面"""
        if not self.project_data:
            return
            
        # 设置项目标题
        project_title = self.project_data.get('title', '未命名项目')
        self.project_title_label.setText(project_title)
        
        # 设置标签页（只显示剧集管理和角色库，不显示项目标题）
        self.pivot.addItem(
            routeKey="episodes",
            text="剧集管理",
            onClick=lambda: self.switch_tab(1)
        )
        self.pivot.addItem(
            routeKey="characters",
            text="角色库",
            onClick=lambda: self.switch_tab(2)
        )
        
        # 设置按钮的点击事件
        self.header_add_btn.clicked.connect(self.on_header_add_clicked)
        self.identify_characters_btn.clicked.connect(self.on_identify_characters)
        self.batch_generate_images_btn.clicked.connect(self.on_batch_generate_images)
        
        self.pivot.setCurrentItem("episodes")
        self.stacked_widget.setCurrentIndex(1)  # 默认显示剧集管理
        self.update_add_button()
        
        # 更新章节名
        chapter_name = self.project_data.get('chapter_name', '')
        if chapter_name:
            self.chapter_name_input.setText(chapter_name)
            
        # 加载剧集列表
        self.load_episodes()
        
        # 加载角色列表
        self.load_characters()
        
    def switch_tab(self, index):
        """切换标签页"""
        self.stacked_widget.setCurrentIndex(index)
        self.update_add_button()
        
    def update_add_button(self):
        """更新新增按钮的显示和功能"""
        current_index = self.stacked_widget.currentIndex()
        if current_index == 1:  # 剧集管理
            self.header_add_btn.show()
            self.header_add_btn.setText("新增")
            self.identify_characters_btn.hide()
        elif current_index == 2:  # 角色库
            self.header_add_btn.show()
            self.header_add_btn.setText("新增")
            self.identify_characters_btn.show()
            self.batch_generate_images_btn.show()
        else:
            self.header_add_btn.hide()
            self.identify_characters_btn.hide()
            self.batch_generate_images_btn.hide()
            
    def on_header_add_clicked(self):
        """顶部新增按钮点击事件"""
        current_index = self.stacked_widget.currentIndex()
        if current_index == 1:  # 剧集管理
            self.show_add_episode_dialog()
        elif current_index == 2:  # 角色库
            self.show_add_character_dialog()
            
    def on_identify_characters(self):
        """识别角色按钮点击事件"""
        from threads.character_analysis_thread import CharacterAnalysisThread
        from qfluentwidgets import InfoBar, InfoBarPosition
        
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
        
        # 停止之前的分析线程（如果存在）
        if hasattr(self, 'character_analysis_thread') and self.character_analysis_thread and self.character_analysis_thread.isRunning():
            self.character_analysis_thread.terminate()
            self.character_analysis_thread.wait()
        
        # 显示分析提示
        InfoBar.info(
            title='分析中',
            content='正在分析小说内容，提取角色信息...',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
        # 创建并启动分析线程
        self.character_analysis_thread = CharacterAnalysisThread(self.project_id, self)
        self.character_analysis_thread.progress.connect(self.on_character_analysis_progress)
        self.character_analysis_thread.finished.connect(self.on_character_analysis_finished)
        self.character_analysis_thread.error.connect(self.on_character_analysis_error)
        self.character_analysis_thread.start()
        
    def on_character_analysis_progress(self, message: str):
        """角色分析进度回调"""
        from loguru import logger
        logger.info(f"角色分析进度: {message}")
        
    def on_character_analysis_finished(self, characters: list):
        """角色分析完成回调"""
        try:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.success(
                title='成功',
                content=f'已识别 {len(characters)} 个角色',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            from loguru import logger
            logger.error(f"显示成功提示失败: {e}")
        
        # 重新加载角色列表
        try:
            self.load_characters()
        except Exception as e:
            from loguru import logger
            logger.error(f"重新加载角色列表失败: {e}")
        
    def on_character_analysis_error(self, error_message: str):
        """角色分析错误回调"""
        try:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.error(
                title='分析失败',
                content=error_message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except Exception as e:
            from loguru import logger
            logger.error(f"显示错误提示失败: {e}")
            # 如果InfoBar显示失败，至少打印错误信息
            print(f"角色分析失败: {error_message}")
            
    def save_chapter_name(self):
        """保存章节名"""
        chapter_name = self.chapter_name_input.text().strip()
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects
                SET chapter_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (chapter_name, self.project_id))
            conn.commit()
            conn.close()
        except Exception as e:
            from loguru import logger
            logger.error(f"保存章节名失败: {e}")
            
    def load_episodes(self):
        """加载剧集列表"""
        # 清空现有剧集
        while self.episodes_grid.count():
            item = self.episodes_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, episode_number, episode_name, file_path
                FROM episodes
                WHERE project_id = ?
                ORDER BY episode_number ASC
            ''', (self.project_id,))
            episodes = cursor.fetchall()
            conn.close()
            
            # 网格布局，每行6个（与角色库一致）
            row = 0
            col = 0
            for episode in episodes:
                episode_data = {
                    'id': episode[0],
                    'episode_number': episode[1],
                    'episode_name': episode[2],
                    'file_path': episode[3]
                }
                card = EpisodeCard(episode_data, self)
                card.edit_clicked.connect(self.on_edit_episode)
                card.delete_clicked.connect(self.on_delete_episode)
                self.episodes_grid.addWidget(card, row, col)
                
                col += 1
                if col >= 6:
                    col = 0
                    row += 1
                
        except Exception as e:
            from loguru import logger
            logger.error(f"加载剧集列表失败: {e}")
            
    def load_characters(self):
        """加载角色列表"""
        # 清空现有角色
        while self.characters_grid.count():
            item = self.characters_grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                # 断开所有信号连接
                try:
                    widget.character_clicked.disconnect()
                except:
                    pass
                # 延迟删除，避免在事件处理中删除对象
                widget.deleteLater()
        
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, front_image, sora_character_username, sora_status
                FROM characters
                WHERE project_id = ?
                ORDER BY created_at ASC
            ''', (self.project_id,))
            characters = cursor.fetchall()
            conn.close()
            
            # 网格布局，每行6个（与项目卡片一致）
            from ui.character_card import CharacterCard
            row = 0
            col = 0
            for char in characters:
                character_data = {
                    'id': char[0],
                    'name': char[1],
                    'description': char[2],
                    'front_image': char[3],
                    'sora_character_username': char[4],
                    'sora_status': char[5]
                }
                character_card = CharacterCard(character_data, self)
                character_card.character_clicked.connect(self.on_character_clicked)
                self.characters_grid.addWidget(character_card, row, col)
                
                col += 1
                if col >= 6:
                    col = 0
                    row += 1
                    
        except Exception as e:
            from loguru import logger
            logger.error(f"加载角色列表失败: {e}")
            
    def on_character_clicked(self, character_id):
        """点击角色卡片"""
        from components.character_detail_dialog import CharacterDetailDialog
        dialog = CharacterDetailDialog(character_id, self.project_id, self)
        dialog.exec_()
        # 对话框关闭后刷新角色列表（可能更新了状态）
        self.load_characters()
    
    def on_batch_generate_images(self):
        """一键生成所有角色图"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        from PyQt5.QtCore import Qt
        from loguru import logger
        from threads.character_image_generation_thread import CharacterImageGenerationThread
        
        # 获取所有角色
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name
                FROM characters
                WHERE project_id = ?
                ORDER BY created_at ASC
            ''', (self.project_id,))
            characters = cursor.fetchall()
            conn.close()
            
            if not characters:
                InfoBar.warning(
                    title='提示',
                    content='当前项目中没有角色，请先添加角色',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            # 检查是否有生成任务在运行
            if hasattr(self, 'batch_generation_threads') and self.batch_generation_threads:
                running_count = sum(1 for t in self.batch_generation_threads.values() if t and t.isRunning())
                if running_count > 0:
                    InfoBar.warning(
                        title='提示',
                        content=f'已有 {running_count} 个生成任务正在进行中，请稍候...',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                    return
            
            # 确认对话框
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                '确认生成',
                f'将为 {len(characters)} 个角色生成图片，这可能需要较长时间，是否继续？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 禁用按钮
            self.batch_generate_images_btn.setEnabled(False)
            self.batch_generate_images_btn.setText(f"生成中 (0/{len(characters)})")
            
            # 显示开始提示
            InfoBar.info(
                title='开始批量生成',
                content=f'正在为 {len(characters)} 个角色生成图片，请稍候...',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 初始化线程字典
            self.batch_generation_threads = {}
            self.batch_generation_completed = 0
            self.batch_generation_total = len(characters)
            
            # 为每个角色创建生成线程
            for character_id, character_name in characters:
                thread = CharacterImageGenerationThread(character_id, self.project_id, self)
                # 使用闭包正确捕获 character_id
                def make_progress_handler(cid):
                    return lambda msg: self.on_batch_generation_progress(cid, msg)
                def make_finished_handler(cid):
                    return lambda path: self.on_batch_generation_finished(cid, path)
                def make_error_handler(cid):
                    return lambda error: self.on_batch_generation_error(cid, error)
                
                thread.progress.connect(make_progress_handler(character_id))
                thread.finished.connect(make_finished_handler(character_id))
                thread.error.connect(make_error_handler(character_id))
                self.batch_generation_threads[character_id] = thread
                thread.start()
                
                # 避免同时启动太多线程，每个线程启动后稍微延迟
                from PyQt5.QtCore import QThread
                QThread.msleep(100)
            
        except Exception as e:
            logger.error(f"批量生成角色图失败: {e}")
            InfoBar.error(
                title='错误',
                content=f'批量生成失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            if hasattr(self, 'batch_generation_threads'):
                self.batch_generation_threads = {}
            self.batch_generate_images_btn.setEnabled(True)
            self.batch_generate_images_btn.setText("一键生成角色图")
    
    def on_batch_generation_progress(self, character_id, message):
        """批量生成进度回调"""
        from loguru import logger
        logger.info(f"角色 {character_id} 生成进度: {message}")
    
    def on_batch_generation_finished(self, character_id, image_path):
        """批量生成完成回调"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        from PyQt5.QtCore import Qt
        from loguru import logger
        
        logger.info(f"角色 {character_id} 图片生成完成: {image_path}")
        
        # 更新完成计数
        self.batch_generation_completed += 1
        
        # 更新按钮文本
        self.batch_generate_images_btn.setText(
            f"生成中 ({self.batch_generation_completed}/{self.batch_generation_total})"
        )
        
        # 检查是否全部完成
        if self.batch_generation_completed >= self.batch_generation_total:
            # 恢复按钮
            self.batch_generate_images_btn.setEnabled(True)
            self.batch_generate_images_btn.setText("一键生成角色图")
            
            # 显示完成提示
            InfoBar.success(
                title='批量生成完成',
                content=f'已为 {self.batch_generation_completed} 个角色生成图片',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 延迟重新加载角色列表，避免在事件处理中删除对象
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.load_characters)
            
            # 清空线程字典
            self.batch_generation_threads = {}
    
    def on_batch_generation_error(self, character_id, error_message):
        """批量生成错误回调"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        from PyQt5.QtCore import Qt
        from loguru import logger
        
        logger.error(f"角色 {character_id} 图片生成失败: {error_message}")
        
        # 更新完成计数（即使失败也计入）
        self.batch_generation_completed += 1
        
        # 更新按钮文本
        self.batch_generate_images_btn.setText(
            f"生成中 ({self.batch_generation_completed}/{self.batch_generation_total})"
        )
        
        # 检查是否全部完成
        if self.batch_generation_completed >= self.batch_generation_total:
            # 恢复按钮
            self.batch_generate_images_btn.setEnabled(True)
            self.batch_generate_images_btn.setText("一键生成角色图")
            
            # 显示完成提示（包含错误信息）
            InfoBar.warning(
                title='批量生成完成',
                content=f'已完成 {self.batch_generation_total} 个角色的生成任务（部分可能失败）',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
            # 延迟重新加载角色列表，避免在事件处理中删除对象
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self.load_characters)
            
            # 清空线程字典
            self.batch_generation_threads = {}
            
    def show_add_episode_dialog(self):
        """显示添加剧集对话框"""
        from components.add_episode_dialog import AddEpisodeDialog
        
        dialog = AddEpisodeDialog(self.project_id, self)
        if dialog.exec_() == QDialog.Accepted:
            # 重新加载剧集列表
            self.load_episodes()
        
    def show_add_character_dialog(self):
        """显示添加角色对话框"""
        # TODO: 实现添加角色对话框
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.info(
            title='提示',
            content='添加角色功能待实现',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        
    def on_edit_episode(self, episode_id):
        """编辑剧集 - 打开剧集详情页面"""
        try:
            # 获取剧集信息
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT episode_number, project_id
                FROM episodes
                WHERE id = ?
            ''', (episode_id,))
            episode = cursor.fetchone()
            
            if not episode:
                conn.close()
                return
            
            episode_number = episode[0]
            project_id = episode[1]
            
            # 获取项目标题
            cursor.execute('''
                SELECT title
                FROM projects
                WHERE id = ?
            ''', (project_id,))
            project = cursor.fetchone()
            conn.close()
            
            if not project:
                return
            
            project_title = project[0]
            
            # 获取主窗口并添加剧集详情页面
            main_window = self.window()
            if hasattr(main_window, 'add_episode_detail_page'):
                main_window.add_episode_detail_page(
                    episode_id, 
                    project_id, 
                    episode_number, 
                    project_title
                )
        except Exception as e:
            from loguru import logger
            logger.error(f"打开剧集详情页面失败: {e}")
    
    def on_delete_episode(self, episode_id):
        """删除剧集"""
        from qfluentwidgets import MessageBox
        dialog = MessageBox(
            title='确认删除',
            content='确定要删除这个剧集吗？此操作不可恢复！',
            parent=self
        )
        dialog.yesButton.setText('确定删除')
        dialog.cancelButton.setText('取消')
        
        if dialog.exec():
            try:
                # 获取主窗口并关闭对应的详情页面（同时删除数据）
                main_window = self.window()
                if hasattr(main_window, 'remove_episode_detail_page'):
                    main_window.remove_episode_detail_page(episode_id, delete_data=True)
                else:
                    # 如果没有主窗口方法，直接删除数据库
                    conn = sqlite3.connect(db_manager.db_path)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM episodes WHERE id = ?', (episode_id,))
                    conn.commit()
                    conn.close()
                
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.success(
                    title='成功',
                    content='剧集已删除',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
                # 重新加载剧集列表
                self.load_episodes()
            except Exception as e:
                from loguru import logger
                logger.error(f"删除剧集失败: {e}")
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.error(
                    title='错误',
                    content=f'删除剧集失败: {str(e)}',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )

