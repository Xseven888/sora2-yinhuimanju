"""
视频生成工作线程
"""

from PyQt5.QtCore import QThread, pyqtSignal
from sora_client import SoraClient
from constants import API_BASE_URL
from loguru import logger

class VideoGenerationThread(QThread):
    """视频生成工作线程"""
    progress = pyqtSignal(str)
    task_created = pyqtSignal(str, dict)  # task_id, task_data - 当任务创建成功时发出
    task_creation_failed = pyqtSignal(str)  # message - 当任务创建失败时发出
    finished = pyqtSignal(bool, str, str, str)  # success, message, video_url, task_id

    def __init__(self, api_key, prompt, model, duration, images, aspect_ratio="16:9"):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        self.model = model
        self.duration = duration
        self.images = images
        self.aspect_ratio = aspect_ratio
        self.running = True

    def run(self):
        """实际的视频生成实现"""
        try:
            # 使用SoraClient进行API调用
            client = SoraClient(base_url=API_BASE_URL, api_key=self.api_key)

            self.progress.emit("正在创建视频生成任务...")

            # 使用现有的 create_sora2_video 方法
            result = client.create_sora2_video(
                prompt=self.prompt,
                aspect_ratio=self.aspect_ratio,
                hd=False,
                duration=str(self.duration),
                images=self.images if self.images else None
            )
            
            task_id = result.get('task_id') or result.get('id')
            if not task_id:
                error_msg = result.get('message', 'API返回结果中没有任务ID')
                self.task_creation_failed.emit(error_msg)
                return

            self.progress.emit(f"任务创建成功！任务ID: {task_id}")

            # 创建任务数据用于存储到数据库
            task_data = {
                'task_id': task_id,
                'prompt': self.prompt,
                'model': self.model,
                'orientation': 'portrait' if self.aspect_ratio == "9:16" else 'landscape',
                'size': 'small',  # 默认值
                'duration': self.duration,
                'images': self.images,
                'video_url': '',
                'thumbnail_url': '',
                'status': 'processing'  # 任务已创建，状态为处理中
            }

            # 发出任务创建信号
            self.task_created.emit(task_id, task_data)

            # 等待任务完成
            # final_result = client.wait_for_completion(
            #     task_id=task_id,
            #     max_wait_time=600,  # 10分钟
            #     poll_interval=10    # 每10秒查询一次
            # )

            # status = final_result.get('status', '')

            # if status == 'completed':
            #     video_url = final_result.get('video_url') or final_result.get('detail', {}).get('url', '')
            #     if video_url:
            #         self.finished.emit(True, "视频生成成功", video_url, task_id)
            #     else:
            #         self.finished.emit(False, "任务完成但没有返回视频URL", "", task_id)
            # else:
            #     failure_reason = final_result.get('detail', {}).get('pending_info', {}).get('failure_reason', '未知错误')
            #     error_msg = f"视频生成失败: {failure_reason}" if failure_reason else f"任务失败，状态: {status}"
            #     self.finished.emit(False, error_msg, "", task_id)

        except Exception as e:
            # 尝试从异常中解析错误信息
            error_message = str(e)
            
            # 检查是否有附加的错误数据
            if hasattr(e, 'error_data'):
                error_data = getattr(e, 'error_data', None)
                # 优先使用message字段
                if error_data and 'message' in error_data:
                    error_message = error_data['message']
                logger.error(f"API错误详情: {error_data}")
            elif hasattr(e, 'response') and getattr(e, 'response', None) is not None:
                # 尝试从响应中解析JSON
                try:
                    response = getattr(e, 'response', None)
                    if response:
                        error_json = response.json()
                        if 'message' in error_json:
                            error_message = error_json['message']
                        logger.error(f"API错误响应: {error_json}")
                except:
                    pass
            
            logger.error(f"视频生成失败: {error_message}")
            self.task_creation_failed.emit(error_message)
