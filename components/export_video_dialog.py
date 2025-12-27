"""
导出视频进度对话框
"""

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    TitleLabel, BodyLabel, PushButton, ProgressBar, CardWidget
)
from loguru import logger


class ExportVideoThread(QThread):
    """导出视频线程"""
    progress = pyqtSignal(str)  # 进度消息
    finished = pyqtSignal(bool, str, str)  # success, message, output_path
    
    def __init__(self, episode_id, episode_data, project_data, parent=None):
        super().__init__(parent)
        self.episode_id = episode_id
        self.episode_data = episode_data
        self.project_data = project_data
        self._stop = False
        
    def run(self):
        """执行导出任务"""
        try:
            import sqlite3
            import requests
            import subprocess
            import imageio_ffmpeg
            import tempfile
            import shutil
            import os
            from pathlib import Path
            from database_manager import db_manager
            
            # 1. 获取所有已生成视频的分镜（按sequence_number排序）
            self.progress.emit("正在获取视频列表...")
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, sequence_number, video_url, title
                FROM storyboards
                WHERE episode_id = ? 
                  AND video_url IS NOT NULL 
                  AND video_url != ''
                ORDER BY sequence_number ASC
            """, (self.episode_id,))
            storyboards = cursor.fetchall()
            conn.close()
            
            if not storyboards:
                self.finished.emit(False, "没有已生成的视频可以导出", "")
                return
            
            # 2. 获取输出目录
            self.progress.emit("正在准备输出目录...")
            output_dir = db_manager.load_config('video_save_path', '')
            if not output_dir:
                output_dir = str(Path.home() / "Downloads" / "Sora2Videos")
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 3. 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="sora2_export_")
            logger.info(f"临时目录: {temp_dir}")
            
            try:
                # 4. 下载所有视频到临时目录
                self.progress.emit(f"正在下载 {len(storyboards)} 个视频...")
                video_files = []
                for idx, (storyboard_id, sequence_number, video_url, title) in enumerate(storyboards, 1):
                    if self._stop:
                        return
                    
                    self.progress.emit(f"正在下载视频 [{idx}/{len(storyboards)}]: 分镜{sequence_number}")
                    
                    try:
                        # 下载视频
                        response = requests.get(video_url, stream=True, timeout=300)
                        response.raise_for_status()
                        
                        # 保存到临时文件
                        temp_video_path = os.path.join(temp_dir, f"video_{sequence_number:03d}.mp4")
                        with open(temp_video_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if self._stop:
                                    return
                                if chunk:
                                    f.write(chunk)
                        
                        video_files.append(temp_video_path)
                        logger.info(f"视频下载完成: {temp_video_path}")
                        
                    except Exception as e:
                        logger.error(f"下载视频失败 (分镜{sequence_number}): {e}")
                        self.finished.emit(False, f"下载分镜{sequence_number}的视频失败: {str(e)}", "")
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return
                
                if not video_files:
                    self.finished.emit(False, "没有成功下载的视频", "")
                    return
                
                # 5. 合并视频
                self.progress.emit(f"正在合并 {len(video_files)} 个视频...")
                
                # 生成输出文件名
                episode_name = self.episode_data.get('episode_name', f'第{self.episode_data.get("episode_number", "?")}集')
                project_title = self.project_data.get('title', '项目')
                # 清理文件名中的非法字符
                safe_project_title = "".join(c for c in project_title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_episode_name = "".join(c for c in episode_name if c.isalnum() or c in (' ', '-', '_')).strip()
                output_filename = f"{safe_project_title}_{safe_episode_name}_合并视频.mp4"
                output_path = os.path.join(output_dir, output_filename)
                
                # 如果文件已存在，添加序号
                counter = 1
                original_output_path = output_path
                while os.path.exists(output_path):
                    base_name = os.path.splitext(original_output_path)[0]
                    output_path = f"{base_name}_{counter}.mp4"
                    counter += 1
                
                # 使用ffmpeg合并视频
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                
                # 创建文件列表（用于concat demuxer）
                concat_file = os.path.join(temp_dir, "concat_list.txt")
                with open(concat_file, 'w', encoding='utf-8') as f:
                    for video_file in video_files:
                        # 转义路径中的特殊字符
                        escaped_path = video_file.replace('\\', '/').replace("'", "'\\''")
                        f.write(f"file '{escaped_path}'\n")
                
                # 使用concat demuxer合并视频
                cmd = [
                    ffmpeg_exe,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_file,
                    "-c", "copy",
                    "-y",
                    output_path
                ]
                
                logger.info(f"执行ffmpeg合并命令: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True)
                
                if proc.returncode != 0:
                    error_msg = (proc.stderr or "ffmpeg合并失败").strip()
                    logger.error(f"ffmpeg合并失败: {error_msg}")
                    self.finished.emit(False, f"合并视频失败: {error_msg}", "")
                    return
                
                # 6. 清理临时文件
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # 7. 完成
                self.progress.emit("导出完成")
                self.finished.emit(True, f"视频已导出到: {output_path}", output_path)
                
            except Exception as e:
                logger.error(f"导出视频失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.finished.emit(False, f"导出视频失败: {str(e)}", "")
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"导出视频异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.finished.emit(False, f"导出视频失败: {str(e)}", "")
    
    def stop(self):
        """停止导出"""
        self._stop = True
        self.requestInterruption()


class ExportVideoDialog(QDialog):
    """导出视频进度对话框"""
    
    def __init__(self, episode_id, episode_data, project_data, parent=None):
        super().__init__(parent)
        self.episode_id = episode_id
        self.episode_data = episode_data
        self.project_data = project_data
        self.export_thread = None
        self.setWindowTitle("导出视频")
        self.setModal(True)
        self.resize(500, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("导出视频")
        layout.addWidget(title)
        
        # 状态卡片
        status_card = CardWidget()
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_layout.setSpacing(15)
        
        # 状态标签
        self.status_label = BodyLabel("准备中...")
        self.status_label.setStyleSheet("font-size: 14px;")
        status_layout.addWidget(self.status_label)
        
        # 进度条（不确定进度）
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定进度模式
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_card)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_btn)
        
        self.close_btn = PushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)  # 初始隐藏
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
    def start_export(self):
        """开始导出"""
        # 创建导出线程
        self.export_thread = ExportVideoThread(
            self.episode_id,
            self.episode_data,
            self.project_data,
            self
        )
        self.export_thread.progress.connect(self.on_progress)
        self.export_thread.finished.connect(self.on_finished)
        self.export_thread.start()
        
        # 禁用取消按钮（导出开始后）
        self.cancel_btn.setEnabled(True)
        
    def on_progress(self, message):
        """更新进度"""
        self.status_label.setText(message)
        
    def on_finished(self, success, message, output_path):
        """导出完成"""
        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("font-size: 14px; color: #4CAF50;")
            # 显示完成进度条
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("font-size: 14px; color: #D32F2F;")
            # 显示失败进度条
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        
        # 隐藏取消按钮，显示关闭按钮
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)
        
    def on_cancel(self):
        """取消导出"""
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.stop()
            self.export_thread.wait(3000)  # 等待最多3秒
        
        self.reject()
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.export_thread and self.export_thread.isRunning():
            self.export_thread.stop()
            self.export_thread.wait(3000)
        event.accept()

