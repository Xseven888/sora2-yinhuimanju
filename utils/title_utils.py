r"""
AI 标题生成与文件名清理工具
"""

import re
import requests
from constants import API_CHAT_COMPLETIONS_URL
from typing import Optional


def sanitize_filename(name: str, max_length: int = 80) -> str:
    """清理标题为安全文件名。
    - 去除非法字符：<>:"/\|?*
    - 将连续空白压缩为一个空格
    - 去除首尾空白
    - 限制最大长度
    """
    if not name:
        return "untitled"
    # 去掉换行等
    name = name.replace("\n", " ").replace("\r", " ")
    # 移除非法字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 压缩空白
    name = re.sub(r"\s+", " ", name).strip()
    # 过长截断
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    # 空名兜底
    return name or "untitled"


def generate_ai_title(api_key: str, system_prompt: str, task_prompt: Optional[str] = None) -> Optional[str]:
    """调用聊天补全接口生成视频标题（使用 gpt-5-chat-latest）。
    要求只返回一个标题，不包含任何额外内容。失败返回 None。
    """
    try:
        if not api_key:
            return None
        base_url = API_CHAT_COMPLETIONS_URL
        # 组装消息：系统指令加入严格规则，用户消息仅传递生成提示词
        rules = (
            "你是视频标题生成助手。只返回一个中文视频标题，不要返回任何解释、标注或额外内容；"
            "不要使用引号、编号、前缀或后缀；不要换行；长度不超过30个字，风格有趣吸引人。"
        )
        system_text = rules if not system_prompt else (rules + "\n\n" + system_prompt)
        user_text = task_prompt or ""
        payload = {
            "model": "gpt-5-chat-latest",
            "messages": [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_text}]
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_text}]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 64
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        resp = requests.post(base_url, json=payload, headers=headers, timeout=20)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # 从响应中提取文本
        try:
            choices = data.get("choices") or []
            if not choices:
                return None
            content = choices[0]["message"]["content"]
            if isinstance(content, list):
                # 提取第一个文本片段
                for part in content:
                    if part.get("type") == "text" and part.get("text"):
                        return sanitize_filename(part["text"])  # 清理
                return None
            elif isinstance(content, str):
                return sanitize_filename(content)
            return None
        except Exception:
            return None
    except Exception:
        return None
