# 阿里云 OSS 上传工具

这是一个独立的阿里云 OSS 上传工具模块，可以方便地集成到任何 Python 项目中。

## 功能特性

- ✅ 支持图片和视频上传到阿里云 OSS
- ✅ 使用公共写模式（HTTP PUT 直接上传，需要 Bucket 开启公共读写权限）
- ✅ 自动从 Bucket 域名解析 Endpoint 和 Bucket 名称
- ✅ 自动生成唯一文件名（8位随机ID + 扩展名）
- ✅ 按类型自动分类存储（图片到 `images/`，视频到 `videos/`）
- ✅ 完善的错误处理和日志记录
- ✅ 配置简单，只需提供 Bucket 域名即可

## 依赖安装

```bash
pip install requests
pip install loguru  # 可选，如果使用日志功能
```

**注意**：本工具使用公共写模式（HTTP PUT），不需要安装 `oss2` 库。

## 完整代码

将以下代码保存为 `oss_uploader.py`：

```python
"""
阿里云 OSS 上传工具
支持图片和视频上传到阿里云 OSS
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Callable
import requests
import urllib3

# 本工具使用公共写模式（HTTP PUT），不需要 oss2 库

# 如果使用 loguru，取消下面的注释
# from loguru import logger
# 如果不使用 loguru，可以使用 print 或自定义日志函数
def logger_info(msg): print(f"[INFO] {msg}")
def logger_warning(msg): print(f"[WARNING] {msg}")
def logger_error(msg): print(f"[ERROR] {msg}")
logger = type('Logger', (), {'info': logger_info, 'warning': logger_warning, 'error': logger_error})()


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
        
        # 禁用 SSL 警告（如果遇到 SSL 问题）
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
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
```

## 使用方法

### 基本使用

```python
from oss_uploader import OSSUploader

# 初始化上传器（只需要 Bucket 域名）
uploader = OSSUploader(
    bucket_domain='https://your-bucket.oss-cn-hangzhou.aliyuncs.com'
)

# 上传图片
image_url = uploader.upload_image('/path/to/image.jpg')
print(f"图片 URL: {image_url}")

# 上传视频
video_url = uploader.upload_video('/path/to/video.mp4')
print(f"视频 URL: {video_url}")

# 上传到自定义路径
custom_url = uploader.upload_file('/path/to/file.pdf', prefix='documents')
print(f"文件 URL: {custom_url}")
```

### 从配置文件读取

```python
from oss_uploader import OSSUploader
import json

# 读取配置
with open('config.json', 'r') as f:
    config = json.load(f)

# 初始化上传器
uploader = OSSUploader(
    bucket_domain=config.get('oss_bucket_domain', '')
)

# 上传文件
image_url = uploader.upload_image('/path/to/image.jpg')
```

## 配置说明

### 必需参数

- **bucket_domain**: Bucket 域名（外网访问地址）
  - 格式：`https://your-bucket.oss-cn-hangzhou.aliyuncs.com`
  - 系统会自动从中解析出 Endpoint 和 Bucket 名称
  - **注意**：需要确保 Bucket 已开启公共读写权限

## 文件存储结构

上传的文件会按以下结构存储：

```
images/
  └── 8位随机ID.jpg
  └── 8位随机ID.png
videos/
  └── 8位随机ID.mp4
  └── 8位随机ID.mov
```

- 图片存储在 `images/` 目录下
- 视频存储在 `videos/` 目录下
- 文件名格式：`8位随机ID.扩展名`

## 注意事项

1. **Bucket 权限**：需要确保 Bucket 已开启公共读写权限，否则上传会失败
2. **Bucket 设置**：
   - 建议设置为「公共读」或配置跨域规则（如果需要）
3. **费用**：OSS 按使用量计费，请注意存储和流量费用
4. **SSL 错误**：如果遇到 SSL 错误，请检查网络连接和 Bucket 域名是否正确

## 错误处理

代码已包含完善的错误处理，常见错误：

- **文件不存在**：`FileNotFoundError`
- **配置不完整**：`ValueError`
- **上传失败**：`RuntimeError`（包含详细错误信息）
- **SSL 错误**：会提供详细的解决建议

## 集成到其他项目

1. 将 `oss_uploader.py` 复制到你的项目中
2. 安装依赖：`pip install requests`
3. 在代码中导入并使用：

```python
from oss_uploader import OSSUploader

# 初始化并上传（只需要 Bucket 域名）
uploader = OSSUploader(
    bucket_domain='https://your-bucket.oss-cn-hangzhou.aliyuncs.com'
)

url = uploader.upload_image('/path/to/image.jpg')
```

## 许可证

本代码可自由使用和修改。

