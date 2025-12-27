"""
批量添加任务对话框
"""

import csv
import io
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QFileDialog, 
    QWidget, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    TitleLabel, PushButton, PrimaryPushButton, BodyLabel, CardWidget, InfoBar, InfoBarPosition
)

class BatchAddTaskDialog(QDialog):
    """批量添加任务对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks_data = []  # 存储解析的任务数据
        self.setWindowTitle("批量添加视频生成任务")
        self.setModal(True)
        self.resize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = TitleLabel("批量添加视频生成任务")
        layout.addWidget(title)
        
        # 说明文本
        description = BodyLabel("请按照表格模板格式准备CSV文件，仅支持文生视频任务")
        description.setStyleSheet("color: #666;")
        layout.addWidget(description)
        
        # 模板下载和文件选择区域
        template_layout = QHBoxLayout()
        
        self.download_template_btn = PushButton("下载表格模板")
        self.download_template_btn.clicked.connect(self.download_template)
        template_layout.addWidget(self.download_template_btn)
        
        self.select_file_btn = PushButton("选择CSV文件")
        self.select_file_btn.clicked.connect(self.select_csv_file)
        template_layout.addWidget(self.select_file_btn)
        
        template_layout.addStretch()
        layout.addLayout(template_layout)
        
        # 预览表格
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(['提示词', '分辨率', '时长(秒)', '状态'])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)
        layout.addWidget(self.preview_table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_btn = PrimaryPushButton("批量创建")
        self.create_btn.clicked.connect(self.accept)
        self.create_btn.setEnabled(False)  # 默认禁用，只有成功解析文件后才启用
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
    def download_template(self):
        """下载表格模板"""
        try:
            # 创建CSV模板内容
            template_content = """提示词,分辨率,时长(秒)
A beautiful sunset over the ocean,16:9,10
A cat playing with a ball of yarn,9:16,15
A bustling city street at night,16:9,10"""
            
            # 保存文件对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存表格模板", 
                "批量任务模板.csv", 
                "CSV文件 (*.csv)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                    f.write(template_content)
                    
                InfoBar.success(
                    title='成功',
                    content='模板文件已保存',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'保存模板失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def select_csv_file(self):
        """选择CSV文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "选择CSV文件", 
                "", 
                "CSV文件 (*.csv)"
            )
            
            if file_path:
                self.parse_csv_file(file_path)
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'选择文件失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def parse_csv_file(self, file_path):
        """解析CSV文件"""
        try:
            self.tasks_data = []
            self.preview_table.setRowCount(0)
            
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                # 使用csv模块读取
                reader = csv.reader(f)
                rows = list(reader)
                
                if len(rows) < 2:
                    InfoBar.warning(
                        title='警告',
                        content='CSV文件内容为空或格式不正确',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    return
                
                # 检查表头
                headers = rows[0]
                if len(headers) < 3 or headers[0] != '提示词' or headers[1] != '分辨率' or headers[2] != '时长(秒)':
                    InfoBar.warning(
                        title='警告',
                        content='CSV文件格式不正确，请使用提供的模板',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    return
                
                # 解析数据行
                for i, row in enumerate(rows[1:], start=1):
                    if len(row) >= 3:
                        prompt = row[0].strip()
                        resolution = row[1].strip()
                        duration_str = row[2].strip()
                        
                        # 验证数据
                        if not prompt:
                            status = '提示词为空'
                        elif resolution not in ['16:9', '9:16']:
                            status = '分辨率无效'
                        else:
                            try:
                                duration = int(duration_str)
                                if duration not in [10, 15]:
                                    status = '时长无效(仅支持10或15)'
                                else:
                                    # 有效数据
                                    self.tasks_data.append({
                                        'prompt': prompt,
                                        'resolution': resolution,
                                        'duration': duration
                                    })
                                    status = '有效'
                            except ValueError:
                                status = '时长格式错误'
                        
                        # 添加到预览表格
                        row_position = self.preview_table.rowCount()
                        self.preview_table.insertRow(row_position)
                        
                        self.preview_table.setItem(row_position, 0, QTableWidgetItem(prompt))
                        self.preview_table.setItem(row_position, 1, QTableWidgetItem(resolution))
                        self.preview_table.setItem(row_position, 2, QTableWidgetItem(duration_str))
                        self.preview_table.setItem(row_position, 3, QTableWidgetItem(status))
                        
                        # 设置状态列的颜色
                        status_item = self.preview_table.item(row_position, 3)
                        if status == '有效':
                            status_item.setForeground(Qt.darkGreen)
                        else:
                            status_item.setForeground(Qt.red)
                
                # 更新创建按钮状态
                if self.tasks_data:
                    self.create_btn.setEnabled(True)
                    InfoBar.success(
                        title='成功',
                        content=f'成功解析 {len(self.tasks_data)} 个有效任务',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    self.create_btn.setEnabled(False)
                    InfoBar.warning(
                        title='警告',
                        content='没有找到有效的任务数据',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'解析CSV文件失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def get_tasks_data(self):
        """获取解析的任务数据"""
        return self.tasks_data