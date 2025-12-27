"""
视频状态查询线程
"""

from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from database_manager import db_manager
from sora_client import SoraClient
from loguru import logger
import requests


class VideoStatusCheckThread(QThread):
    """视频状态查询线程"""
    
    status_updated = pyqtSignal(int, str, str)  # 信号：storyboard_id, status, video_url
    error = pyqtSignal(int, str)  # 错误信号：storyboard_id, 错误信息
    
    def __init__(self, storyboard_id, task_id, parent=None):
        super().__init__(parent)
        self.storyboard_id = storyboard_id
        self.task_id = task_id
        self._stop = False
        
    def run(self):
        """执行查询任务"""
        try:
            # 获取API密钥
            api_key = db_manager.load_config('api_key', '')
            if not api_key:
                raise RuntimeError("未设置API密钥")
            
            # 创建Sora2客户端
            sora_client = SoraClient(api_key=api_key)
            
            # 轮询查询任务状态
            max_attempts = 120  # 最多查询120次（约20分钟，每10秒一次）
            attempt = 0
            
            while not self._stop and attempt < max_attempts:
                if self.isInterruptionRequested():
                    break
                
                try:
                    # 查询任务状态
                    result = sora_client.query_video_task(self.task_id)
                    
                    # API响应结构：
                    # 顶层有: id, status, video_url, thumbnail_url
                    # detail里有: id, url, status, gif_url 等
                    status = result.get('status', '').lower()
                    video_url = result.get('video_url')
                    
                    # 如果顶层没有video_url，尝试从detail中获取
                    if not video_url:
                        detail = result.get('detail', {})
                        if detail:
                            video_url = detail.get('url')
                            # 如果detail中有status，优先使用detail的status（更准确）
                            detail_status = detail.get('status', '').lower()
                            if detail_status:
                                status = detail_status
                    
                    logger.info(f"查询任务状态: task_id={self.task_id}, status={status}, video_url={video_url or '(无)'}")
                    
                    # 更新数据库
                    db_manager.update_storyboard_video_info(
                        storyboard_id=self.storyboard_id,
                        video_url=video_url if video_url else None,
                        video_status=self._translate_status(status)
                    )
                    
                    # 发送状态更新信号
                    self.status_updated.emit(self.storyboard_id, status, video_url or '')
                    
                    # 如果任务完成或失败，停止查询
                    if status in ['completed', 'failed']:
                        break
                    
                    # 等待10秒后再次查询
                    self.msleep(10000)
                    attempt += 1
                    
                except requests.exceptions.HTTPError as http_error:
                    # 处理HTTP错误（如404任务不存在）
                    status_code = http_error.response.status_code if hasattr(http_error, 'response') and http_error.response else None
                    logger.warning(f"查询任务状态HTTP错误 (task_id={self.task_id}, status_code={status_code}): {http_error}")
                    
                    # 如果是404，说明任务不存在，标记为失败
                    if status_code == 404:
                        logger.warning(f"任务不存在 (404): {self.task_id}，标记为失败")
                        db_manager.update_storyboard_video_info(
                            storyboard_id=self.storyboard_id,
                            video_task_id=None,
                            video_url=None,
                            video_status='生成失败'
                        )
                        self.status_updated.emit(self.storyboard_id, 'failed', '')
                        break
                    else:
                        # 其他HTTP错误，继续重试（最多3次）
                        if attempt >= 3:
                            logger.error(f"查询任务状态多次失败，标记为失败: {self.task_id}")
                            db_manager.update_storyboard_video_info(
                                storyboard_id=self.storyboard_id,
                                video_url=None,
                                video_status='生成失败'
                            )
                            self.status_updated.emit(self.storyboard_id, 'failed', '')
                            break
                        self.msleep(10000)
                        attempt += 1
                        
                except Exception as e:
                    # 其他异常，记录并继续重试（最多3次）
                    logger.warning(f"查询任务状态异常 (task_id={self.task_id}): {e}")
                    if attempt >= 3:
                        logger.error(f"查询任务状态多次失败，标记为失败: {self.task_id}")
                        db_manager.update_storyboard_video_info(
                            storyboard_id=self.storyboard_id,
                            video_url=None,
                            video_status='生成失败'
                        )
                        self.status_updated.emit(self.storyboard_id, 'failed', '')
                        break
                    self.msleep(10000)
                    attempt += 1
            
            if attempt >= max_attempts:
                logger.warning(f"查询视频任务状态超时: {self.task_id}")
                # 超时也标记为失败
                db_manager.update_storyboard_video_info(
                    storyboard_id=self.storyboard_id,
                    video_url=None,
                    video_status='生成失败'
                )
                self.status_updated.emit(self.storyboard_id, 'failed', '')
                
        except Exception as e:
            logger.error(f"查询视频状态失败 (分镜ID: {self.storyboard_id}): {e}")
            # 发生异常时，标记为失败
            db_manager.update_storyboard_video_info(
                storyboard_id=self.storyboard_id,
                video_url=None,
                video_status='生成失败'
            )
            self.status_updated.emit(self.storyboard_id, 'failed', '')
    
    def stop(self):
        """停止查询"""
        self._stop = True
        self.requestInterruption()
    
    def _translate_status(self, status):
        """翻译状态"""
        status_map = {
            'pending': '等待中',
            'processing': '生成中',
            'completed': '已完成',
            'failed': '生成失败'
        }
        return status_map.get(status.lower(), status)

