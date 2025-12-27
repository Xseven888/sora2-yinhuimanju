"""
Sora2角色上传线程
"""

import os
import subprocess
import sqlite3
import requests
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from database_manager import db_manager
from constants import API_BASE_URL
from loguru import logger
import imageio_ffmpeg
from utils.oss_uploader import OSSUploader


class SoraCharacterUploadThread(QThread):
    """Sora2角色上传线程"""
    
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(dict)  # 完成信号，参数为角色信息字典
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, character_id, timestamps="1,3", parent=None):
        super().__init__(parent)
        self.character_id = character_id
        self.timestamps = timestamps  # 格式: "1,3"，默认1-3秒
        
    def run(self):
        """执行上传任务"""
        try:
            # 检查是否被请求中断
            if self.isInterruptionRequested():
                return
            
            # 1. 获取角色图片和绑定的音色
            self.progress.emit("正在获取角色信息...")
            character_data = self.get_character_data()
            if not character_data:
                raise RuntimeError("无法获取角色信息")
            
            image_path = character_data[0]
            voice_id = character_data[1]
            
            if not image_path or not Path(image_path).exists():
                raise RuntimeError("角色图片不存在，请先生成角色图片")
            
            if not voice_id:
                raise RuntimeError("未绑定音色，请先绑定音色")
            
            # 2. 获取音色文件路径
            self.progress.emit("正在获取音色文件...")
            voice_path = self.get_voice_file_path(voice_id)
            if not voice_path or not Path(voice_path).exists():
                raise RuntimeError("音色文件不存在")
            
            # 3. 合并图片和音频生成视频
            self.progress.emit("正在合并图片和音频生成视频...")
            video_path = self.merge_image_and_audio(image_path, voice_path)
            
            # 4. 上传视频到OSS
            self.progress.emit("正在上传视频到OSS...")
            video_url = self.upload_video_to_oss(video_path)
            
            # 5. 调用创建角色API
            self.progress.emit("正在创建Sora2角色...")
            character_info = self.create_sora_character(video_url, self.timestamps)
            
            if not character_info:
                raise RuntimeError("创建角色失败，未返回角色信息")
            
            # 6. 更新数据库
            self.progress.emit("正在保存角色信息...")
            self.update_character_info(character_info)
            
            # 7. 清理临时视频文件
            try:
                if Path(video_path).exists():
                    os.remove(video_path)
            except:
                pass
            
            self.progress.emit("上传完成")
            self.finished.emit(character_info)
            
        except Exception as e:
            error_msg = f"上传Sora2角色失败: {str(e)}"
            logger.error(error_msg)
            # 只有在对话框还存在时才发送错误信号
            try:
                self.error.emit(error_msg)
            except RuntimeError:
                # 如果对话框已关闭，信号接收者不存在，忽略错误
                pass
    
    def get_character_data(self):
        """获取角色数据（图片路径和音色ID）"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT front_image, voice_id
                FROM characters
                WHERE id = ?
            ''', (self.character_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"获取角色数据失败: {e}")
            return None
    
    def get_voice_file_path(self, voice_id):
        """获取音色文件路径"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT file_path FROM voice_library WHERE id = ?', (voice_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"获取音色文件路径失败: {e}")
            return None
    
    def merge_image_and_audio(self, image_path, audio_path):
        """使用ffmpeg将图片和音频合并成视频"""
        try:
            # 创建临时视频文件
            temp_dir = Path(db_manager.app_data_dir) / "temp_videos"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            import uuid
            video_filename = f"character_{self.character_id}_{uuid.uuid4().hex[:8]}.mp4"
            video_path = temp_dir / video_filename
            
            # 获取ffmpeg可执行文件
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            # 获取音频时长（用于设置视频时长）
            # 先获取音频信息
            probe_cmd = [
                ffmpeg_exe,
                "-i", str(audio_path),
                "-show_entries", "format=duration",
                "-v", "quiet",
                "-of", "csv=p=0"
            ]
            
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                audio_duration = float(probe_result.stdout.strip()) if probe_result.returncode == 0 else 3.0
            except:
                audio_duration = 3.0  # 默认3秒
            
            # 确保视频时长至少3秒（满足API要求）
            video_duration = max(audio_duration, 3.0)
            
            # 构建ffmpeg命令：将图片循环播放并添加音频
            # -loop 1: 循环输入图片
            # -t: 设置输出时长
            # -i: 输入图片和音频
            # -c:v libx264: 视频编码
            # -c:a aac: 音频编码
            # -pix_fmt yuv420p: 像素格式（兼容性）
            # -shortest: 以最短的输入流为准（音频结束视频也结束）
            cmd = [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel", "error",
                "-loop", "1",
                "-i", str(image_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-t", str(video_duration),
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-y",  # 覆盖输出文件
                str(video_path)
            ]
            
            logger.info(f"执行ffmpeg命令合并视频: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if proc.returncode != 0:
                err = (proc.stderr or "ffmpeg执行失败").strip()
                logger.error(f"ffmpeg合并视频失败: {err}")
                raise RuntimeError(f"合并视频失败: {err}")
            
            if not video_path.exists():
                raise RuntimeError("视频文件生成失败")
            
            logger.info(f"视频合并成功: {video_path}")
            return str(video_path)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("视频合并超时")
        except Exception as e:
            logger.error(f"合并视频失败: {e}")
            raise
    
    def upload_video_to_oss(self, video_path):
        """上传视频到OSS"""
        try:
            # 检查OSS配置
            oss_bucket = db_manager.load_config('oss_bucket_domain', '')
            if not oss_bucket:
                raise RuntimeError("未配置OSS Bucket域名，请在设置中配置")
            
            # 创建OSS上传器
            uploader = OSSUploader(oss_bucket)
            
            # 上传视频
            video_url = uploader.upload_video(video_path)
            logger.info(f"视频上传到OSS成功: {video_url}")
            return video_url
            
        except Exception as e:
            logger.error(f"上传视频到OSS失败: {e}")
            raise
    
    def create_sora_character(self, video_url, timestamps):
        """调用API创建Sora2角色"""
        api_key = db_manager.load_config('api_key', '')
        if not api_key:
            raise RuntimeError("未配置API Key，请在设置中配置")
        
        url = f"{API_BASE_URL}/sora/v1/characters"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "url": video_url,
            "timestamps": timestamps
        }
        
        logger.info(f"创建Sora2角色: url={video_url}, timestamps={timestamps}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        
        if response.status_code != 200:
            error_text = response.text[:500] if response.text else "无响应内容"
            raise RuntimeError(f"API调用失败: {response.status_code} - {error_text}")
        
        result = response.json()
        
        # 解析返回的角色信息
        if "id" in result and "username" in result:
            return {
                "id": result.get("id"),
                "username": result.get("username"),
                "permalink": result.get("permalink", ""),
                "profile_picture_url": result.get("profile_picture_url", "")
            }
        else:
            raise RuntimeError("API返回格式异常，未找到角色信息")
    
    def update_character_info(self, character_info):
        """更新角色信息到数据库"""
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE characters
                SET sora_character_id = ?,
                    sora_character_username = ?,
                    sora_status = '已上传',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                character_info["id"],
                character_info["username"],
                self.character_id
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新角色信息失败: {e}")
            raise

