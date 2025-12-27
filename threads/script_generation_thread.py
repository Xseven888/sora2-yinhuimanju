"""
脚本/提示词生成线程
根据主题、分辨率(横/竖屏)、时长，调用 gpt-5-chat-latest 生成适合文生视频的提示词。
会按视频个数循环生成，逐条通过信号返回。
"""

from typing import List
import json
import requests
from constants import API_CHAT_COMPLETIONS_URL
from PyQt5.QtCore import QThread, pyqtSignal
from database_manager import db_manager


class ScriptGenerationThread(QThread):
    prompt_ready = pyqtSignal(int, str)  # index, prompt
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, api_key: str, theme: str, aspect_ratio: str, duration: int, count: int):
        super().__init__()
        self.api_key = api_key
        self.theme = theme
        self.aspect_ratio = aspect_ratio
        self.duration = duration
        self.count = count
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            base_url = API_CHAT_COMPLETIONS_URL
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            # 写死提示词，强制仅以JSON数组返回（与视频克隆分析一致的字段）
            default_scene = (
                '你是视频脚本生成助手。仅以JSON数组返回，不要任何额外说明或客套话。示例：\n'
                '[{"time": "00:00-00:05", "content": "镜头掠过城市夜景", "style": "冷色调、快剪", "narration": "开场解说", "dialogue": "", "audio": "低沉电子乐"}]\n'
                '请根据主题生成 {duration} 秒左右的视频脚本，分镜为 2–3 段；分辨率比例为 {aspect_ratio}（横屏16:9或竖屏9:16）。\n'
                'JSON数组的每个元素必须包含字段：time（如 00:00-00:05）、content、style、narration、dialogue、audio。\n'
                '仅以JSON数组返回，不要代码块标记、不要语言标签、不要任何解释。'
            )
            scene_prompt = default_scene + (
                '\n'
                'time(时间或时间段)、content(内容)、style(风格)、narration(旁白)、dialogue(人物对话)、audio(音频/音乐)。\n'
                '仅以JSON数组返回，不要任何额外说明或客套话。示例：\n'
                '[{"time": "00:00-00:05", "content": "镜头掠过城市夜景", "style": "冷色调、快剪", '
                '"narration": "开场解说", "dialogue": "", "audio": "低沉电子乐"}]'
            )
            # 替换占位符
            scene_prompt = scene_prompt.replace('{aspect_ratio}', self.aspect_ratio).replace('{duration}', str(self.duration))

            for i in range(self.count):
                if not self._running:
                    break
                payload = {
                    'model': 'gpt-5-chat-latest',
                    'stream': False,
                    'messages': [
                        {
                            'role': 'system',
                            'content': [{'type': 'text', 'text': scene_prompt}]
                        },
                        {
                            'role': 'user',
                            'content': [{'type': 'text', 'text': f'主题：{self.theme}\n分辨率：{self.aspect_ratio}\n时长：{self.duration}秒'}]
                        }
                    ]
                }

                resp = requests.post(base_url, json=payload, headers=headers, timeout=60)
                if resp.status_code != 200:
                    self.error.emit(f'提示词生成失败: {resp.status_code} - {resp.text}')
                    continue
                j = resp.json()
                prompt_text = ''
                try:
                    choices = j.get('choices') or []
                    if choices:
                        msg = choices[0].get('message') or {}
                        content = msg.get('content')
                        if isinstance(content, str):
                            prompt_text = content.strip()
                        elif isinstance(content, list):
                            texts: List[str] = []
                            for part in content:
                                if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str):
                                    texts.append(part['text'])
                            prompt_text = '\n'.join([t.strip() for t in texts if t and isinstance(t, str)])
                        else:
                            t = msg.get('text')
                            if isinstance(t, str) and t.strip():
                                prompt_text = t.strip()
                    if not prompt_text and isinstance(j.get('output_text'), str):
                        prompt_text = j['output_text'].strip()
                except Exception:
                    pass

                # 解析JSON数组，转换为最终提示词文本（视频克隆格式）
                final_prompt = ''
                if prompt_text:
                    try:
                        s = prompt_text.strip()
                        # 去除可能的代码块包裹
                        if '```' in s:
                            # 截取第一个'['到最后一个']'之间的内容
                            l = s.find('[')
                            r = s.rfind(']')
                            if l != -1 and r != -1 and r > l:
                                s = s[l:r+1]
                        # 加载JSON数组
                        data = json.loads(s)
                        if isinstance(data, list) and data:
                            blocks: List[str] = []
                            for item in data:
                                try:
                                    time_s = item.get('time', '')
                                    content_s = item.get('content', '')
                                    style_s = item.get('style') or ''
                                    narration_s = item.get('narration') or ''
                                    dialogue_s = item.get('dialogue') or ''
                                    audio_s = item.get('audio') or ''
                                    lines: List[str] = []
                                    lines.append(f'时间: {time_s}')
                                    lines.append(f'内容: {content_s}')
                                    if style_s:
                                        lines.append(f'风格: {style_s}')
                                    if narration_s:
                                        lines.append(f'旁白: {narration_s}')
                                    if dialogue_s:
                                        lines.append(f'人物对话: {dialogue_s}')
                                    if audio_s:
                                        lines.append(f'音频/音乐: {audio_s}')
                                    blocks.append('\n'.join(lines))
                                except Exception:
                                    continue
                            final_prompt = '\n\n'.join(blocks)
                    except Exception:
                        # 如果JSON解析失败，则直接使用原始文本
                        final_prompt = prompt_text

                if final_prompt:
                    self.prompt_ready.emit(i, final_prompt)
                else:
                    self.error.emit('提示词解析失败')

            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
