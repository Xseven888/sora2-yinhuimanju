"""
角色分析线程 - 用于分析小说内容提取角色信息
"""

import requests
import json
import sqlite3
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from database_manager import db_manager
from constants import API_BASE_URL, API_CHAT_COMPLETIONS_URL


class CharacterAnalysisThread(QThread):
    """角色分析线程"""
    progress = pyqtSignal(str)  # 进度消息
    finished = pyqtSignal(list)  # 分析完成，返回角色列表
    error = pyqtSignal(str)  # 错误消息

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

    def run(self):
        """执行角色分析"""
        try:
            # 获取项目信息
            self.progress.emit("正在读取项目信息...")
            project_data = self.get_project_data()
            
            if not project_data:
                self.error.emit("无法获取项目信息，请检查项目是否存在")
                return

            # 检查是否有小说文件路径
            novel_file_path = project_data.get('novel_file_path', '')
            novel_folder_path = project_data.get('novel_folder_path', '')
            
            if not novel_file_path and not novel_folder_path:
                self.error.emit("项目中没有小说文件，请先在添加项目时选择小说文件或文件夹")
                return

            # 读取小说文件内容
            self.progress.emit("正在读取小说文件...")
            novel_content = self.read_novel_file(project_data)
            
            if not novel_content:
                self.error.emit("无法读取小说文件内容，请检查文件路径是否正确")
                return

            # 截取前10000字符（避免内容过长）
            content_preview = novel_content[:10000]
            if len(novel_content) > 10000:
                content_preview += "\n...(内容已截断)"

            # 获取API配置
            api_key = db_manager.load_config('api_key', '')
            if not api_key:
                self.error.emit("请先在设置中配置API Key")
                return

            # 获取分析模型
            analysis_model = db_manager.load_config('analysis_model', 'gemini-3-pro-preview')

            self.progress.emit(f"正在调用{analysis_model}分析角色信息...")

            # 构建提示词
            prompt = f"""请分析以下小说内容，提取所有出现的人物角色信息。

要求：
1. 提取所有角色的名字
2. 对每个角色，提供详细的描述（外貌、性格、身份等）
3. 以JSON数组格式返回，每个角色包含以下字段：
   - name: 角色名字
   - description: 角色描述（至少50字）

格式示例：
[
  {{
    "name": "角色名",
    "description": "角色的详细描述，包括外貌、性格、身份等信息"
  }}
]

只返回JSON数组，不要添加任何其他说明文字。

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
                    timeout=180
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
                    "max_tokens": 2000
                }
                response = requests.post(url, json=payload, headers=headers, timeout=180)
            
            if response.status_code != 200:
                self.error.emit(f"API调用失败: {response.status_code} - {response.text[:200]}")
                return

            # 解析响应
            result = response.json()
            characters = self.extract_characters(result)

            if characters:
                # 保存角色到数据库
                self.save_characters(characters)
                self.finished.emit(characters)
            else:
                self.error.emit("无法从API响应中提取角色信息")

        except Exception as e:
            logger.error(f"分析角色失败: {e}")
            self.error.emit(f"分析失败: {str(e)}")

    def get_project_data(self):
        """获取项目数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT novel_file_path, novel_folder_path
                FROM projects
                WHERE id = ?
            ''', (self.project_id,))
            project = cursor.fetchone()
            conn.close()
            
            if project:
                return {
                    'novel_file_path': project[0] if project[0] else '',
                    'novel_folder_path': project[1] if project[1] else ''
                }
            else:
                logger.error(f"项目ID {self.project_id} 不存在于数据库中")
                return None
        except Exception as e:
            logger.error(f"获取项目数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def read_novel_file(self, project_data):
        """读取小说文件内容"""
        try:
            # 优先使用文件路径
            if project_data.get('novel_file_path'):
                file_path = Path(project_data['novel_file_path'])
                if file_path.exists():
                    return self.read_file_content(file_path)
            
            # 如果文件路径不存在，尝试文件夹
            if project_data.get('novel_folder_path'):
                folder_path = Path(project_data['novel_folder_path'])
                if folder_path.exists() and folder_path.is_dir():
                    # 读取文件夹中所有txt和md文件
                    content = ""
                    for file in folder_path.glob("*.txt"):
                        content += self.read_file_content(file) + "\n\n"
                    for file in folder_path.glob("*.md"):
                        content += self.read_file_content(file) + "\n\n"
                    return content
            
            return ""
        except Exception as e:
            logger.error(f"读取小说文件失败: {e}")
            return ""

    def read_file_content(self, file_path):
        """读取文件内容"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return ""

    def extract_characters(self, response_data):
        """从API响应中提取角色信息"""
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
                return []
            
            # 尝试解析JSON
            # 去除可能的代码块标记
            import re
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
            else:
                # 如果没有代码块标记，尝试直接提取JSON数组
                start = text_content.find('[')
                end = text_content.rfind(']')
                if start != -1 and end != -1 and start < end:
                    text_content = text_content[start:end+1]
            
            # 如果仍然没有找到JSON数组，返回空列表
            if not text_content or text_content.find('[') == -1:
                logger.warning(f"响应内容中未找到JSON数组，内容预览: {text_content[:200]}")
                return []
            
            # 解析JSON
            characters = json.loads(text_content)
            
            if isinstance(characters, list):
                return characters
            elif isinstance(characters, dict) and 'characters' in characters:
                return characters['characters']
            else:
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"解析角色JSON失败: {e}")
            logger.error(f"响应内容: {text_content[:500]}")
            return []
        except Exception as e:
            logger.error(f"提取角色失败: {e}")
            return []

    def save_characters(self, characters):
        """保存角色到数据库"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            for char in characters:
                name = char.get('name', '').strip()
                description = char.get('description', '').strip()
                
                if not name:
                    continue
                
                # 检查角色是否已存在
                cursor.execute('''
                    SELECT id FROM characters
                    WHERE project_id = ? AND name = ?
                ''', (self.project_id, name))
                
                if cursor.fetchone():
                    # 更新现有角色
                    cursor.execute('''
                        UPDATE characters
                        SET description = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE project_id = ? AND name = ?
                    ''', (description, self.project_id, name))
                else:
                    # 插入新角色
                    cursor.execute('''
                        INSERT INTO characters (project_id, name, description)
                        VALUES (?, ?, ?)
                    ''', (self.project_id, name, description))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存角色失败: {e}")
            raise

