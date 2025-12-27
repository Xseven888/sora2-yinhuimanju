"""
阿里云 OSS 上传工具
支持图片和视频上传到阿里云 OSS（公共写模式）
"""

import os
import uuid
from pathlib import Path
from typing import Optional
import requests
import urllib3
from loguru import logger

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OSSUploader:
    """阿里云 OSS 上传器"""
    
    def __init__(self, bucket_domain: str):
        """初始化 OSS 上传器
        
        Args:
            bucket_domain: Bucket 域名（外网访问地址），例如: https://your-bucket.oss-cn-hangzhou.aliyuncs.com
        """
        self.bucket_domain = bucket_domain.strip()
        
        if not self.bucket_domain:
            raise ValueError("需要配置 Bucket 域名")
        
        # 确保 Bucket 域名格式正确
        if not self.bucket_domain.startswith('http://') and not self.bucket_domain.startswith('https://'):
            self.bucket_domain = f"https://{self.bucket_domain}"
        
        # 尝试从 Bucket 域名解析 Endpoint 和 Bucket 名称（用于日志记录）
        parsed = OSSUploader._parse_bucket_domain(self.bucket_domain)
        if parsed:
            self.endpoint = parsed['endpoint']
            self.bucket_name = parsed['bucket_name']
            logger.info(f"从 Bucket 域名解析出 Endpoint: {self.endpoint}, Bucket 名称: {self.bucket_name}")
        
        logger.info(f"OSS 公共写模式初始化成功: bucket_domain={self.bucket_domain}")
    
    @staticmethod
    def _parse_bucket_domain(bucket_domain: str) -> Optional[dict]:
        """从 Bucket 域名解析出 Endpoint 和 Bucket 名称
        
        Args:
            bucket_domain: Bucket 域名，例如: https://my-bucket.oss-cn-hangzhou.aliyuncs.com
        
        Returns:
            包含 endpoint 和 bucket_name 的字典，如果解析失败返回 None
        """
        try:
            # 移除协议和尾部斜杠
            domain = bucket_domain.replace('https://', '').replace('http://', '').rstrip('/')
            
            # 标准格式: bucket-name.oss-region.aliyuncs.com
            # 或者: bucket-name.oss-cn-region.aliyuncs.com
            parts = domain.split('.')
            
            if len(parts) >= 4 and 'aliyuncs.com' in '.'.join(parts[-2:]):
                # 找到包含 'oss' 的部分（可能是 'oss' 或 'oss-cn-xxx'）
                oss_index = -1
                for i, part in enumerate(parts):
                    if part.startswith('oss'):
                        oss_index = i
                        break
                
                if oss_index > 0:
                    # Bucket 名称是第一部分
                    bucket_name = parts[0]
                    
                    # Endpoint 是从 oss 开始到结尾的部分
                    endpoint_parts = parts[oss_index:]
                    endpoint_domain = '.'.join(endpoint_parts)
                    endpoint = f"https://{endpoint_domain}"
                    
                    logger.info(f"成功解析 Bucket 域名: bucket_name={bucket_name}, endpoint={endpoint}")
                    return {
                        'bucket_name': bucket_name,
                        'endpoint': endpoint
                    }
            
            logger.warning(f"无法解析 Bucket 域名格式: {bucket_domain}")
            return None
        except Exception as e:
            logger.error(f"解析 Bucket 域名失败: {e}")
            return None
    
    def _generate_object_key(self, file_path: str, prefix: str = '') -> str:
        """生成 OSS 对象键（文件路径）
        
        Args:
            file_path: 本地文件路径
            prefix: 前缀路径，如 'images/' 或 'videos/'
        
        Returns:
            OSS 对象键，如 'images/8位随机ID.jpg'
        """
        p = Path(file_path)
        suffix = p.suffix.lower()
        
        # 生成唯一文件名（只使用8位随机ID + 原文件扩展名）
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        filename = f"{unique_id}{suffix}"
        
        # 组合完整路径（去掉日期分层）
        if prefix:
            object_key = f"{prefix.rstrip('/')}/{filename}"
        else:
            object_key = filename
        
        return object_key
    
    def _guess_content_type(self, suffix: str) -> str:
        """根据文件后缀猜测 Content-Type"""
        s = suffix.lower()
        
        # 图片类型
        image_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.tif': 'image/tiff',
            '.tiff': 'image/tiff',
        }
        
        # 视频类型
        video_types = {
            '.mp4': 'video/mp4',
            '.m4v': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
        }
        
        if s in image_types:
            return image_types[s]
        elif s in video_types:
            return video_types[s]
        else:
            return 'application/octet-stream'
    
    def upload_file(self, file_path: str, prefix: str = '', custom_key: Optional[str] = None) -> str:
        """上传文件到 OSS（公共写模式）
        
        Args:
            file_path: 本地文件路径
            prefix: 前缀路径，如 'images/' 或 'videos/'
            custom_key: 自定义对象键，如果提供则使用此值
        
        Returns:
            文件的访问 URL
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 生成对象键
        if custom_key:
            object_key = custom_key
        else:
            object_key = self._generate_object_key(file_path, prefix)
        
        # 获取 Content-Type
        content_type = self._guess_content_type(p.suffix)
        
        logger.info(f"开始上传文件到 OSS: {file_path} -> {object_key}")
        
        # 使用公共写模式（HTTP PUT 直接上传）
        upload_url = f"{self.bucket_domain.rstrip('/')}/{object_key}"
        
        # 获取文件大小
        file_size = p.stat().st_size
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 准备请求头
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(file_size),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 创建 session 并禁用代理
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        
        logger.info(f"开始上传到 OSS（公共写模式）: {upload_url}, 文件大小: {file_size} bytes")
        
        try:
            try:
                response = session.put(
                    upload_url,
                    data=file_data,
                    headers=headers,
                    timeout=300,
                    verify=True  # 保持 SSL 验证
                )
            except requests.exceptions.SSLError as ssl_err:
                # 如果 SSL 验证失败，尝试不验证（仅作为备选方案）
                logger.warning(f"SSL 验证失败，尝试不验证 SSL: {ssl_err}")
                response = session.put(
                    upload_url,
                    data=file_data,
                    headers=headers,
                    timeout=300,
                    verify=False  # 不验证 SSL（仅用于调试）
                )
            
            if response.status_code == 200:
                # 上传成功，返回访问 URL
                url = upload_url
                logger.info(f"文件上传成功（公共写模式）: {url}")
                return url
            else:
                error_msg = response.text[:500] if response.text else "无响应内容"
                logger.error(f"OSS 公共写模式上传失败: 状态码={response.status_code}, 响应={error_msg}")
                raise RuntimeError(
                    f"OSS 上传失败（状态码: {response.status_code}）。\n"
                    f"请检查 Bucket 是否已开启公共读写权限。\n"
                    f"错误详情: {error_msg}"
                )
        
        except requests.exceptions.SSLError as ssl_err:
            logger.error(f"OSS 上传 SSL 错误: {ssl_err}")
            raise RuntimeError(
                f"OSS 上传失败：SSL 连接错误。\n"
                f"这可能是由于网络问题或 OSS 配置问题导致的。\n"
                f"建议：\n"
                f"1. 检查网络连接是否正常\n"
                f"2. 检查 Bucket 域名是否正确\n"
                f"3. 确认 Bucket 已开启公共读写权限\n"
                f"错误详情: {str(ssl_err)}"
            )
        except Exception as e:
            logger.error(f"上传文件到 OSS 失败: {str(e)}")
            raise
    
    def upload_image(self, image_path: str) -> str:
        """上传图片到 OSS
        
        Args:
            image_path: 图片文件路径
        
        Returns:
            图片的访问 URL
        """
        return self.upload_file(image_path, prefix='images')
    
    def upload_video(self, video_path: str) -> str:
        """上传视频到 OSS
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            视频的访问 URL
        """
        return self.upload_file(video_path, prefix='videos')
    
    @staticmethod
    def is_configured(bucket_domain: str = '') -> bool:
        """检查 OSS 是否已配置
        
        Args:
            bucket_domain: Bucket 域名
        
        Returns:
            是否已配置
        """
        try:
            bucket_domain = bucket_domain.strip()
            return bool(bucket_domain)
        except Exception as e:
            logger.error(f"检查 OSS 配置失败: {e}")
            return False

