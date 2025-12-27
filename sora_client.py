"""
Sora 2 视频生成客户端
支持创建视频生成任务以及查询任务状态
"""

import requests
import json
import time
from typing import List, Dict, Optional, Union
from enum import Enum
import logging
from constants import API_HOST

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SoraModel(Enum):
    """Sora模型枚举"""
    SORA_2 = "sora-2"
    SORA_2_PRO = "sora-2-pro"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SoraClient:
    """Sora 2 视频生成客户端"""

    def __init__(self, base_url: str = "https://api.sora2.email", api_key: Optional[str] = None):
        """
        初始化Sora客户端

        Args:
            base_url: API基础URL
            api_key: API密钥
        """
        print(f"\n[INFO] 初始化Sora客户端")
        print(f"   [WEB] API基础URL: {base_url}")
        print(f"   [KEY] API密钥: {'已设置' if api_key else '未设置'}")

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        # 设置默认请求头 - 模拟Apifox调试环境
        default_headers = {
            'Accept': 'application/json',
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Content-Type': 'application/json',
            'Host': API_HOST,
            'Connection': 'keep-alive'
        }
        self.session.headers.update(default_headers)
        print(f"   [LIST] 设置Apifox兼容请求头: {default_headers}")

        if self.api_key:
            # 清理API密钥 - 去除可能的空格和换行
            cleaned_api_key = self.api_key.strip()
            print(f"   [KEY] 原始API密钥长度: {len(self.api_key)}")
            print(f"   [KEY] 清理后API密钥长度: {len(cleaned_api_key)}")

            # 检查API密钥格式
            if not cleaned_api_key.startswith('sk-'):
                print(f"   ⚠️ 警告: API密钥格式可能不正确，通常应该以'sk-'开头")

            if len(cleaned_api_key) < 20:
                print(f"   ⚠️ 警告: API密钥长度似乎太短 ({len(cleaned_api_key)} 字符)")

            self.api_key = cleaned_api_key
            auth_header = {'Authorization': f'Bearer {self.api_key}'}
            self.session.headers.update(auth_header)
            print(f"   [AUTH] 认证头已设置: Bearer {self.api_key[:10]}...")
        else:
            print(f"   [ERROR] 警告: 未提供API密钥")

        print(f"   [OK] Sora客户端初始化完成")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数

        Returns:
            响应数据

        Raises:
            requests.RequestException: 请求失败时抛出
        """
        url = f"{self.base_url}{endpoint}"

        # 添加详细的请求日志
        print(f"\n[API] 发送HTTP请求:")
        print(f"   方法: {method}")
        print(f"   URL: {url}")
        print(f"   请求头: {dict(self.session.headers)}")

        # 记录请求参数
        if 'json' in kwargs:
            print(f"   JSON数据: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
        if 'params' in kwargs:
            print(f"   URL参数: {kwargs['params']}")
        if 'data' in kwargs:
            print(f"   表单数据: {kwargs['data']}")

        print(f"   完整请求参数: {kwargs}")

        try:
            print(f"   [SEND] 正在发送请求...")
            response = self.session.request(method, url, **kwargs)

            # 添加响应日志
            print(f"   [RECV] 响应状态码: {response.status_code}")
            print(f"   [RECV] 响应头: {dict(response.headers)}")
            print(f"   [RECV] 响应大小: {len(response.content)} bytes")

            # 先尝试解析响应，再检查状态码
            try:
                response_data = response.json()
                print(f"   [RECV] 响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                
                # 检查是否是错误响应（有code和message字段）
                if not response.ok and 'code' in response_data and 'message' in response_data:
                    # API返回了结构化的错误信息
                    error_code = response_data.get('code', 'unknown')
                    error_message = response_data.get('message', '未知错误')
                    print(f"   [ERROR] API错误 - Code: {error_code}, Message: {error_message}")
                    logger.error(f"API错误: {error_code} - {error_message}")
                    
                    # 抛出自定义异常，包含错误信息
                    error = requests.exceptions.HTTPError(f"{error_message}")
                    error.response = response
                    setattr(error, 'error_data', response_data)  # 附加错误数据
                    raise error
                
                # 正常响应，检查HTTP状态码
                response.raise_for_status()
                return response_data
                
            except json.JSONDecodeError:
                # 非JSON响应，检查HTTP状态码
                response.raise_for_status()
                print(f"   [RECV] 响应内容 (非JSON): {response.text[:500]}...")
                return {"response": response.text}

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] 请求失败: {e}")
            logger.error(f"请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    # 尝试解析错误响应中的JSON
                    error_json = e.response.json()
                    print(f"   [ERROR] 错误响应JSON: {json.dumps(error_json, ensure_ascii=False, indent=2)}")
                    logger.error(f"错误响应: {error_json}")
                    
                    # 如果error_json中包含'error'字段且有'message',使用更友好的错误消息
                    if 'error' in error_json and 'message' in error_json['error']:
                        friendly_message = error_json['error']['message']
                        print(f"   [ERROR] 提取友好错误消息: {friendly_message}")
                        # 创建新的Exception带有友好的错误消息
                        new_error = Exception(friendly_message)
                        setattr(new_error, 'error_data', error_json)
                        setattr(new_error, 'response', e.response)
                        raise new_error
                    else:
                        # 没有友好消息,附加error_data后重新抛出
                        setattr(e, 'error_data', error_json)
                        raise
                except Exception as parse_error:
                    # 如果是我们创建的友好错误异常，直接重新抛出
                    if str(parse_error) != str(e):
                        # 这是我们创建的带有友好消息的异常
                        print(f"   [ERROR] 重新抛出友好错误消息: {parse_error}")
                        raise parse_error
                    # 解析JSON失败，记录原始响应
                    print(f"   [ERROR] 解析错误响应失败: {parse_error}")
                    print(f"   [ERROR] 错误响应内容: {e.response.text}")
                    logger.error(f"响应内容: {e.response.text}")
            raise

    def create_sora2_video(
        self,
        prompt: str,
        model: str = "sora-2",
        aspect_ratio: str = "16:9",
        hd: bool = False,
        duration: str = "10",
        images: Optional[List[str]] = None
    ) -> Dict:
        """
        使用Sora2 API创建视频生成任务 (v2版本)
        支持文生视频和图生视频
        
        Args:
            prompt: 视频生成提示词
            model: 模型名称 (sora-2 或 sora-2-pro)
            aspect_ratio: 输出比例 ('16:9' 横屏 或 '9:16' 竖屏)
            hd: 是否生成高清，默认false
            duration: 视频时长 ('10', '15', '25')
            images: 图片URL列表（可选，用于图生视频）
            notify_hook: 回调URL
            watermark: 是否添加水印，默认false
            
        Returns:
            任务创建响应，包含task_id
        """
        print(f"\n[VIDEO] 开始使用 Sora2 v2 API 创建视频生成任务")
        print(f"   [TEXT] 提示词: {prompt}")
        print(f"   [MODEL] 模型: {model}")
        print(f"   [RATIO] 比例: {aspect_ratio}")
        print(f"   [HD] 高清: {hd}")
        print(f"   [TIME] 时长: {duration}")
        
        payload = {
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "hd": hd,
            "duration": duration
        }
        
        # 如果提供了图片，则添加到payload中
        if images:
            payload["images"] = images
            print(f"   [IMAGE] 图片数量: {len(images)}")
            for i, img in enumerate(images, 1):
                print(f"      图片{i}: {img}")
        
            
        print(f"   [DATA] 构建的请求数据包:")
        for key, value in payload.items():
            print(f"      {key}: {value}")

        logger.info(f"创建 Sora2 v2 视频任务: {prompt}")
        result = self._make_request('POST', '/v2/videos/generations', json=payload)

        print(f"   [OK] Sora2 v2 任务创建请求完成")
        return result

    def query_task(self, task_id: str) -> Dict:
        """
        查询任务状态 (v2版本)
        
        Args:
            task_id: 任务ID

        Returns:
            任务状态响应
        """
        print(f"\n[SEARCH] 开始查询任务状态 (v2 API)")
        print(f"   🆔 任务ID: {task_id}")

        logger.info(f"查询任务状态: {task_id}")
        result = self._make_request('GET', f'/v2/videos/generations/{task_id}')

        print(f"   [OK] 任务状态查询完成")
        return result

    def wait_for_completion(
        self,
        task_id: str,
        max_wait_time: int = 1200,
        poll_interval: int = 10
    ) -> Dict:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            最终任务状态

        Raises:
            TimeoutError: 等待超时
        """
        print(f"\n[TIMER] 开始等待任务完成")
        print(f"   🆔 任务ID: {task_id}")
        print(f"   [TIME] 最大等待时间: {max_wait_time} 秒")
        print(f"   [LOOP] 轮询间隔: {poll_interval} 秒")

        start_time = time.time()
        attempt_count = 0

        while time.time() - start_time < max_wait_time:
            attempt_count += 1
            print(f"\n[LOOP] 第 {attempt_count} 次查询任务状态")

            try:
                result = self.query_task(task_id)
                status = result.get('status', '').lower()

                print(f"   [STATUS] 当前状态: {status}")
                logger.info(f"任务状态: {status}")

                if status == TaskStatus.COMPLETED.value:
                    print(f"   [SUCCESS] 任务完成！")
                    logger.info(f"任务完成: {task_id}")
                    return result
                elif status == TaskStatus.FAILED.value:
                    print(f"   [ERROR] 任务失败！")
                    logger.error(f"任务失败: {task_id}")
                    return result
                else:
                    print(f"   [PAUSE]  任务进行中，{poll_interval} 秒后再次查询...")

                time.sleep(poll_interval)

            except Exception as e:
                print(f"   [ERROR] 查询任务状态失败: {e}")
                logger.error(f"查询任务状态失败: {e}")
                print(f"   [PAUSE]  {poll_interval} 秒后重试...")
                time.sleep(poll_interval)

        print(f"\n[TIMER] 等待任务完成超时！")
        print(f"   🆔 任务ID: {task_id}")
        print(f"   [TIME]  总用时: {time.time() - start_time:.1f} 秒")
        print(f"   [LOOP] 总查询次数: {attempt_count}")

        raise TimeoutError(f"等待任务完成超时: {task_id}")

    def create_video_with_image(
        self,
        images: List[str],
        prompt: str,
        model: str = "sora-2",
        orientation: str = "landscape",
        size: str = "small",
        duration: int = 10,
        watermark: bool = False
    ) -> Dict:
        """
        使用Sora2 API创建图生视频任务 (v1版本)
        
        Args:
            images: 图片URL列表
            prompt: 视频生成提示词
            model: 模型名称 (默认 sora-2)
            orientation: 输出方向 ('portrait' 竖屏 或 'landscape' 横屏)
            size: 视频尺寸 ('small' 720p 或 'large')
            duration: 视频时长 (10 或 15)
            watermark: 是否添加水印 (默认 False)
            
        Returns:
            任务创建响应，包含id和status
        """
        print(f"\n[VIDEO] 开始使用 Sora2 v1 API 创建图生视频任务")
        print(f"   [TEXT] 提示词: {prompt}")
        print(f"   [MODEL] 模型: {model}")
        print(f"   [ORIENTATION] 方向: {orientation}")
        print(f"   [SIZE] 尺寸: {size}")
        print(f"   [DURATION] 时长: {duration}秒")
        print(f"   [WATERMARK] 水印: {watermark}")
        
        payload = {
            "images": images,
            "prompt": prompt,
            "model": model,
            "orientation": orientation,
            "size": size,
            "duration": duration,
            "watermark": watermark
        }
        
        print(f"   [IMAGE] 图片数量: {len(images)}")
        for i, img in enumerate(images, 1):
            print(f"      图片{i}: {img}")
        
        print(f"   [DATA] 构建的请求数据包:")
        for key, value in payload.items():
            print(f"      {key}: {value}")

        logger.info(f"创建 Sora2 v1 图生视频任务: {prompt}")
        result = self._make_request('POST', '/v1/video/create', json=payload)

        print(f"   [OK] Sora2 v1 任务创建请求完成")
        return result

    def query_video_task(self, task_id: str) -> Dict:
        """
        查询视频任务状态 (v1版本)
        
        Args:
            task_id: 任务ID (例如: sora-2:task_01k6x15vhrff09dkkqjrzwhm60)

        Returns:
            任务状态响应，包含status和video_url
        """
        print(f"\n[SEARCH] 开始查询视频任务状态 (v1 API)")
        print(f"   🆔 任务ID: {task_id}")

        logger.info(f"查询视频任务状态: {task_id}")
        result = self._make_request('GET', '/v1/video/query', params={'id': task_id})

        print(f"   [OK] 视频任务状态查询完成")
        return result
