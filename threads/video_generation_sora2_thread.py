"""
Sora2视频生成线程
"""

import sqlite3
from PyQt5.QtCore import QThread, pyqtSignal
from database_manager import db_manager
from sora_client import SoraClient
from utils.oss_uploader import OSSUploader
from loguru import logger


class VideoGenerationSora2Thread(QThread):
    """Sora2视频生成线程"""
    
    progress = pyqtSignal(int, str)  # 进度信号，参数为(storyboard_id, 消息)
    finished = pyqtSignal(int, str)  # 完成信号，参数为(storyboard_id, task_id)
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
            self.progress.emit(self.storyboard_id, "正在获取分镜信息...")
            storyboard_data = db_manager.get_storyboard_by_id(self.storyboard_id)
            if not storyboard_data:
                raise RuntimeError("无法获取分镜信息")
            
            # 检查必要字段
            thumbnail_path = storyboard_data.get('thumbnail_path')
            prompt = storyboard_data.get('prompt')
            
            if not thumbnail_path:
                raise RuntimeError("分镜没有场景图，无法生成视频")
            
            if not prompt:
                raise RuntimeError("分镜没有提示词，无法生成视频")
            
            # 2. 获取项目信息（用于确定视频方向）
            if self.isInterruptionRequested():
                return
            self.progress.emit(self.storyboard_id, "正在获取项目信息...")
            project_data = self.get_project_data()
            if not project_data:
                raise RuntimeError("无法获取项目信息")
            
            video_aspect_ratio = project_data.get('video_aspect_ratio', '16:9')
            orientation = 'landscape' if video_aspect_ratio == '16:9' else 'portrait'
            
            # 3. 上传场景图到OSS（如果需要）
            if self.isInterruptionRequested():
                return
            self.progress.emit(self.storyboard_id, "正在上传场景图...")
            image_url = self.upload_image_to_oss(thumbnail_path)
            if not image_url:
                raise RuntimeError("上传场景图失败")
            
            # 4. 获取API密钥
            if self.isInterruptionRequested():
                return
            self.progress.emit(self.storyboard_id, "正在创建视频任务...")
            api_key = db_manager.load_config('api_key', '')
            if not api_key:
                raise RuntimeError("未设置API密钥")
            
            # 5. 创建Sora2客户端并提交视频生成任务
            sora_client = SoraClient(api_key=api_key)
            
            # 解析时长
            duration_str = storyboard_data.get('duration', '10s')
            duration = 10
            if '15' in duration_str:
                duration = 15
            
            # 调用API创建视频任务
            result = sora_client.create_video_with_image(
                images=[image_url],
                prompt=prompt,
                model="sora-2",
                orientation=orientation,
                size="small",
                duration=duration,
                watermark=False
            )
            
            # 6. 获取任务ID并保存到数据库
            task_id = result.get('id')
            if not task_id:
                raise RuntimeError("API返回的任务ID为空")
            
            # 更新数据库
            db_manager.update_storyboard_video_info(
                storyboard_id=self.storyboard_id,
                video_task_id=task_id,
                video_status='生成中'
            )
            
            self.finished.emit(self.storyboard_id, task_id)
            
        except Exception as e:
            logger.error(f"生成视频失败 (分镜ID: {self.storyboard_id}): {e}")
            self.error.emit(self.storyboard_id, str(e))
    
    def get_project_data(self):
        """获取项目数据"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT aspect_ratio
                FROM projects
                WHERE id = ?
            ''', (self.project_id,))
            project = cursor.fetchone()
            conn.close()
            
            if project:
                return {
                    'video_aspect_ratio': project[0] if project[0] else '16:9'
                }
            return None
        except Exception as e:
            logger.error(f"获取项目数据失败: {e}")
            return None
    
    def upload_image_to_oss(self, image_path):
        """上传图片到OSS"""
        try:
            # 获取OSS配置
            bucket_domain = db_manager.load_config('oss_bucket_domain', '')
            if not bucket_domain:
                logger.warning("OSS未配置，无法上传图片")
                return None
            
            # 创建OSS上传器
            oss_uploader = OSSUploader(bucket_domain)
            
            # 上传图片
            image_url = oss_uploader.upload_image(image_path)
            return image_url
        except Exception as e:
            logger.error(f"上传图片到OSS失败: {e}")
            return None

