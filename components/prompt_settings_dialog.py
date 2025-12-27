"""
提示词设置对话框

包含两个多行输入框：主图处理提示词、场景生成提示词。
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TitleLabel, BodyLabel, TextEdit, PushButton, PrimaryPushButton, InfoBar, InfoBarPosition
from database_manager import db_manager


class PromptSettingsDialog(QDialog):
    """提示词设置对话框"""

    def __init__(self, initial_main_prompt: str = '', initial_scene_prompt: str = '', parent=None):
        super().__init__(parent)
        self.setWindowTitle('提示词设置')
        self.resize(640, 520)
        # 从数据库加载，如传入初始值为空则使用数据库值；数据库缺省时使用本地默认
        default_main = (
            '根据提供的商品主图生成标准电商白底图：\n'
            '- 背景：纯白(#FFFFFF)，干净无纹理；\n'
            '- 主体：保持原始外观与质感，不改变颜色与结构；\n'
            '- 抠图：边缘干净无锯齿，无残留背景；\n'
            '- 光线：均匀柔和，无明显阴影或色偏；\n'
            '- 构图：产品居中，适度留白，画面整洁；\n'
            '- 分辨率：至少 2048×2048；\n'
            '- 输出：PNG(透明背景)或JPEG(白底)，适合电商展示。'
        )
        default_scene = (
            '请基于白底图与商品标题生成一个 15 秒的产品介绍视频脚本与镜头计划。要求：\n'
            '1) 产品简短描述与核心卖点(中文)。\n'
            '2) 旁白文案(中文、自然口语，节奏紧凑)。\n'
            '3) 背景音乐风格：轻快现代，音量不压旁白。\n'
            '4) 运镜设计：推进/摇移/环绕等，流畅自然。\n'
            '5) 时间轴划分为 2–3 个镜头，每个镜头标注【时长/画面内容/镜头运动/旁白/字幕】。\n'
            '6) 画面以白底图为核心，可加入品牌色点缀。\n'
            '7) 结尾包含行动号召(如“立即了解/购买”)。\n'
            '总时长严格控制在 15 秒。\n'
            '请按如下格式输出：\n'
            'Shot 1（0–5s）：画面内容…｜镜头运动…｜旁白…｜字幕…\n'
            'Shot 2（5–10s）：…\n'
            'Shot 3（10–15s）：…'
        )

        db_main = db_manager.load_config('main_image_prompt', default_main)
        db_scene = db_manager.load_config('scene_generation_prompt', default_scene)
        self._main_prompt = initial_main_prompt or db_main or default_main
        self._scene_prompt = initial_scene_prompt or db_scene or default_scene
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel('提示词设置'))

        # 主图处理提示词
        layout.addWidget(BodyLabel('主图处理提示词'))
        self.main_prompt_edit = TextEdit(self)
        self.main_prompt_edit.setPlaceholderText('请输入用于主图处理的提示词（支持多行）')
        self.main_prompt_edit.setMinimumHeight(160)
        self.main_prompt_edit.setText(self._main_prompt)
        layout.addWidget(self.main_prompt_edit)

        # 场景生成提示词
        layout.addWidget(BodyLabel('场景生成提示词'))
        self.scene_prompt_edit = TextEdit(self)
        self.scene_prompt_edit.setPlaceholderText('请输入用于场景生成的提示词（支持多行）')
        self.scene_prompt_edit.setMinimumHeight(160)
        self.scene_prompt_edit.setText(self._scene_prompt)
        layout.addWidget(self.scene_prompt_edit)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = PushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.ok_btn = PrimaryPushButton('确定')
        self.ok_btn.clicked.connect(self.on_confirm)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def on_confirm(self):
        self._main_prompt = self.main_prompt_edit.toPlainText().strip()
        self._scene_prompt = self.scene_prompt_edit.toPlainText().strip()
        # 保存到数据库配置表
        try:
            db_manager.save_config('main_image_prompt', self._main_prompt, 'string', '主图处理提示词(白底图生成)')
            db_manager.save_config('scene_generation_prompt', self._scene_prompt, 'string', '场景生成提示词(15秒产品介绍)')
        except Exception:
            pass
        InfoBar.success(
            title='已保存',
            content='提示词设置已保存',
            orient=Qt.Horizontal,  # type: ignore
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1600,
            parent=self
        )
        self.accept()

    def get_main_prompt(self) -> str:
        return self._main_prompt

    def get_scene_prompt(self) -> str:
        return self._scene_prompt
