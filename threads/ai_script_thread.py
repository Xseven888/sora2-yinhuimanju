"""
AI编剧线程 - 用于分析剧集文件生成分镜脚本
"""

import requests
import json
import re
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from database_manager import db_manager
from constants import API_CHAT_COMPLETIONS_URL, API_BASE_URL


class AIScriptThread(QThread):
    """AI编剧线程"""
    progress = pyqtSignal(str)  # 进度消息
    finished = pyqtSignal(list)  # 分析完成，返回分镜列表
    error = pyqtSignal(str)  # 错误消息

    def __init__(self, episode_id, episode_file_path, parent=None):
        super().__init__(parent)
        self.episode_id = episode_id
        self.episode_file_path = episode_file_path

    def run(self):
        """执行AI编剧分析"""
        try:
            # 读取剧集文件内容
            self.progress.emit("正在读取剧集文件...")
            episode_content = self.read_episode_file()
            
            if not episode_content:
                self.error.emit("无法读取剧集文件内容")
                return

            # 获取API配置
            api_key = db_manager.load_config('api_key', '')
            if not api_key:
                self.error.emit("请先在设置中配置API Key")
                return

            # 获取分析模型
            analysis_model = db_manager.load_config('analysis_model', 'gemini-3-pro-preview')

            self.progress.emit(f"正在调用{analysis_model}生成分镜脚本...")

            # 构建提示词（严格按照界面展示结构生成：标题、时长、脚本（文案/对白）、画面内容、镜头移动）
            prompt = f"""你是专业分镜编剧，请根据以下这一集的完整文本内容，生成 10-15 个连贯的分镜脚本。
每个分镜的结构必须能映射到界面中的以下栏目：
【标题】、【时长】、【脚本】文案/对白、【画面内容】、【镜头移动】。

具体要求：
1. 每个分镜必须包含下面 5 个字段（字段名固定，用于程序解析）：
   - title: 分镜标题（对应界面【标题】；简洁概括这一镜头的核心事件或情绪）
   - duration: 时长（对应界面【时长】；只能是 "10s" 或 "15s" 两种字符串）
   - dialogue: 脚本文案/对白（对应界面【脚本】文案/对白；需要综合写出：
       * 角色对话（标明说话角色，例如：学生A: \"......\"；老师: \"......\"）
       * 音效描述（例如：SFX: 下课铃声响起 / 操场欢呼声 / 关门声 等）
       * 系统音 / 画外音 / 旁白（例如：旁白: \"三年后的高考现场……\"）
     以上内容请用自然语言写在同一个字符串里，按时间顺序描述清楚，没有就略写或留空字符串 ""）
   - screen_content: 画面内容（对应界面【画面内容】；用详细但精炼的中文描述该分镜在屏幕上看到的场景，包括人物动作、表情、环境氛围、道具等）
   - camera_movement: 镜头移动（对应界面【镜头移动】；描述镜头语言，例如：
       固定镜头 / 推镜 / 拉镜 / 摇镜 / 跟拍 / 俯拍 / 仰拍 / POV 等，以及镜头从哪里到哪里，如何移动）

2. 分镜数量：至少 10 个，最多 15 个，按剧情发展顺序排列。
3. 每个分镜的 duration 必须是 "10s" 或 "15s"（字符串），不要写成中文。
4. 整体剧情要完整、连贯，能够从开头到结尾清晰讲完这一集的主要情节。
5. 只返回 JSON 数组，不要任何额外说明、解释或客套话，不要代码块标记。

下面是本集的全文内容（请先整体理解，再进行拆分和改写）：
{episode_content}

请严格以 JSON 数组格式返回，参考结构示例（示例仅说明结构，你需要根据上面的文本重新创作具体内容）：
[
  {{
    "title": "开学日的慌乱教室",
    "duration": "10s",
    "dialogue": "旁白: 新学期的第一天, 教室里格外嘈杂。学生A: \"你作业写完了吗?\" 学生B(慌张): \"还差一点点!\" SFX: 铃声响起。",
    "screen_content": "清晨的教室, 阳光从窗户斜射进来, 桌面上堆满试卷和练习本, 学生们一边整理书包一边交头接耳, 气氛紧张又兴奋。",
    "camera_movement": "从黑场淡入到全景, 缓慢推进到教室中部, 最后定格在一张写满公式的课桌特写上。"
  }}
]

务必只返回 JSON 数组本身，不要任何其他内容。"""

            # 根据模型类型选择不同的API接口
            if 'gemini' in analysis_model.lower():
                # Gemini模型使用原生格式
                url = f"{API_BASE_URL}/v1beta/models/{analysis_model}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                }
                payload = {
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
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    params={"key": api_key},
                    timeout=300
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
                    "max_tokens": 4000
                }
                response = requests.post(url, json=payload, headers=headers, timeout=300)
            
            if response.status_code != 200:
                self.error.emit(f"API调用失败: {response.status_code} - {response.text[:200]}")
                return

            # 解析响应
            result = response.json()
            storyboards = self.extract_storyboards(result)

            if storyboards:
                self.finished.emit(storyboards)
            else:
                self.error.emit("无法从API响应中提取分镜内容")

        except Exception as e:
            logger.error(f"AI编剧分析失败: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(f"分析失败: {str(e)}")

    def read_episode_file(self) -> str:
        """读取剧集文件内容"""
        try:
            file_path = Path(self.episode_file_path)
            if not file_path.exists():
                return ""
            
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        # 限制内容长度，避免过长
                        if len(content) > 20000:
                            content = content[:20000] + "\n...(内容已截断)"
                        return content
                except UnicodeDecodeError:
                    continue
            
            return ""
        except Exception as e:
            logger.error(f"读取剧集文件失败: {e}")
            return ""

    def extract_storyboards(self, response_data: dict) -> list:
        """从API响应中提取分镜列表"""
        try:
            text_content = ""
            
            # 标准OpenAI格式
            if 'choices' in response_data and len(response_data['choices']) > 0:
                choice = response_data['choices'][0]
                if 'message' in choice:
                    content = choice['message'].get('content', '')
                    if content:
                        text_content = content.strip()
            
            # Gemini格式
            if not text_content and 'candidates' in response_data and len(response_data['candidates']) > 0:
                candidate = response_data['candidates'][0]
                if 'content' in candidate:
                    parts = candidate['content'].get('parts', [])
                    if parts and len(parts) > 0:
                        for part in parts:
                            if 'text' in part:
                                text_content = part.get('text', '').strip()
                                break
            
            if not text_content:
                logger.warning(f"无法从API响应中提取文本内容: {response_data}")
                return []
            
            # 尝试解析JSON
            # 去除可能的代码块标记
            if '```' in text_content:
                # 提取JSON部分
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text_content, re.DOTALL)
                if json_match:
                    text_content = json_match.group(1)
                else:
                    # 尝试提取第一个 [ 到最后一个 ] 之间的内容
                    start = text_content.find('[')
                    end = text_content.rfind(']')
                    if start != -1 and end != -1:
                        text_content = text_content[start:end+1]
            
            # 解析JSON
            storyboards = json.loads(text_content)
            
            if isinstance(storyboards, list):
                # 验证每个分镜的字段
                validated_storyboards = []
                for i, sb in enumerate(storyboards):
                    if isinstance(sb, dict):
                        validated_storyboards.append({
                            'sequence_number': i + 1,
                            'title': sb.get('title', f'分镜{i+1}'),
                            'duration': sb.get('duration', '10s'),
                            'dialogue': sb.get('dialogue', ''),
                            'screen_content': sb.get('screen_content', ''),
                            'camera_movement': sb.get('camera_movement', '')
                        })
                return validated_storyboards
            
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 内容: {text_content[:500]}")
            self.error.emit(f"JSON解析失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"提取分镜失败: {e}")
            return []

