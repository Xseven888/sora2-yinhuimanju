"""
视频高清放大线程
"""

import json
import time
import requests
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

class VideoUpscaleThread(QThread):
    """视频高清放大线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)  # success, message, output_path

    def __init__(self, video_path, output_path, mode, scale, comfyui_server):
        super().__init__()
        self.video_path = video_path
        self.output_path = output_path
        self.mode = mode
        self.scale = scale
        self.comfyui_server = comfyui_server

    def _base(self):
        return (self.comfyui_server or "").rstrip('/')

    def run(self):
        """执行高清放大"""
        try:
            self.progress.emit("开始高清放大处理...")
            
            # 读取sora2_up.json模板
            template_path = Path(__file__).parent.parent / "sora2_up.json"
            if not template_path.exists():
                self.finished.emit(False, "sora2_up.json模板文件不存在", "")
                return
                
            # 读取模板文件
            with open(template_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
                
            # 修改模板参数
            # 设置视频文件路径
            video_filename = Path(self.video_path).name
            workflow["14"]["inputs"]["video"] = video_filename  # 节点14是VHS_LoadVideo
            
            # 设置模式和放大系数 (节点11是FlashVSRNode)
            workflow["11"]["inputs"]["mode"] = self.mode
            workflow["11"]["inputs"]["scale"] = self.scale
            
            # 设置输出文件名前缀 (节点12是VHS_VideoCombine)
            output_prefix = Path(self.output_path).stem
            workflow["12"]["inputs"]["filename_prefix"] = output_prefix
            
            # 上传视频文件到ComfyUI (使用正确的API端点)
            self.progress.emit("正在上传视频文件...")
            with open(self.video_path, 'rb') as video_file:
                files = {'image': (video_filename, video_file, 'video/mp4')}
                upload_response = requests.post(f"{self._base()}/upload/image", files=files)
            
            if upload_response.status_code != 200:
                self.finished.emit(False, f"上传视频文件失败: {upload_response.status_code}: {upload_response.text}", "")
                return
                
            # 发送工作流到ComfyUI
            self.progress.emit("正在发送处理请求...")
            workflow_response = requests.post(
                f"{self._base()}/prompt",
                json={"prompt": workflow}
            )
            
            if workflow_response.status_code != 200:
                self.finished.emit(False, f"发送处理请求失败: {workflow_response.status_code}: {workflow_response.text}", "")
                return
                
            # 获取prompt_id
            prompt_data = workflow_response.json()
            prompt_id = prompt_data.get("prompt_id") or prompt_data.get("data", {}).get("prompt_id")
            
            if not prompt_id:
                self.finished.emit(False, "未能获取处理任务ID", "")
                return
                
            # 轮询处理状态
            self.progress.emit("正在处理视频，请稍候...")
            max_wait_time = 600  # 最大等待10分钟
            check_interval = 5   # 每5秒检查一次
            wait_time = 0
            
            # 初始化output_info
            output_info = {}
            
            while wait_time < max_wait_time:
                # 检查处理状态
                try:
                    status_response = requests.get(f"{self._base()}/history")
                    if status_response.status_code == 200:
                        history_data = status_response.json()
                        # 查找我们的prompt_id
                        if prompt_id in history_data:
                            # 处理完成，获取输出信息
                            output_info = history_data[prompt_id].get("outputs", {})
                            self.progress.emit(f"处理完成，输出信息: {output_info}")
                            break
                        # 检查是否在history中（较新的ComfyUI版本）
                        for key, value in history_data.items():
                            if key == prompt_id or (isinstance(value, dict) and value.get('prompt', [None])[0] == prompt_id):
                                # 处理完成，获取输出信息
                                output_info = value.get("outputs", {})
                                self.progress.emit(f"处理完成，输出信息: {output_info}")
                                break
                except Exception as e:
                    self.progress.emit(f"检查状态时出错: {str(e)}")
                    
                time.sleep(check_interval)
                wait_time += check_interval
                self.progress.emit(f"处理中... ({wait_time}/{max_wait_time}秒)")
                
            if wait_time >= max_wait_time:
                self.finished.emit(False, "处理超时", "")
                return
                
            # 下载处理后的视频
            self.progress.emit("正在下载处理后的视频...")
            
            # 使用通用的下载方法
            if self.download_output(output_info, self.output_path):
                self.finished.emit(True, "高清放大处理完成", self.output_path)
            else:
                self.finished.emit(False, "无法下载处理后的视频", "")
            
        except Exception as e:
            self.finished.emit(False, f"处理过程中出现错误: {str(e)}", "")

    def download_output(self, output_info: dict, save_path: str) -> bool:
        """下载输出文件（支持视频、GIF等多种格式）"""
        try:
            self.progress.emit(f"开始下载输出文件，输出信息: {output_info}")
            self.progress.emit(f"保存路径: {save_path}")

            # 检查所有输出内容
            for node_id, node_output in output_info.items():
                self.progress.emit(f"节点 {node_id} 输出: {node_output}")

                # 检查视频输出
                if "videos" in node_output:
                    self.progress.emit(f"找到视频输出: {node_output['videos']}")
                    for video_info in node_output["videos"]:
                        if self._download_file(video_info, save_path, "视频"):
                            return True

                # 检查GIF输出（实际的mp4文件）
                if "gifs" in node_output:
                    self.progress.emit(f"找到GIF输出: {node_output['gifs']}")
                    for gif_info in node_output["gifs"]:
                        if self._download_file(gif_info, save_path, "GIF/视频"):
                            return True

                # 检查图片输出
                if "images" in node_output:
                    self.progress.emit(f"找到图片输出: {node_output['images']}")
                    for image_info in node_output["images"]:
                        if self._download_file(image_info, save_path, "图片"):
                            return True

            self.progress.emit(f"没有找到任何可下载的输出文件")
            return False

        except Exception as e:
            self.progress.emit(f"下载输出文件时发生异常: {str(e)}")
            import traceback
            self.progress.emit(f"异常堆栈: {traceback.format_exc()}")
            return False

    def _download_file(self, file_info: dict, save_path: str, file_type: str) -> bool:
        """下载单个文件"""
        try:
            # 获取文件信息
            filename = file_info.get("filename", "")
            subfolder = file_info.get("subfolder", "")
            file_type_param = file_info.get("type", "output")
            
            self.progress.emit(f"尝试下载{file_type}: {filename}, 子文件夹: {subfolder}, 类型: {file_type_param}")
            
            if not filename:
                self.progress.emit("文件名为空，跳过")
                return False

            # 构造下载参数
            download_params = {
                "filename": filename,
                "type": file_type_param
            }
            
            if subfolder:
                download_params["subfolder"] = subfolder

            # 发送下载请求
            download_response = requests.get(
                f"{self._base()}/view",
                params=download_params,
                timeout=60
            )
            
            self.progress.emit(f"下载响应状态码: {download_response.status_code}")
            self.progress.emit(f"下载响应大小: {len(download_response.content)} bytes")
            
            if download_response.status_code == 200 and len(download_response.content) > 0:
                # 检查返回的内容是否是视频数据
                content_type = download_response.headers.get('content-type', '')
                self.progress.emit(f"下载响应Content-Type: {content_type}")
                
                # 保存到指定路径
                with open(save_path, 'wb') as f:
                    f.write(download_response.content)
                
                self.progress.emit(f"{file_type}下载成功并保存到: {save_path}")
                return True
            else:
                self.progress.emit(f"{file_type}下载失败: 状态码 {download_response.status_code}, 内容长度: {len(download_response.content)}")
                return False
                
        except Exception as e:
            self.progress.emit(f"下载{file_type}时发生异常: {str(e)}")
            return False
