"""
启动时版本检查线程

从 Gitee 最新发布接口获取版本信息，比较本地与远端版本，
将结果通过信号通知主窗口以弹出更新提示。
"""

from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
import requests

from constants import APP_VERSION, GITEE_LATEST_RELEASE_API, GITEE_RELEASES_URL
from version import compare_versions


class VersionCheckThread(QThread):
    """异步版本检查线程"""

    check_finished = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._latest_api = GITEE_LATEST_RELEASE_API

    def _extract_version(self, data: dict) -> str:
        # 尝试多个字段
        for key in ("tag_name", "name", "title"):
            v = (data or {}).get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def _extract_release_url(self, data: dict) -> str:
        # Gitee 可能没有 html_url，回退到 Releases 页面
        url = (data or {}).get("html_url") or (data or {}).get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
        return GITEE_RELEASES_URL

    def _extract_body(self, data: dict) -> str:
        # 解析更新说明正文，兼容常见字段
        for key in ("body", "description", "notes", "changelog"):
            v = (data or {}).get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def run(self):
        result = {
            "ok": False,
            "has_update": False,
            "current_version": APP_VERSION,
            "latest_version": "",
            "release_url": GITEE_RELEASES_URL,
            "release_body": "",
            "error": "",
        }
        try:
            session = requests.Session()
            session.trust_env = False  # 禁用系统代理
            session.proxies = {"http": None, "https": None}

            logger.info("正在检查最新版本...")
            resp = session.get(self._latest_api, timeout=8)
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                self.check_finished.emit(result)
                return

            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            latest = self._extract_version(data)
            release_url = self._extract_release_url(data)
            release_body = self._extract_body(data)

            result["latest_version"] = latest or ""
            result["release_url"] = release_url
            result["release_body"] = release_body or ""
            result["ok"] = True

            if latest:
                cmp = compare_versions(APP_VERSION, latest)
                result["has_update"] = (cmp < 0)
            else:
                result["has_update"] = False

        except requests.exceptions.ProxyError as e:
            logger.warning(f"版本检查代理错误: {e}")
            result["error"] = f"ProxyError: {e}"
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"版本检查连接错误: {e}")
            result["error"] = f"ConnectionError: {e}"
        except Exception as e:
            logger.error(f"版本检查失败: {e}")
            result["error"] = str(e)
        finally:
            self.check_finished.emit(result)
