"""
项目列表界面 - 网格布局，6个项目一行
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QMenu
from PyQt5.QtGui import QPixmap, QPainter, QFont, QContextMenuEvent
from qfluentwidgets import (
    TitleLabel, PushButton, PrimaryPushButton, CardWidget, BodyLabel
)
from constants import PROJECT_NAME
from database_manager import db_manager
from ui.image_widget import ImageWidget
import sqlite3


class ProjectCard(CardWidget):
    """项目卡片"""
    project_clicked = pyqtSignal(int)  # 项目ID
    delete_requested = pyqtSignal(int)  # 删除请求信号
    
    def __init__(self, project_data, parent=None):
        super().__init__(parent)
        self.project_id = project_data.get('id')
        self.project_data = project_data
        self.setFixedSize(180, 240)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 封面图片（占位）
        cover_url = self.project_data.get('cover_image', '')
        self.cover_widget = ImageWidget(cover_url, size=160)
        self.cover_widget.setFixedSize(160, 120)
        layout.addWidget(self.cover_widget)
        
        # 标题
        title = BodyLabel(self.project_data.get('title', '未命名项目'))
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        
        # 简介（截断显示）
        description = self.project_data.get('description', '')
        if description:
            desc_text = description[:30] + '...' if len(description) > 30 else description
            desc_label = BodyLabel(desc_text)
            desc_label.setStyleSheet("color: #666; font-size: 11px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        layout.addStretch()
        
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.project_clicked.emit(self.project_id)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """右键菜单事件"""
        menu = QMenu(self)
        delete_action = menu.addAction("删除项目")
        delete_action.triggered.connect(self.on_delete_requested)
        menu.exec_(event.globalPos())

    def on_delete_requested(self):
        """请求删除项目"""
        # 发送删除信号，让父组件处理
        self.delete_requested.emit(self.project_id)


class TaskListWidget(QWidget):
    """项目列表界面 - 网格布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("taskListWidget")
        self.init_ui()
        self.load_projects()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题和控制按钮
        header_layout = QHBoxLayout()
        title = TitleLabel(PROJECT_NAME)
        header_layout.addWidget(title)
        header_layout.addStretch()

        # 添加项目按钮
        self.add_project_btn = PrimaryPushButton('添加项目')
        self.add_project_btn.clicked.connect(self.show_add_project_dialog)
        header_layout.addWidget(self.add_project_btn)

        layout.addLayout(header_layout)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 项目网格容器
        self.projects_container = QWidget()
        self.grid_layout = QGridLayout(self.projects_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.projects_container)
        layout.addWidget(scroll)

    def load_projects(self):
        """加载项目列表"""
        # 清空现有项目
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 从数据库加载项目
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, cover_image, description, created_at
                FROM projects
                ORDER BY created_at DESC
            ''')
            projects = cursor.fetchall()
            conn.close()
            
            # 创建项目卡片（6个一行）
            row = 0
            col = 0
            for project in projects:
                project_data = {
                    'id': project[0],
                    'title': project[1],
                    'cover_image': project[2],
                    'description': project[3],
                    'created_at': project[4]
                }
                card = ProjectCard(project_data, self)
                card.project_clicked.connect(self.on_project_clicked)
                card.delete_requested.connect(self.on_delete_project)
                self.grid_layout.addWidget(card, row, col)
                
                col += 1
                if col >= 6:
                    col = 0
                    row += 1
                    
        except Exception as e:
            from loguru import logger
            logger.error(f"加载项目列表失败: {e}")

    def on_project_clicked(self, project_id):
        """点击项目卡片"""
        # 打开项目详情页面
        from ui.project_detail_widget import ProjectDetailWidget
        detail_widget = ProjectDetailWidget(project_id, self)
        
        # 获取主窗口并切换到详情页面
        main_window = self.window()
        if hasattr(main_window, 'stackedWidget'):
            # 使用主窗口的stackedWidget切换
            main_window.stackedWidget.addWidget(detail_widget)
            main_window.stackedWidget.setCurrentWidget(detail_widget)
        else:
            # 如果没有stackedWidget，尝试添加到导航
            if hasattr(main_window, 'addSubInterface'):
                # 临时添加到导航（需要唯一objectName）
                detail_widget.setObjectName(f"projectDetail_{project_id}")
                main_window.addSubInterface(detail_widget, None, "项目详情")
                main_window.stackedWidget.setCurrentWidget(detail_widget)

    def on_delete_project(self, project_id):
        """删除项目"""
        from components.delete_project_dialog import DeleteProjectDialog
        dialog = DeleteProjectDialog(self)
        if dialog.exec_() == 1:  # QDialog.Accepted
            # 从数据库删除项目
            try:
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                # 删除项目（外键约束会自动删除关联的episodes、characters、storyboards）
                cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
                conn.commit()
                conn.close()
                
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.success(
                    title='成功',
                    content='项目已删除',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                
                # 重新加载项目列表
                self.load_projects()
            except Exception as e:
                from loguru import logger
                logger.error(f"删除项目失败: {e}")
                from qfluentwidgets import InfoBar, InfoBarPosition
                InfoBar.error(
                    title='错误',
                    content=f'删除项目失败: {str(e)}',
                    orient=Qt.Horizontal,

                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )

    def show_add_project_dialog(self):
        """显示添加项目对话框"""
        from components.add_project_dialog import AddProjectDialog
        dialog = AddProjectDialog(self)
        if dialog.exec_() == 1:  # QDialog.Accepted
            # 重新加载项目列表
            self.load_projects()
