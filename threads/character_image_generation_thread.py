"""
角色图片生成线程
"""

import requests
import json
import sqlite3
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from database_manager import db_manager
from constants import API_BASE_URL
from loguru import logger


class CharacterImageGenerationThread(QThread):
    """角色图片生成线程"""
    
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(str)  # 完成信号，参数为图片路径
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, character_id, project_id, parent=None):
        super().__init__(parent)
        self.character_id = character_id
        self.project_id = project_id
        
    def run(self):
        """执行生成任务"""
        try:
            # 检查是否被请求中断
            if self.isInterruptionRequested():
                return
            # 1. 获取角色信息
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在获取角色信息...")
            character_data = self.get_character_data()
            if not character_data:
                raise RuntimeError("无法获取角色信息")
            
            character_name = character_data[0]
            character_description = character_data[1] or ""
            
            # 2. 获取项目信息（获取风格）
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在获取项目信息...")
            project_data = self.get_project_data()
            if not project_data:
                raise RuntimeError("无法获取项目信息")
            
            style = project_data[0] or ""
            
            # 3. 获取生图模型
            if self.isInterruptionRequested():
                return
            image_model = db_manager.load_config('image_model', 'gemini-3-pro-image-preview')
            
            # 4. 构建提示词
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在构建生成提示词...")
            prompt = self.build_prompt(character_name, character_description, style)
            
            # 5. 调用API生成图片
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在调用AI生成图片...")
            image_url = self.generate_image(prompt, image_model)
            
            if not image_url:
                raise RuntimeError("图片生成失败，未返回图片URL")
            
            # 6. 下载图片
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在下载生成的图片...")
            image_path = self.download_image(image_url, character_id=self.character_id)
            
            # 7. 更新数据库
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在保存图片信息...")
            self.update_character_images(image_path)
            
            if self.isInterruptionRequested():
                return
            self.progress.emit("生成完成")
            self.finished.emit(image_path)
            
        except Exception as e:
            # 如果是因为中断请求导致的，不发送错误信号
            if self.isInterruptionRequested():
                logger.info("生成任务被用户中断")
                return
            error_msg = f"生成角色图失败: {str(e)}"
            logger.error(error_msg)
            # 只有在对话框还存在时才发送错误信号
            try:
                self.error.emit(error_msg)
            except RuntimeError:
                # 如果对话框已关闭，信号接收者不存在，忽略错误
                pass
    
    def get_character_data(self):
        """获取角色数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, description
                FROM characters
                WHERE id = ?
            ''', (self.character_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"获取角色数据失败: {e}")
            return None
    
    def get_project_data(self):
        """获取项目数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT style
                FROM projects
                WHERE id = ?
            ''', (self.project_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"获取项目数据失败: {e}")
            return None
    
    def build_prompt(self, character_name, character_description, style):
        """构建生成提示词"""
        # 构建详细的提示词，要求生成9:16比例的图片，只包含正面视图
        prompt = f"""请生成一张9:16比例的图片，纯白背景，角色全身正面视图：

角色名称：{character_name}
角色特征：{character_description}

风格要求：{style if style else "日本动漫"}

重要要求：
- 图片必须是9:16比例
- 角色全身正面视图，纯白背景
- 必须使用纯色白底，不能有任何背景元素或装饰
- 不能出现任何文字、水印、标签、标识等元素
- 只能出现纯角色形象，图片中不能有任何文字内容
- 角色形象必须清晰、完整"""
        
        return prompt
    
    def generate_image(self, prompt, model):
        """调用API生成图片"""
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            raise RuntimeError("未配置API Key，请在设置中配置")
        
        # 根据模型选择不同的API端点
        if model in ['gemini-3-pro-image-preview', 'gemini-2.5-flash-image-preview']:
            # 使用Gemini原生API
            url = f"{API_BASE_URL}/v1beta/models/{model}:generateContent"
            params = {"key": api_key}
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "aspectRatio": "16:9",
                    "safetySettings": [
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "threshold": "BLOCK_NONE"
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "threshold": "BLOCK_NONE"
                        }
                    ]
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=300)
            
            if response.status_code != 200:
                raise RuntimeError(f"API调用失败: {response.status_code} - {response.text}")
            
            result = response.json()
            logger.info(f"API返回结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
            
            # 解析返回的图片数据
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "inlineData" in part:
                            # 如果是base64编码的图片数据，需要先保存
                            import base64
                            inline_data = part["inlineData"]
                            mime_type = inline_data.get("mimeType", "image/png")
                            data = inline_data.get("data", "")
                            if data:
                                image_data = base64.b64decode(data)
                                # 保存临时图片
                                temp_path = self.save_temp_image(image_data, mime_type)
                                return temp_path
                        elif "url" in part:
                            return part["url"]
                # 也可能直接在candidate中有图片数据
                if "inlineData" in candidate:
                    import base64
                    inline_data = candidate["inlineData"]
                    mime_type = inline_data.get("mimeType", "image/png")
                    data = inline_data.get("data", "")
                    if data:
                        image_data = base64.b64decode(data)
                        temp_path = self.save_temp_image(image_data, mime_type)
                        return temp_path
            
            # 如果都没有找到，记录详细日志
            logger.error(f"无法解析API返回: {json.dumps(result, ensure_ascii=False, indent=2)}")
            raise RuntimeError("API返回格式异常，未找到图片数据")
        else:
            raise RuntimeError(f"不支持的模型: {model}")
    
    def save_temp_image(self, image_data, mime_type="image/png"):
        """保存临时图片数据"""
        from datetime import datetime
        temp_dir = Path(db_manager.app_data_dir) / "temp_images"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 根据mime_type确定文件扩展名
        if "jpeg" in mime_type or "jpg" in mime_type:
            ext = ".jpg"
        elif "png" in mime_type:
            ext = ".png"
        elif "webp" in mime_type:
            ext = ".webp"
        else:
            ext = ".png"  # 默认使用png
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = temp_dir / f"character_{self.character_id}_{timestamp}{ext}"
        
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        
        return str(temp_path)
    
    def download_image(self, image_url, character_id):
        """下载图片"""
        # 如果已经是本地路径，直接返回
        if Path(image_url).exists():
            return image_url
        
        # 下载图片
        response = requests.get(image_url, timeout=300)
        if response.status_code != 200:
            raise RuntimeError(f"下载图片失败: {response.status_code}")
        
        # 保存图片
        images_dir = Path(db_manager.app_data_dir) / "character_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = images_dir / f"character_{character_id}_{timestamp}.png"
        
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        return str(image_path)
    
    def update_character_images(self, image_path):
        """更新角色图片信息"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            # 更新正面图（使用生成的图片）
            cursor.execute('''
                UPDATE characters
                SET front_image = ?
                WHERE id = ?
            ''', (image_path, self.character_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新角色图片失败: {e}")
            raise

