"""
场景图生成线程
"""

import requests
import json
import sqlite3
import base64
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from database_manager import db_manager
from constants import API_BASE_URL
from loguru import logger


class SceneImageGenerationThread(QThread):
    """场景图生成线程"""
    
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(int, str)  # 完成信号，参数为(storyboard_id, 图片路径)
    error = pyqtSignal(int, str)  # 错误信号，参数为(storyboard_id, 错误信息)
    
    def __init__(self, storyboard_id, project_id, parent=None):
        super().__init__(parent)
        self.storyboard_id = storyboard_id
        self.project_id = project_id
        
    def run(self):
        """执行生成任务"""
        try:
            # 检查是否被请求中断
            if self.isInterruptionRequested():
                return
            
            # 1. 获取分镜信息
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在获取分镜信息...")
            storyboard_data = self.get_storyboard_data()
            if not storyboard_data:
                raise RuntimeError("无法获取分镜信息")
            
            screen_content = storyboard_data[0] if storyboard_data[0] is not None else ""
            # 去除空白字符后检查
            screen_content = screen_content.strip() if screen_content else ""
            logger.info(f"分镜ID {self.storyboard_id} 的画面内容: {screen_content[:100] if screen_content else '(空)'}")
            
            if not screen_content:
                raise RuntimeError("分镜详情中没有画面内容")
            
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
            prompt = self.build_prompt(screen_content, style)
            
            # 5. 调用API生成图片
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在调用AI生成图片...")
            image_path = self.generate_image(prompt, image_model)
            
            if not image_path:
                raise RuntimeError("图片生成失败，未返回图片路径")
            
            # 6. 更新数据库
            if self.isInterruptionRequested():
                return
            self.progress.emit("正在保存图片信息...")
            self.update_storyboard_image(image_path)
            
            if self.isInterruptionRequested():
                return
            self.progress.emit("生成完成")
            self.finished.emit(self.storyboard_id, image_path)
            
        except Exception as e:
            # 如果是因为中断请求导致的，不发送错误信号
            if self.isInterruptionRequested():
                logger.info("生成任务被用户中断")
                return
            error_msg = f"生成场景图失败: {str(e)}"
            logger.error(error_msg)
            try:
                self.error.emit(self.storyboard_id, error_msg)
            except RuntimeError:
                # 如果接收者不存在，忽略错误
                pass
    
    def get_storyboard_data(self):
        """获取分镜数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT screen_content
                FROM storyboards
                WHERE id = ?
            ''', (self.storyboard_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"获取分镜数据失败: {e}")
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
    
    def build_prompt(self, screen_content, style):
        """构建生成提示词"""
        # 构建详细的提示词，要求生成16:9比例的纯场景图片，不能出现人物
        prompt = f"""请根据以下画面内容生成一张16:9比例的纯场景图片：

画面内容：{screen_content}

风格要求：{style if style else "写实风格"}

重要要求：
- 图片必须是16:9比例
- 只能出现场景，不能出现任何人物、角色、角色形象
- 场景要完整、清晰，符合画面内容的描述
- 风格要与项目风格一致：{style if style else "写实风格"}
- 图片中不能有任何文字、水印、标签、标识等元素
- 场景要美观、有氛围感，适合作为视频背景"""
        
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
                            inline_data = part["inlineData"]
                            mime_type = inline_data.get("mimeType", "image/png")
                            data = inline_data.get("data", "")
                            if data:
                                image_data = base64.b64decode(data)
                                # 保存图片
                                image_path = self.save_image(image_data, mime_type)
                                return image_path
                        elif "url" in part:
                            # 如果是URL，下载图片
                            image_path = self.download_image(part["url"])
                            return image_path
                # 也可能直接在candidate中有图片数据
                if "inlineData" in candidate:
                    inline_data = candidate["inlineData"]
                    mime_type = inline_data.get("mimeType", "image/png")
                    data = inline_data.get("data", "")
                    if data:
                        image_data = base64.b64decode(data)
                        image_path = self.save_image(image_data, mime_type)
                        return image_path
            
            # 如果都没有找到，记录详细日志
            logger.error(f"无法解析API返回: {json.dumps(result, ensure_ascii=False, indent=2)}")
            raise RuntimeError("API返回格式异常，未找到图片数据")
        else:
            raise RuntimeError(f"不支持的模型: {model}")
    
    def save_image(self, image_data, mime_type="image/png"):
        """保存图片数据"""
        # 根据mime_type确定文件扩展名
        if "jpeg" in mime_type or "jpg" in mime_type:
            ext = ".jpg"
        elif "png" in mime_type:
            ext = ".png"
        elif "webp" in mime_type:
            ext = ".webp"
        else:
            ext = ".png"  # 默认使用png
        
        # 保存到场景图目录
        images_dir = Path(db_manager.app_data_dir) / "scene_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = images_dir / f"scene_{self.storyboard_id}_{timestamp}{ext}"
        
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        return str(image_path)
    
    def download_image(self, image_url):
        """下载图片"""
        # 下载图片
        response = requests.get(image_url, timeout=300)
        if response.status_code != 200:
            raise RuntimeError(f"下载图片失败: {response.status_code}")
        
        # 保存图片
        images_dir = Path(db_manager.app_data_dir) / "scene_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = images_dir / f"scene_{self.storyboard_id}_{timestamp}.png"
        
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        return str(image_path)
    
    def update_storyboard_image(self, image_path):
        """更新分镜场景图信息"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            # 更新场景图路径
            cursor.execute('''
                UPDATE storyboards
                SET thumbnail_path = ?
                WHERE id = ?
            ''', (image_path, self.storyboard_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新分镜场景图失败: {e}")
            raise

