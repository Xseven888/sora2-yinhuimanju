"""
图片上传线程 - 使用文件上传接口（multipart/form-data）

按照 OpenAPI 规范：
- POST {BASE_URL}/v1/files
- Header: Authorization: Bearer <API_KEY>（如果配置了 api_key）
- Body: form-data 字段 `file` 为二进制文件
- 响应：JSON，优先读取 `url` 字段作为可访问地址
"""

from pathlib import Path
import requests
from requests.exceptions import ProxyError, ConnectionError
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from database_manager import db_manager
from constants import API_BASE_URL

class ImageUploadThread(QThread):
    """图片上传线程 - 通过 BASE_URL/v1/files 上传"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)  # success, message, image_url

    def __init__(self, file_path, token=None):
        super().__init__()
        self.file_path = file_path
        # token 参数兼容旧调用，不再使用
        self.running = True

    def _guess_content_type(self, suffix: str) -> str:
        s = suffix.lower()
        if s in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        if s == '.png':
            return 'image/png'
        if s == '.gif':
            return 'image/gif'
        if s == '.webp':
            return 'image/webp'
        if s in ['.bmp']:
            return 'image/bmp'
        if s in ['.tif', '.tiff']:
            return 'image/tiff'
        return 'application/octet-stream'

    def run(self):
        """将本地图片上传到 {api_base_url}/v1/files 并返回URL"""
        try:
            p = Path(self.file_path)
            if not p.exists() or not p.is_file():
                raise FileNotFoundError(f"图片文件不存在: {self.file_path}")

            # 从配置读取 base_url 与 api_key
            base_url = API_BASE_URL
            api_key = db_manager.load_config('api_key', '')
            endpoint = f"{base_url.rstrip('/')}/v1/files"

            logger.info(f"endpoint: {endpoint}")
            logger.info(f"api_key: {api_key}")

            suffix = p.suffix or '.jpg'
            content_type = self._guess_content_type(suffix)

            headers = {
                'Accept': 'application/json',
            }
            if api_key:
                headers['Authorization'] = f"Bearer {api_key}"

            f = open(self.file_path, 'rb')
            files = {
                'file': (p.name, f, content_type)
            }

            self.progress.emit(f"正在上传图片到文件服务: {p.name}")
            logger.info(f"开始上传图片: path={self.file_path} endpoint={endpoint} ct={content_type}")

            # 使用独立会话且禁用系统代理，避免 127.0.0.1:7890 等代理导致连接失败
            session = requests.Session()
            session.trust_env = False
            try:
                resp = session.post(
                    endpoint,
                    files=files,
                    headers=headers,
                    timeout=180,
                    proxies={"http": None, "https": None}
                )
            except (ProxyError, ConnectionError) as e:
                logger.warning(f"首次上传因代理/网络异常失败，将在禁用代理下重试: {e}")
                try:
                    resp = requests.post(
                        endpoint,
                        files=files,
                        headers=headers,
                        timeout=180,
                        proxies={"http": None, "https": None}
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
                    err = f"解析响应失败（非JSON）: {resp.text[:200]}"
                    logger.error(err)
                    self.finished.emit(False, err, "")
                    return

                image_url = data.get('url') or ''
                # 兼容某些服务不返回 url，仅返回 id/filename
                if not image_url:
                    file_id = data.get('id')
                    filename = data.get('filename') or p.name
                    logger.warning(f"响应未包含 url，id={file_id}, filename={filename}")
                    # 尝试构造兼容的下载地址（若服务支持此路径）
                    # 注意：若服务不支持，则仍返回空字符串供上层判定。
                    possible = f"{base_url.rstrip('/')}/v1/files/{file_id}/content" if file_id else ''
                    image_url = possible

                if image_url:
                    logger.info(f"图片上传成功，URL: {image_url}")
                    self.finished.emit(True, "图片上传成功", image_url)
                else:
                    msg = "上传成功但响应未提供可访问URL"
                    logger.warning(msg)
                    self.finished.emit(True, msg, "")
            else:
                err = f"上传失败: {resp.status_code} - {resp.text[:200]}"
                logger.error(err)
                self.finished.emit(False, err, "")

        except Exception as e:
            logger.exception(e)
            self.finished.emit(False, f"上传出错: {str(e)}", "")
