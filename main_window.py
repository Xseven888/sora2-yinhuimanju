"""
重构版Sora2主窗口 - 空白框架
使用PyQt-Fluent-Widgets创建现代化界面
"""

import sys
import os
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    FluentWindow, FluentIcon
)
from PyQt5.QtWidgets import QMenu, QApplication
from PyQt5.QtCore import Qt
from constants import PROJECT_NAME

# 导入拆分的UI组件
from ui.settings_interface import SettingsInterface
from ui.task_list_widget import TaskListWidget
from ui.voice_library_interface import VoiceLibraryInterface


class MainWindow(FluentWindow):
    """主窗口 - 漫剧视频生成工具"""
    
    def __init__(self):
        super().__init__()
        # 存储动态添加的剧集详情页面 {episode_id: (widget, navigation_item)}
        self.episode_widgets = {}
        # 存储导航项到episode_id的映射 {navigation_item: episode_id}
        self.nav_item_to_episode = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.resize(1200, 800)
        self.setWindowTitle("音绘漫剧")
        
        # 设置窗口图标
        import sys
        # 处理打包后的资源路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境
            base_path = Path(__file__).parent
        
        # 优先尝试 .ico 格式，如果没有则使用 .png
        logo_path = base_path / "logo.ico"
        if not logo_path.exists():
            logo_path = base_path / "logo.png"
        
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        # 创建界面
        self.task_interface = TaskListWidget(self)
        self.voice_library_interface = VoiceLibraryInterface(self)
        self.settings_interface = SettingsInterface(self)

        # 添加到导航界面
        self.addSubInterface(self.task_interface, FluentIcon.ROBOT, PROJECT_NAME)
        self.addSubInterface(self.voice_library_interface, FluentIcon.MUSIC, '音色库')
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, '设置')

        self.navigationInterface.setCurrentItem(self.task_interface.objectName())

        # 设置最小宽度
        self.setMinimumWidth(1000)
    
    def add_episode_detail_page(self, episode_id, project_id, episode_number, project_title):
        """添加剧集详情页面到侧边栏"""
        # 如果页面已存在，直接切换到该页面
        if episode_id in self.episode_widgets:
            widget, nav_item = self.episode_widgets[episode_id]
            self.navigationInterface.setCurrentItem(widget.objectName())
            return
        
        # 创建剧集详情页面
        from ui.episode_detail_widget import EpisodeDetailWidget
        episode_widget = EpisodeDetailWidget(episode_id, project_id, self)
        
        # 设置唯一objectName
        episode_widget.setObjectName(f"episodeDetail_{episode_id}")
        
        # 页面标题：项目标题+第几集
        page_title = f"{project_title}-第{episode_number}集"
        
        # 添加到导航界面
        nav_item = self.addSubInterface(episode_widget, FluentIcon.DOCUMENT, page_title)
        
        # 存储引用
        self.episode_widgets[episode_id] = (episode_widget, nav_item)
        self.nav_item_to_episode[nav_item] = episode_id
        
        # 为导航界面添加右键菜单支持
        self.navigationInterface.setContextMenuPolicy(Qt.CustomContextMenu)
        if not hasattr(self, '_context_menu_connected'):
            self.navigationInterface.customContextMenuRequested.connect(self.on_navigation_context_menu)
            self._context_menu_connected = True
        
        # 切换到新页面
        self.navigationInterface.setCurrentItem(episode_widget.objectName())
    
    def on_navigation_context_menu(self, position):
        """导航界面右键菜单"""
        try:
            # 获取当前选中的导航项
            current_item = self.navigationInterface.currentItem()
            if not current_item:
                return
            
            # 获取当前widget的objectName
            current_widget = self.stackedWidget.currentWidget()
            if not current_widget:
                return
            
            current_object_name = current_widget.objectName()
            
            # 检查是否是剧集详情页面（objectName格式：episodeDetail_{episode_id}）
            if not current_object_name.startswith('episodeDetail_'):
                return
            
            # 提取episode_id
            try:
                episode_id = int(current_object_name.replace('episodeDetail_', ''))
            except ValueError:
                return
            
            # 检查episode_id是否存在于字典中
            if episode_id not in self.episode_widgets:
                return
            
            # 显示右键菜单
            menu = QMenu(self)
            close_action = menu.addAction("关闭")
            
            action = menu.exec_(self.navigationInterface.mapToGlobal(position))
            if action == close_action:
                # 关闭页面，但不删除数据
                self.remove_episode_detail_page(episode_id, delete_data=False)
        except Exception as e:
            from loguru import logger
            logger.error(f"导航右键菜单错误: {e}")
            import traceback
            traceback.print_exc()
    
    def remove_episode_detail_page(self, episode_id, delete_data=False):
        """移除剧集详情页面"""
        if episode_id not in self.episode_widgets:
            # 如果不在字典中，可能已经被删除了，尝试从导航界面清理
            # 遍历所有导航项，找到对应的剧集页面并移除
            nav = getattr(self, "navigationInterface", None)
            if nav:
                try:
                    # 尝试通过objectName查找并移除
                    target_object_name = f"episodeDetail_{episode_id}"
                    for i in range(nav.count()):
                        item = nav.item(i)
                        if item and hasattr(item, 'routeKey'):
                            if item.routeKey == target_object_name:
                                nav.removeItem(item)
                                break
                except Exception as e:
                    from loguru import logger
                    logger.error(f"清理导航项失败: {e}")
            return
        
        widget, nav_item = self.episode_widgets[episode_id]
        
        # 如果删除数据，从数据库删除剧集
        if delete_data:
            try:
                import sqlite3
                from database_manager import db_manager
                conn = sqlite3.connect(db_manager.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM episodes WHERE id = ?', (episode_id,))
                conn.commit()
                conn.close()
            except Exception as e:
                from loguru import logger
                logger.error(f"删除剧集数据失败: {e}")
        
        # 从导航界面移除（尝试多种方法确保成功）
        nav = getattr(self, "navigationInterface", None)
        removed_from_nav = False
        if nav:
            try:
                # 方法1: 尝试使用 removeItem
                if hasattr(nav, "removeItem"):
                    nav.removeItem(nav_item)
                    removed_from_nav = True
                # 方法2: 尝试使用 removeWidget
                elif hasattr(nav, "removeWidget"):
                    nav.removeWidget(nav_item)
                    removed_from_nav = True
                # 方法3: 尝试通过 routeKey 查找并移除
                elif hasattr(nav_item, 'routeKey'):
                    target_object_name = widget.objectName()
                    for i in range(nav.count()):
                        item = nav.item(i)
                        if item and hasattr(item, 'routeKey') and item.routeKey == target_object_name:
                            if hasattr(nav, "removeItem"):
                                nav.removeItem(item)
                            removed_from_nav = True
                            break
            except Exception as e:
                from loguru import logger
                logger.error(f"从导航中移除剧集页面失败: {e}")
        
        # 如果导航移除失败，尝试从stackedWidget中移除
        if not removed_from_nav:
            try:
                stacked = getattr(self, "stackedWidget", None)
                if stacked:
                    stacked.removeWidget(widget)
            except Exception as e:
                from loguru import logger
                logger.error(f"从stackedWidget移除失败: {e}")
        
        # 删除widget
        widget.deleteLater()
        
        # 从字典中移除（无论导航移除是否成功，都要清理内部状态）
        del self.episode_widgets[episode_id]
        if nav_item in self.nav_item_to_episode:
            del self.nav_item_to_episode[nav_item]

    def closeEvent(self, a0):
        """窗口关闭事件"""
        super().closeEvent(a0)
