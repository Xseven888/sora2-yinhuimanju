"""
视频分析工作线程
调用自定义API代理分析视频
"""

import requests
from requests.exceptions import ProxyError, ConnectionError
import json
import os
import uuid
import re
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from database_manager import db_manager
from constants import API_BASE_URL
from utils.file_utils import format_file_size

class VideoAnalysisThread(QThread):
    """视频分析工作线程"""
    progress = pyqtSignal(str)  # 进度消息
    result = pyqtSignal(object)  # 分析结果
    error = pyqtSignal(str)  # 错误消息

    def __init__(self, video_path, api_key):
        super().__init__()
        self.video_path = video_path
        self.api_key = api_key

    def run(self):
        """执行视频分析"""
        try:
            # 检查视频文件大小
            if not self.check_file_size():
                return
                
            self.progress.emit("正在上传视频到文件服务...")
            
            # 先上传视频到阿里云OSS
            video_url = self.upload_video_to_oss()
            
            self.progress.emit("正在分析视频...")
            
            # 调用自定义API代理进行视频分析
            analysis_result = self.analyze_video_with_proxy(video_url)
            
            self.result.emit(analysis_result)
                
        except Exception as e:
            error_msg = f"视频分析失败: {str(e)}"
            logger.error(error_msg)
            logger.exception(e)  # 记录完整的异常堆栈
            self.error.emit(error_msg)

    def check_file_size(self):
        """检查视频文件大小"""
        try:
            file_size = os.path.getsize(self.video_path)
            # 20MB = 20 * 1024 * 1024 bytes
            max_size = 20 * 1024 * 1024
            
            if file_size > max_size:
                error_msg = f"视频文件大小为 {format_file_size(file_size)}，超过20MB限制"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return False
            return True
        except Exception as e:
            error_msg = f"检查文件大小失败: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            return False

    def upload_video_to_oss(self):
        """通过文件服务接口上传视频并返回可访问URL

        使用 {api_base_url}/v1/files，multipart/form-data，字段 `file`。
        保留原方法名以兼容调用方。
        """
        try:
            p = Path(self.video_path)
            if not p.exists() or not p.is_file():
                raise FileNotFoundError(f"视频文件不存在: {self.video_path}")

            # 读取 API 基础地址与密钥
            base_url = API_BASE_URL
            api_key = db_manager.load_config('api_key', '')
            endpoint = f"{base_url.rstrip('/')}/v1/files"

            logger.info(f"api_key: {api_key}")

            logger.info(f"开始上传视频到文件服务: path={self.video_path} endpoint={endpoint}")

            # 内容类型推断
            def _guess_ct(suffix: str) -> str:
                s = (suffix or '').lower()
                if s in ['.mp4', '.m4v']:
                    return 'video/mp4'
                if s == '.avi':
                    return 'video/x-msvideo'
                if s == '.mov':
                    return 'video/quicktime'
                if s == '.mkv':
                    return 'video/x-matroska'
                if s == '.wmv':
                    return 'video/x-ms-wmv'
                if s == '.flv':
                    return 'video/x-flv'
                if s == '.webm':
                    return 'video/webm'
                return 'application/octet-stream'

            content_type = _guess_ct(p.suffix)

            headers = {
                'Accept': 'application/json',
            }
            if api_key:
                headers['Authorization'] = f"Bearer {api_key}"

            f = open(self.video_path, 'rb')
            files = {
                'file': (p.name, f, content_type)
            }

            # 保持原有的进度提示文案，避免UI变更
            self.progress.emit("正在上传视频文件到文件服务...")

            # 禁用系统代理，避免 127.0.0.1:7890 等导致连接失败
            session = requests.Session()
            session.trust_env = False
            session.proxies = {}
            try:
                resp = session.post(
                    endpoint,
                    files=files,
                    headers=headers,
                    timeout=300,
                    proxies={}
                )
            except (ProxyError, ConnectionError) as e:
                logger.warning(f"首次上传因代理/网络异常失败，将在禁用代理下重试: {e}")
                try:
                    resp = requests.post(
                        endpoint,
                        files=files,
                        headers=headers,
                        timeout=300,
                        proxies={}
                    )
                except Exception as e2:
                    raise e2
            finally:
                try:
                    session.close()
                except Exception:
                    pass

            logger.info(f"文件服务上传完成，状态码: {resp.status_code}")
            try:
                f.close()
            except Exception:
                pass

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    raise Exception(f"解析响应失败（非JSON）: {resp.text[:200]}")

                video_url = data.get('url') or ''
                if not video_url:
                    file_id = data.get('id')
                    filename = data.get('filename') or p.name
                    logger.warning(f"响应未包含 url，id={file_id}, filename={filename}")
                    # 尝试构造可能的下载地址（若服务支持）
                    possible = f"{base_url.rstrip('/')}/v1/files/{file_id}/content" if file_id else ''
                    video_url = possible

                if video_url:
                    logger.info(f"视频上传成功，URL: {video_url}")
                    return video_url
                else:
                    raise Exception("上传成功但响应未提供可访问URL")
            else:
                raise Exception(f"上传失败: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logger.error(f"视频上传到文件服务失败: {str(e)}")
            logger.exception(e)
            raise

    def analyze_video_with_proxy(self, video_url):
        """使用自定义API代理分析视频"""
        try:
            logger.info(f"开始分析视频，URL: {video_url}")
            
            # 从数据库获取API基础地址（与设置一致），否则使用默认
            api_proxy = API_BASE_URL
            logger.info(f"使用API代理地址: {api_proxy}")
            
            # 构建API请求
            url = f"{api_proxy.rstrip('/')}/v1/chat/completions"
            logger.info(f"分析API URL: {url}")
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            logger.info(f"分析请求头设置完成")
            
            # 构建请求体，包含视频URL
            payload = {
                "model": "gemini-2.5-pro-preview-05-06",
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "请分析该视频并按时间轴拆分为若干场景。" \
                                    "每个场景请严格给出以下字段，使用简体中文：" \
                                    "time(时间或时间段)、content(内容)、style(风格)、narration(旁白)、dialogue(人物对话)、audio(音频/音乐)。" \
                                    "仅以JSON数组返回，不要任何额外说明或客套话。示例：" \
                                    "[{" \
                                    "\"time\": \"00:00-00:05\", \"content\": \"镜头掠过城市夜景\", \"style\": \"冷色调、快剪\", " \
                                    "\"narration\": \"开场解说\", \"dialogue\": \"\", \"audio\": \"低沉电子乐\"}]"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": video_url
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000
            }
            logger.info(f"分析请求体构建完成，模型: {payload['model']}")
            
            self.progress.emit("正在调用视频分析API...")
            
            # 发送请求（禁用系统代理，避免 127.0.0.1:7890 等代理导致连接失败）
            logger.info("开始发送分析请求")
            session = requests.Session()
            session.trust_env = False
            try:
                response = session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                    proxies={"http": None, "https": None}
                )
            except (ProxyError, ConnectionError) as e:
                logger.warning(f"分析请求因代理/网络异常失败，将在禁用代理下重试: {e}")
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                    proxies={"http": None, "https": None}
                )
            finally:
                try:
                    session.close()
                except Exception:
                    pass
            logger.info(f"分析请求完成，状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"分析响应: {result}")
                
                # 解析响应结果
                analysis_result = self.parse_api_response(result)
                logger.info(f"解析分析结果完成，结果项数: {len(analysis_result) if isinstance(analysis_result, list) else 'N/A'}")
                
                # 检查是否有有效的分析结果
                if not analysis_result:
                    error_msg = "视频分析未返回有效结果"
                    logger.warning(error_msg)
                    raise Exception(error_msg)
                    
                return analysis_result
            else:
                error_msg = f"API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"API代理调用失败: {str(e)}")
            logger.exception(e)  # 记录完整的异常堆栈
            # 重新抛出异常，不返回模拟数据
            raise

    def parse_api_response(self, response):
        """解析API响应"""
        try:
            logger.info("开始解析API响应")
            
            if not response:
                logger.warning("API响应为空")
                return []
            
            if 'choices' not in response:
                logger.warning("API响应中缺少'choices'字段")
                return []
            
            choices = response['choices']
            if not choices:
                logger.warning("'choices'字段为空")
                return []
                
            # 获取第一个选择的内容
            message = choices[0].get('message', {})
            content = message.get('content', '')
            
            if not content:
                logger.warning("消息内容为空")
                return []
            
            # 优先尝试按JSON解析
            json_text = content.strip()
            # 去除代码块围栏
            if '```' in json_text:
                fences = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", json_text)
                if fences:
                    json_text = fences[0].strip()
            # 截取可能的JSON片段
            start_idx_candidates = [idx for idx in (json_text.find('['), json_text.find('{')) if idx != -1]
            if start_idx_candidates:
                start_idx = min(start_idx_candidates)
                end_idx = max(json_text.rfind(']'), json_text.rfind('}'))
                if end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx+1]
            try:
                data = json.loads(json_text)
                scenes = data.get('scenes', data) if isinstance(data, dict) else data
                if isinstance(scenes, list):
                    normalized = []
                    for s in scenes:
                        if not isinstance(s, dict):
                            continue
                        time_val = s.get('time') or s.get('time_range')
                        if not time_val:
                            start = s.get('start', '')
                            end = s.get('end', '')
                            time_val = f"{start}-{end}".strip('-')
                        item = {
                            'time': time_val or '',
                            'content': s.get('content') or s.get('description') or '',
                            'style': s.get('style') or '',
                            'narration': s.get('narration') or s.get('voice_over') or '',
                            'dialogue': s.get('dialogue') or s.get('character_dialogue') or '',
                            'audio': s.get('audio') or s.get('music_audio') or s.get('bgm') or ''
                        }
                        normalized.append(item)
                        logger.debug(f"解析场景 {len(normalized)}: {item}")
                    if normalized:
                        logger.info(f"JSON解析完成，共{len(normalized)}个场景")
                        return normalized
            except Exception as e:
                logger.debug(f"JSON解析失败，回退到行解析: {e}")

            # 回退：简单解析内容，按行分割
            lines = content.strip().split('\n')
            logger.info(f"内容解析完成，共{len(lines)}行")

            result = []
            i = 0
            while i < len(lines):
                # 跳过空行
                if not lines[i].strip():
                    i += 1
                    continue
                # 简单解析，假设每3行是一个时间段的信息
                if i + 2 < len(lines):
                    item = {
                        'time': f"00:00:{i//3*5:02d}",  # 简单的时间戳
                        'content': lines[i].strip() if lines[i].strip() else "视频内容",
                        'style': '',
                        'narration': '',
                        'dialogue': '',
                        'audio': lines[i+1].strip() if i+1 < len(lines) and lines[i+1].strip() else "音频内容"
                    }
                    result.append(item)
                    logger.debug(f"解析时间段 {len(result)}: {item}")
                i += 3

            logger.info(f"解析完成，共{len(result)}个时间段")
            return result
            
        except Exception as e:
            logger.error(f"解析API响应失败: {str(e)}")
            logger.exception(e)  # 记录完整的异常堆栈
            return []

    def get_mock_data(self):
        """获取模拟数据 - 仅用于测试"""
        logger.info("返回模拟数据")
        return [
            {
                'time': '00:00:01',
                'content': '视频开始，显示标题画面',
                'audio': '背景音乐开始播放'
            },
            {
                'time': '00:00:05',
                'content': '主角出现在画面中，穿着红色衣服',
                'audio': '主角说："大家好，欢迎观看我的视频"'
            },
            {
                'time': '00:00:10',
                'content': '展示产品特写镜头',
                'audio': '介绍产品功能和特点'
            },
            {
                'time': '00:00:15',
                'content': '演示产品使用过程',
                'audio': '详细说明使用步骤'
            },
            {
                'time': '00:00:20',
                'content': '总结和结束画面',
                'audio': '感谢观看，再见'
            }
        ]
