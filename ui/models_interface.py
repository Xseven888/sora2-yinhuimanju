"""
模型管理界面
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import TitleLabel, TableWidget
from database_manager import model_manager

class ModelsInterface(QWidget):
    """模型管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modelsInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        title = TitleLabel('Sora 2 模型介绍')
        layout.addWidget(title)

        # 创建表格
        self.models_table = TableWidget()
        self.setup_models_table()
        layout.addWidget(self.models_table)

    def setup_models_table(self):
        """设置模型表格"""
        models = model_manager.get_all_models()

        # 设置表格列
        headers = ['模型名称', '模型ID', '方向', '画质', '描述']
        self.models_table.setColumnCount(len(headers))
        self.models_table.setHorizontalHeaderLabels(headers)
        self.models_table.setRowCount(len(models))

        # 设置列宽
        self.models_table.setColumnWidth(0, 150)  # 模型名称
        self.models_table.setColumnWidth(1, 180)  # 模型ID
        self.models_table.setColumnWidth(2, 80)   # 方向
        self.models_table.setColumnWidth(3, 60)   # 画质
        self.models_table.setColumnWidth(4, 400)  # 描述

        # 填充表格数据
        for row, (model_id, model_info) in enumerate(models.items()):
            from PyQt5.QtWidgets import QTableWidgetItem
            
            # 模型名称
            name_item = QTableWidgetItem(model_info['name'])
            self.models_table.setItem(row, 0, name_item)

            # 模型ID
            id_item = QTableWidgetItem(model_id)
            self.models_table.setItem(row, 1, id_item)

            # 方向
            orientation = model_info['orientation']
            orientation_text = {
                'auto': '自动',
                'landscape': '横屏',
                'portrait': '竖屏'
            }.get(orientation, orientation)
            orientation_item = QTableWidgetItem(orientation_text)
            self.models_table.setItem(row, 2, orientation_item)

            # 画质
            quality = model_info['quality']
            quality_text = "HD" if quality == 'hd' else "标准"
            quality_item = QTableWidgetItem(quality_text)
            self.models_table.setItem(row, 3, quality_item)

            # 描述
            desc_item = QTableWidgetItem(model_info['description'])
            desc_item.setToolTip(model_info['description'])  # 设置工具提示
            self.models_table.setItem(row, 4, desc_item)

        # 设置表格属性
        vertical_header = self.models_table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
            
        horizontal_header = self.models_table.horizontalHeader()
        if horizontal_header:
            horizontal_header.setStretchLastSection(True)
            
        self.models_table.setAlternatingRowColors(True)