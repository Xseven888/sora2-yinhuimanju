"""
剧本批量生成对话框：包含两步
1) ScriptParamsDialog - 输入主题、分辨率、时长、视频个数
2) ScriptListDialog   - 展示按照主题与时长生成的提示词列表，并提供逐条/全部生成视频的按钮
"""

from typing import List, Dict
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTableWidget, QTableWidgetItem,
    QWidget, QHeaderView
)
from qfluentwidgets import (
    TitleLabel, BodyLabel, LineEdit, ComboBox, SpinBox, PushButton, PrimaryPushButton,
    InfoBar, InfoBarPosition, TableWidget
)

from threads.script_generation_thread import ScriptGenerationThread
from database_manager import db_manager


class ScriptParamsDialog(QDialog):
    """剧本参数输入对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('剧本参数')
        self.setModal(True)
        self.resize(480, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(TitleLabel('输入剧本生成参数'))

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)  # type: ignore
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore

        # 主题
        self.theme_edit = LineEdit(self)
        self.theme_edit.setPlaceholderText('例如：城市夜景 vlog / 旅行短片 / 产品介绍')
        form.addRow('主题:', self.theme_edit)

        # 分辨率（仅横屏/竖屏）
        self.resolution_combo = ComboBox(self)
        self.resolution_combo.addItem('横屏 (16:9)', None, '16:9')
        self.resolution_combo.addItem('竖屏 (9:16)', None, '9:16')
        self.resolution_combo.setCurrentIndex(0)
        form.addRow('分辨率:', self.resolution_combo)

        # 时长（仅 10s/15s）
        self.duration_combo = ComboBox(self)
        for s in [10, 15]:
            self.duration_combo.addItem(f'{s} 秒', None, s)
        self.duration_combo.setCurrentIndex(0)
        form.addRow('时长:', self.duration_combo)

        # 视频个数
        self.count_spin = SpinBox(self)
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(5)
        form.addRow('视频个数:', self.count_spin)

        layout.addLayout(form)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = PushButton('取消', self)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = PrimaryPushButton('下一步', self)
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_ok(self):
        theme = self.theme_edit.text().strip()
        if not theme:
            InfoBar.warning(
                title='提示',
                content='请输入视频主题',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2200,
                parent=self
            )
            return
        self.accept()

    def get_params(self) -> Dict:
        aspect_ratio = self.resolution_combo.currentData() or '16:9'
        duration = self.duration_combo.currentData() or 15
        count = int(self.count_spin.value())
        return {
            'theme': self.theme_edit.text().strip(),
            'aspect_ratio': aspect_ratio,
            'duration': duration,
            'count': count,
        }


class ScriptListDialog(QDialog):
    """剧本列表与生成对话框"""

    def __init__(self, theme: str, aspect_ratio: str, duration: int, count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle('剧本列表')
        self.setModal(True)
        self.resize(900, 600)
        self.theme = theme
        self.aspect_ratio = aspect_ratio
        self.duration = duration
        self.count = count
        self.prompts: List[str] = []
        self._thread = None
        self._init_ui()
        self._start_generation()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 头部与说明
        header = QHBoxLayout()
        header.addWidget(TitleLabel('剧本与提示词列表'))
        header.addStretch()
        self.generate_all_btn = PrimaryPushButton('全部生成', self)
        self.generate_all_btn.clicked.connect(self._on_generate_all)
        self.generate_all_btn.setEnabled(False)
        header.addWidget(self.generate_all_btn)
        layout.addLayout(header)

        info = BodyLabel(f'主题：{self.theme} ｜ 分辨率：{self.aspect_ratio} ｜ 时长：{self.duration}s ｜ 数量：{self.count}')
        info.setStyleSheet('color:#666;')
        layout.addWidget(info)

        # 表格
        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['序号', '提示词', '操作'])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        vh = self.table.verticalHeader()
        vh.setVisible(False)
        vh.setDefaultSectionSize(36)
        # 单行显示，避免多行换行
        try:
            self.table.setWordWrap(False)
        except Exception:
            pass
        layout.addWidget(self.table)

        # 底部按钮
        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = PushButton('关闭', self)
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        # 初始列宽设置（1:7:2）
        self._update_table_column_widths()

    def _start_generation(self):
        try:
            api_key = db_manager.load_config('api_key', '') or ''
            if not api_key:
                InfoBar.error(
                    title='错误',
                    content='请先在设置中配置API Key',
                    orient=Qt.Horizontal,  # type: ignore
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2600,
                    parent=self
                )
                return

            self._thread = ScriptGenerationThread(
                api_key=api_key,
                theme=self.theme,
                aspect_ratio=self.aspect_ratio,
                duration=self.duration,
                count=self.count
            )
            self._thread.prompt_ready.connect(self._on_prompt_ready)
            self._thread.finished.connect(self._on_generation_finished)
            self._thread.error.connect(self._on_generation_error)
            self._thread.start()

            InfoBar.info(
                title='生成中',
                content='正在生成剧本与提示词…',
                orient=Qt.Horizontal,  # type: ignore
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1800,
                parent=self
            )
        except Exception as e:
            self._on_generation_error(str(e))

    def _on_prompt_ready(self, index: int, prompt: str):
        self.prompts.append(prompt)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(index + 1)))
        self.table.setItem(row, 1, QTableWidgetItem(self._preview_text(prompt)))

        # 操作列按钮
        op_btn = PushButton('生成', self)
        try:
            op_btn.setFixedHeight(28)
            op_btn.setFixedWidth(88)
        except Exception:
            pass
        op_btn.clicked.connect(lambda: self._on_generate_single(prompt))
        self.table.setCellWidget(row, 2, op_btn)

        # 保持列宽比例
        self._update_table_column_widths()

    def _on_generation_finished(self):
        self.generate_all_btn.setEnabled(bool(self.prompts))
        InfoBar.success(
            title='完成',
            content='剧本生成完成',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1600,
            parent=self
        )

    def _on_generation_error(self, message: str):
        InfoBar.error(
            title='错误',
            content=f'剧本生成失败：{message}',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2600,
            parent=self
        )

    def _on_generate_single(self, prompt: str):
        parent = self.parent()
        if parent and hasattr(parent, 'generate_video'):
            try:
                parent.generate_video({
                    'prompt': prompt,
                    'model': 'sora-2',
                    'duration': self.duration,
                    'images': [],
                    'aspect_ratio': self.aspect_ratio
                })
            except Exception as e:
                self._on_generation_error(str(e))

    def _on_generate_all(self):
        parent = self.parent()
        if not self.prompts:
            return
        if parent and hasattr(parent, 'generate_video'):
            for prompt in self.prompts:
                try:
                    parent.generate_video({
                        'prompt': prompt,
                        'model': 'sora-2',
                        'duration': self.duration,
                        'images': [],
                        'aspect_ratio': self.aspect_ratio
                    })
                except Exception as e:
                    self._on_generation_error(str(e))
        InfoBar.info(
            title='开始生成',
            content='已触发全部生成',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1600,
            parent=self
        )

    def _update_table_column_widths(self):
        # 设置列宽比例 1:7:2（提示词更宽，操作列正常）
        total = max(self.table.viewport().width(), 1)
        c0 = int(total * 0.1)
        c1 = int(total * 0.7)
        c2 = total - c0 - c1
        self.table.setColumnWidth(0, max(c0, 60))
        self.table.setColumnWidth(1, max(c1, 360))
        self.table.setColumnWidth(2, max(c2, 120))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_table_column_widths()

    def _preview_text(self, prompt: str) -> str:
        # 将多行提示词压缩为单行预览，提升可读性
        lines = [l.strip() for l in prompt.splitlines() if l.strip()]
        one_line = ' | '.join(lines)
        if len(one_line) > 260:
            return one_line[:257] + '…'
        return one_line
