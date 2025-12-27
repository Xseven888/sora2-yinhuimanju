"""
小说分析线程 - 用于分析小说内容生成简介
"""

import requests
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from database_manager import db_manager
from constants import API_CHAT_COMPLETIONS_URL, API_BASE_URL


class NovelAnalysisThread(QThread):
    """小说分析线程"""
    progress = pyqtSignal(str)  # 进度消息
    finished = pyqtSignal(str)  # 分析完成，返回简介
    error = pyqtSignal(str)  # 错误消息

    def __init__(self, novel_file_path: str, parent=None):
        super().__init__(parent)
        self.novel_file_path = novel_file_path

    def run(self):
        """执行小说分析"""
        try:
            # 读取小说文件内容
            self.progress.emit("正在读取小说文件...")
            novel_content = self.read_novel_file()
            
            if not novel_content:
                self.error.emit("无法读取小说文件内容")
                return

            # 截取前5000字符（避免内容过长）
            content_preview = novel_content[:5000]
            if len(novel_content) > 5000:
                content_preview += "\n...(内容已截断)"

            # 获取API配置
            api_key = db_manager.load_config('api_key', '')
            if not api_key:
                self.error.emit("请先在设置中配置API Key")
                return

            # 获取分析模型
            analysis_model = db_manager.load_config('analysis_model', 'gemini-3-pro-preview')

            self.progress.emit(f"正在调用{analysis_model}分析小说内容...")

            # 构建提示词
            prompt = f"""请分析以下小说内容，生成一个简洁的项目简介。

要求：
1. 简介长度控制在100-200字
2. 突出小说的核心情节和主要人物
3. 语言简洁生动，吸引读者
4. 只返回简介内容，不要添加任何前缀、后缀或说明文字

小说内容：
{content_preview}
"""

            # 根据模型类型选择不同的API接口
            if 'gemini' in analysis_model.lower():
                # Gemini模型使用原生格式
                url = f"{API_BASE_URL}/v1beta/models/{analysis_model}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                }
                payload = {
                    "key": api_key,
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                }
                # Gemini使用query参数传递key
                response = requests.post(
                    url,
                    json={"contents": payload["contents"]},
                    headers=headers,
                    params={"key": api_key},
                    timeout=120
                )
            else:
                # ChatGPT模型使用标准格式
                url = API_CHAT_COMPLETIONS_URL
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": analysis_model,
                    "stream": False,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 500
                }
                response = requests.post(url, json=payload, headers=headers, timeout=120)
            
            if response.status_code != 200:
                self.error.emit(f"API调用失败: {response.status_code} - {response.text[:200]}")
                return

            # 解析响应
            result = response.json()
            description = self.extract_description(result)

            if description:
                self.finished.emit(description)
            else:
                self.error.emit("无法从API响应中提取简介内容")

        except Exception as e:
            logger.error(f"分析小说失败: {e}")
            self.error.emit(f"分析失败: {str(e)}")

    def read_novel_file(self) -> str:
        """读取小说文件内容"""
        try:
            file_path = Path(self.novel_file_path)
            if not file_path.exists():
                return ""
            
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            return ""
        except Exception as e:
            logger.error(f"读取小说文件失败: {e}")
            return ""

    def extract_description(self, response_data: dict) -> str:
        """从API响应中提取简介"""
        try:
            # 标准OpenAI格式 (ChatGPT)
            if 'choices' in response_data and len(response_data['choices']) > 0:
                choice = response_data['choices'][0]
                if 'message' in choice:
                    content = choice['message'].get('content', '')
                    if content:
                        return content.strip()
            
            # Gemini格式
            if 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate:
                    parts = candidate['content'].get('parts', [])
                    if parts and len(parts) > 0:
                        # Gemini返回的parts是数组，每个part可能有text字段
                        for part in parts:
                            if 'text' in part:
                                text = part.get('text', '')
                                if text:
                                    return text.strip()
            
            # 直接获取text字段
            if 'text' in response_data:
                return str(response_data['text']).strip()
            
            # 如果都没有，记录日志以便调试
            logger.warning(f"无法解析API响应: {response_data}")
            return ""
        except Exception as e:
            logger.error(f"提取简介失败: {e}")
            return ""

