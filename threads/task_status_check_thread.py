"""
任务状态检查线程
"""

import time
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from sora_client import SoraClient
from constants import API_BASE_URL
from database_manager import db_manager

class TaskStatusCheckThread(QThread):
    """任务状态检查线程"""
    status_updated = pyqtSignal(str, dict)  # task_id, updated_data

    def __init__(self):
        super().__init__()
        self.running = True
        self.check_interval = 10  # 10秒检查一次

    def run(self):
        """循环检查未完成的任务状态"""
        while self.running:
            try:
                # 只获取未完成的任务（排除已完成和失败的任务）
                # 先获取进行中的任务
                processing_tasks = db_manager.get_tasks(status='processing', limit=50)
                # 再获取待处理的任务
                pending_tasks = db_manager.get_tasks(status='pending', limit=50)
                # 合并任务列表
                tasks = processing_tasks + pending_tasks

                for task in tasks:
                    if not self.running:
                        break

                    task_id = task.get('task_id')
                    if not task_id:
                        continue
                        
                    status = task.get('status')
                    
                    # 检查是否为Chat模式任务，如果是则跳过(因为Chat模式是同步返回，不需要轮询)
                    if db_manager.is_chat_task(task_id):
                        logger.debug(f"跳过Chat模式任务: {task_id}")
                        continue

                    # 使用SoraClient查询任务状态
                    api_key = db_manager.load_config('api_key', '')
                    if api_key:
                        try:
                            client = SoraClient(base_url=API_BASE_URL, api_key=api_key)
                            result = client.query_task(task_id)
                            current_status = result.get('status', '')

                            # 获取详细的任务信息
                            task_detail = result

                            # 根据API返回的状态判断，只有明确返回completed或failed才算完成
                            final_status = status or ''  # 默认保持原状态
                            updates = {
                                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }

                            if current_status:
                                # 根据API返回的状态映射到内部状态
                                status_mapping = {
                                    'SUCCESS': 'completed',
                                    'FAILURE': 'failed',
                                    'IN_PROGRESS': 'processing',
                                    'NOT_START': 'pending',
                                    'COMPLETED': 'completed',  # 添加对COMPLETED状态的支持
                                    'FAILED': 'failed'  # 添加对FAILED状态的支持
                                }
                                
                                # 只有明确状态才更新
                                if current_status in ['SUCCESS', 'COMPLETED']:
                                    final_status = 'completed'
                                    # 获取视频URL
                                    if task_detail:
                                        # 打印完整的任务详情以便调试
                                        logger.info(f"任务详情: {task_detail}")
                                        
                                        # 尝试多种方式获取视频URL
                                        video_url = None
                                        
                                        # 方式1: 从 data.output 获取
                                        if 'data' in task_detail and isinstance(task_detail['data'], dict) and 'output' in task_detail['data']:
                                            video_url = task_detail['data'].get('output')
                                            logger.info(f"从 data.output 获取: {video_url}")
                                        
                                        # 方式2: 直接获取 video_url 字段
                                        if not video_url and 'video_url' in task_detail:
                                            video_url = task_detail.get('video_url')
                                            logger.info(f"从 video_url 字段获取: {video_url}")
                                        
                                        # 方式3: 从 detail.url 获取
                                        if not video_url and 'detail' in task_detail:
                                            detail = task_detail.get('detail', {})
                                            if isinstance(detail, dict) and 'url' in detail:
                                                video_url = detail.get('url')
                                                logger.info(f"从 detail.url 获取: {video_url}")
                                        
                                        # 方式4: 从 data.video_url 获取
                                        if not video_url and 'data' in task_detail:
                                            data = task_detail.get('data', {})
                                            if isinstance(data, dict) and 'video_url' in data:
                                                video_url = data.get('video_url')
                                                logger.info(f"从 data.video_url 获取: {video_url}")
                                        
                                        # 方式5: 从 url 字段直接获取
                                        if not video_url and 'url' in task_detail:
                                            video_url = task_detail.get('url')
                                            logger.info(f"从 url 字段获取: {video_url}")
                                        
                                        if video_url:
                                            updates['video_url'] = video_url
                                            updates['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                            logger.info(f"最终获取的视频URL: {video_url}")
                                        else:
                                            logger.warning(f"未能从任务详情中获取视频URL")

                                elif current_status in ['FAILURE', 'FAILED']:
                                    final_status = 'failed'
                                    # 获取错误信息
                                    if task_detail:
                                        # 从fail_reason字段获取错误信息
                                        failure_reason = task_detail.get('fail_reason', '生成失败')
                                        updates['error_message'] = failure_reason
                                        updates['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                                elif current_status in ['IN_PROGRESS', 'NOT_START']:
                                    # 进行中或未开始状态
                                    final_status = status_mapping.get(current_status, 'processing')
                                else:
                                    # 其他状态都视为进行中
                                    final_status = 'processing'

                            # 只有状态发生变化时才更新数据库
                            if final_status != status or 'video_url' in updates or 'error_message' in updates:
                                updates['status'] = str(final_status)

                                # 更新数据库
                                if db_manager.update_task(str(task_id), updates):
                                    # 发出状态更新信号
                                    updates['task_id'] = str(task_id)
                                    self.status_updated.emit(str(task_id), updates)

                                    logger.info(f"任务 {task_id} 状态更新: {status} -> {final_status}")

                        except Exception as e:
                            logger.error(f"检查任务 {task_id} 状态失败: {e}")

                # 等待下一次检查
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    self.sleep(1)

            except Exception as e:
                logger.error(f"任务状态检查线程出错: {e}")
                self.sleep(5)  # 出错时等待5秒再重试

    def stop(self):
        """停止线程"""
        self.running = False
