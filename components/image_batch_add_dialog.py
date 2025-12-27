"""
拖拽图片批量添加生成任务对话框
新增：导入表格、下载模板按钮。支持CSV导入包含：图片路径/URL、提示词、分辨率(16:9|9:16)、时长(10|15)。
"""

from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QFileDialog
)
import csv
from qfluentwidgets import (
    TitleLabel, BodyLabel, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition,
    TableWidget, ComboBox
)

from threads.image_upload_thread import ImageUploadThread
from utils.global_thread_pool import global_thread_pool


class ImageBatchAddDialog(QDialog):
    """批量添加生成任务（拖拽图片）"""

    def __init__(self, parent=None, default_prompt: str = "", default_resolution: str = "16:9", default_duration: int = 10):
        super().__init__(parent)
        self.setWindowTitle("批量添加生成任务（拖拽图片）")
        self.setModal(True)
        self.resize(860, 620)
        self._default_prompt = default_prompt or ""
        self._default_resolution = default_resolution if default_resolution in ("16:9", "9:16") else "16:9"
        self._default_duration = default_duration if default_duration in (10, 15) else 10
        self._upload_threads = []
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = TitleLabel("将图片拖拽到对话框任意位置以添加任务记录")
        layout.addWidget(title)

        desc = BodyLabel("每张图片会生成一条记录，支持编辑提示词；每行可单独选择分辨率与时长，也可批量应用设置")
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        # 模板与导入按钮区域
        template_layout = QHBoxLayout()
        self.import_csv_btn = PushButton("导入表格")
        self.import_csv_btn.clicked.connect(self.import_csv_file)
        template_layout.addWidget(self.import_csv_btn)

        self.download_template_btn = PushButton("下载模板")
        self.download_template_btn.clicked.connect(self.download_template)
        template_layout.addWidget(self.download_template_btn)
        template_layout.addStretch()
        layout.addLayout(template_layout)

        # 选项区域（分辨率/时长）
        opts = QHBoxLayout()
        res_label = BodyLabel("分辨率：")
        opts.addWidget(res_label)
        self.resolution_combo = ComboBox()
        self.resolution_combo.addItems(["16:9", "9:16"]) 
        self.resolution_combo.setCurrentText(self._default_resolution)
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        opts.addWidget(self.resolution_combo)

        dur_label = BodyLabel("时长：")
        opts.addWidget(dur_label)
        self.duration_combo = ComboBox()
        self.duration_combo.addItems(["10", "15"]) 
        self.duration_combo.setCurrentText(str(self._default_duration))
        self.duration_combo.currentTextChanged.connect(self.on_duration_changed)
        opts.addWidget(self.duration_combo)
        
        # 应用到所有记录按钮
        self.apply_all_btn = PushButton("应用到所有行")
        self.apply_all_btn.clicked.connect(self.apply_options_to_all_rows)
        opts.addWidget(self.apply_all_btn)
        opts.addStretch()
        layout.addLayout(opts)

        # 表格
        self.table = TableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["图片URL", "提示词", "分辨率", "时长(秒)", "状态"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # 按钮栏
        btns = QHBoxLayout()
        btns.addStretch()
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)

        self.ok_btn = PrimaryPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        btns.addWidget(self.ok_btn)
        layout.addLayout(btns)

    def download_template(self):
        """下载CSV模板：image_path,prompt,resolution,duration"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "保存模板", "batch_template.csv", "CSV Files (*.csv)")
            if not file_path:
                return
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["image_path", "prompt", "resolution", "duration"])
                writer.writerow(["/path/to/image1.jpg", "示例提示词：产品白底图短视频脚本", "16:9", "10"])
                writer.writerow(["https://example.com/image2.png", "示例提示词：竖屏风格展示", "9:16", "15"])
            InfoBar.success(
                title='成功',
                content='模板已保存',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'保存模板失败: {e}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def import_csv_file(self):
        """导入CSV：image_path,prompt,resolution,duration"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择CSV文件", "", "CSV Files (*.csv)")
            if not file_path:
                return
            count = 0
            rows = self._read_csv_rows_with_fallback(file_path)
            for row in rows:
                image_path = (row.get('image_path') or '').strip()
                prompt = (row.get('prompt') or '').strip()
                resolution = (row.get('resolution') or '').strip()
                duration_str = (row.get('duration') or '').strip()
                if not image_path:
                    try:
                        duration = int(duration_str) if duration_str else self._default_duration
                    except Exception:
                        duration = self._default_duration
                    if resolution not in ("16:9", "9:16"):
                        resolution = self._default_resolution
                    self._append_row_no_image(prompt=prompt, resolution=resolution, duration=duration)
                    count += 1
                    continue
                if resolution not in ("16:9", "9:16"):
                    resolution = self._default_resolution
                try:
                    duration = int(duration_str) if duration_str else self._default_duration
                except Exception:
                    duration = self._default_duration

                if image_path.startswith('http://') or image_path.startswith('https://'):
                    self._append_row_direct(url=image_path, prompt=prompt, resolution=resolution, duration=duration)
                    count += 1
                else:
                    self._append_row_for_file(image_path)
                    last_row = self.table.rowCount() - 1
                    self.table.setItem(last_row, 1, QTableWidgetItem(prompt))
                    res_widget = self.table.cellWidget(last_row, 2)
                    dur_widget = self.table.cellWidget(last_row, 3)
                    if res_widget and hasattr(res_widget, 'setCurrentText'):
                        res_widget.setCurrentText(resolution)
                    if dur_widget and hasattr(dur_widget, 'setCurrentText'):
                        dur_widget.setCurrentText(str(duration))
                    self._upload_image(image_path)
                    count += 1

            InfoBar.success(
                title='成功',
                content=f'已导入 {count} 条记录',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'导入失败: {e}',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _append_row_direct(self, url: str, prompt: str, resolution: str, duration: int):
        """直接追加一行（已上传URL）"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(url))
        self.table.setItem(row, 1, QTableWidgetItem(prompt))
        # 分辨率下拉
        res_combo = ComboBox()
        res_combo.addItems(["16:9", "9:16"]) 
        res_combo.setCurrentText(resolution if resolution in ("16:9", "9:16") else self._default_resolution)
        self.table.setCellWidget(row, 2, res_combo)
        # 时长下拉
        dur_combo = ComboBox()
        dur_combo.addItems(["10", "15"]) 
        dur_combo.setCurrentText(str(duration if duration in (10, 15) else self._default_duration))
        self.table.setCellWidget(row, 3, dur_combo)
        status_item = QTableWidgetItem("已上传")
        status_item.setForeground(Qt.darkGreen)
        self.table.setItem(row, 4, status_item)

    def _append_row_no_image(self, prompt: str, resolution: str, duration: int):
        """追加一行（不含图片，纯文本任务）"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        # 图片URL留空
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(prompt))
        # 分辨率下拉
        res_combo = ComboBox()
        res_combo.addItems(["16:9", "9:16"]) 
        res_combo.setCurrentText(resolution if resolution in ("16:9", "9:16") else self._default_resolution)
        self.table.setCellWidget(row, 2, res_combo)
        # 时长下拉
        dur_combo = ComboBox()
        dur_combo.addItems(["10", "15"]) 
        dur_combo.setCurrentText(str(duration if duration in (10, 15) else self._default_duration))
        self.table.setCellWidget(row, 3, dur_combo)
        # 状态
        status_item = QTableWidgetItem("未提供图片")
        status_item.setForeground(Qt.darkYellow)
        self.table.setItem(row, 4, status_item)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        event.acceptProposedAction()
        count = 0
        file_paths: list[str] = []
        for url in urls:
            fp = url.toLocalFile()
            if fp:
                file_paths.append(fp)
        for fp in file_paths:
            if self._is_image_file(fp):
                self._append_row_for_file(fp)
                self._upload_image(fp)
                count += 1
        if count > 0:
            InfoBar.info(
                title='添加图片',
                content=f'已添加 {count} 张图片，开始上传...',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _append_row_for_file(self, file_path: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # 图片URL列先显示本地路径或占位
        self.table.setItem(row, 0, QTableWidgetItem(Path(file_path).name))
        # 提示词默认
        self.table.setItem(row, 1, QTableWidgetItem(self._default_prompt))
        # 分辨率下拉
        res_combo = ComboBox()
        res_combo.addItems(["16:9", "9:16"]) 
        res_combo.setCurrentText(self._default_resolution)
        self.table.setCellWidget(row, 2, res_combo)
        
        # 时长下拉
        dur_combo = ComboBox()
        dur_combo.addItems(["10", "15"]) 
        dur_combo.setCurrentText(str(self._default_duration))
        self.table.setCellWidget(row, 3, dur_combo)
        # 状态
        status_item = QTableWidgetItem("上传中")
        status_item.setForeground(Qt.darkBlue)
        self.table.setItem(row, 4, status_item)

    def _upload_image(self, file_path: str):
        token = "1c17b11693cb5ec63859b091c5b9c1b2"  # 与单任务上传一致的预设token
        thread = ImageUploadThread(file_path, token)
        thread.progress.connect(lambda msg: None)
        # 闭包捕获行索引
        row_index = self.table.rowCount() - 1
        thread.finished.connect(lambda success, message, url: self._on_upload_finished(row_index, success, message, url))
        global_thread_pool.submit(thread)
        self._upload_threads.append(thread)

    def _on_upload_finished(self, row: int, success: bool, message: str, image_url: str):
        if row < 0 or row >= self.table.rowCount():
            return
        if success and image_url:
            self.table.setItem(row, 0, QTableWidgetItem(image_url))
            status_item = QTableWidgetItem("已上传")
            status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 4, status_item)
        else:
            status_item = QTableWidgetItem(f"上传失败: {message}")
            status_item.setForeground(Qt.red)
            self.table.setItem(row, 4, status_item)

    def _is_image_file(self, file_path: str) -> bool:
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
        return Path(file_path).suffix.lower() in image_extensions

    def on_resolution_changed(self, text: str):
        if text in ("16:9", "9:16"):
            self._default_resolution = text

    def on_duration_changed(self, text: str):
        try:
            val = int(text)
            if val in (10, 15):
                self._default_duration = val
        except Exception:
            pass

    def apply_options_to_all_rows(self):
        rows = self.table.rowCount()
        for r in range(rows):
            res_widget = self.table.cellWidget(r, 2)
            dur_widget = self.table.cellWidget(r, 3)
            if res_widget and hasattr(res_widget, 'setCurrentText'):
                res_widget.setCurrentText(self._default_resolution)
            if dur_widget and hasattr(dur_widget, 'setCurrentText'):
                dur_widget.setCurrentText(str(self._default_duration))

    def get_tasks_data(self) -> list[dict]:
        """从表格收集任务数据"""
        tasks = []
        rows = self.table.rowCount()
        for r in range(rows):
            url_item = self.table.item(r, 0)
            prompt_item = self.table.item(r, 1)
            res_widget = self.table.cellWidget(r, 2)
            dur_widget = self.table.cellWidget(r, 3)
            status_item = self.table.item(r, 4)

            image_url = url_item.text().strip() if url_item else ""
            prompt = (prompt_item.text().strip() if prompt_item else "")
            resolution = "16:9"
            if res_widget and hasattr(res_widget, 'currentText'):
                resolution = res_widget.currentText().strip()
            duration_str = str(self._default_duration)
            if dur_widget and hasattr(dur_widget, 'currentText'):
                duration_str = dur_widget.currentText().strip()
            status = status_item.text() if status_item else ""

            # 支持两类任务：
            # 1) 图生视频：图片URL存在且已上传成功
            # 2) 文生视频：无图片URL但提供了提示词
            include_row = False
            images_list = []
            if image_url and status.startswith("已上传"):
                include_row = True
                images_list = [image_url]
            elif (not image_url) and prompt:
                include_row = True
                images_list = []

            if include_row:
                try:
                    duration = int(duration_str)
                except Exception:
                    duration = self._default_duration
                if resolution not in ("16:9", "9:16"):
                    resolution = self._default_resolution

                tasks.append({
                    'prompt': prompt,
                    'resolution': resolution,
                    'duration': duration,
                    'images': images_list
                })

        return tasks

    def _read_csv_rows_with_fallback(self, file_path: str) -> list[dict]:
        encodings = [
            'utf-8-sig',
            'utf-8',
            'gbk',
            'gb2312',
            'big5',
            'latin-1'
        ]
        last_err = None
        for enc in encodings:
            try:
                with open(file_path, 'r', newline='', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            except Exception as e:
                last_err = e
                continue
        raise last_err if last_err else Exception('无法读取CSV文件')
