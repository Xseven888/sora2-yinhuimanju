"""
带货视频流水线线程：
1) 上传主图到图床
2) 直接调用 NanoBanana `/v1/images/generations` 生成白底图，解析得到白底图URL
3) 使用白底图与商品标题，调用 gpt-5-chat-latest 生成视频提示词
4) 创建 Sora2 视频生成任务，写入 tasks 表（不再使用 goods_videos 表）

信号：
- progress(str): 进度更新
- finished(bool, dict): 成功/失败及返回数据或错误信息
"""

import re
import json
import requests
from typing import Dict, Any, Optional, List
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger

from utils.nanobanana_util import upload_image_to_bed, call_nano_banana_image_generation
from constants import API_BASE_URL, API_CHAT_COMPLETIONS_URL
from database_manager import db_manager
from sora_client import SoraClient


def _extract_image_url_from_chat_response(resp: Dict[str, Any]) -> Optional[str]:
    """从 /v1/chat/completions 返回的JSON中提取第一个 image_url.url"""
    try:
        choices = resp.get('choices') or []
        if choices:
            msg = choices[0].get('message') or {}
            content = msg.get('content') or []
            # content 可能是 list[dict]
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'image_url':
                    url_obj = part.get('image_url') or {}
                    url = url_obj.get('url')
                    if url:
                        return url
            # 若没有 image_url，尝试从 text 中提取URL
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text = part.get('text') or ''
                    m = re.search(r'https?://\S+', text)
                    if m:
                        return m.group(0)
        # 兼容一些返回结构不标准的情况
        m2 = re.search(r'https?://\S+', str(resp))
        if m2:
            return m2.group(0)
    except Exception as e:
        logger.error(f"解析白底图URL失败: {e}")
    return None


def _extract_image_url_from_generation_response(resp: Dict[str, Any]) -> Optional[str]:
    """从 /v1/images/generations 返回的JSON中尽可能提取图片URL。
    常见结构：{"data": [{"url": "..."}]}
    兼容其他可能字段：image_url、images[0].url、顶层 url；若为原始文本（raw）则用正则提取。
    """
    try:
        if not isinstance(resp, dict):
            return None
        raw = resp.get('raw')
        if isinstance(raw, str):
            m = re.search(r"https?://[^\s\"]+", raw)
            return m.group(0) if m else None
        data = resp.get('data')
        if isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, dict):
                if isinstance(item.get('url'), str):
                    return item.get('url')
                iu = item.get('image_url')
                if isinstance(iu, str):
                    return iu
                if isinstance(iu, dict) and isinstance(iu.get('url'), str):
                    return iu.get('url')
                images = item.get('images')
                if isinstance(images, list) and images:
                    first = images[0]
                    if isinstance(first, dict) and isinstance(first.get('url'), str):
                        return first.get('url')
        if isinstance(resp.get('url'), str):
            return resp.get('url')
        iu = resp.get('image_url')
        if isinstance(iu, str):
            return iu
        if isinstance(iu, dict) and isinstance(iu.get('url'), str):
            return iu.get('url')
    except Exception as e:
        logger.error(f"解析生成接口返回URL失败: {e}")
    return None


class GoodsVideoPipelineThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, dict)  # success, data_or_error

    def __init__(self, title: str, main_image_path: str,
                 main_prompt_text: str, scene_prompt_text: str,
                 parent=None):
        super().__init__(parent)
        self.title = title.strip()
        self.main_image_path = main_image_path
        self.main_prompt_text = main_prompt_text.strip()
        self.scene_prompt_text = scene_prompt_text.strip()

    def _emit(self, msg: str):
        self.progress.emit(msg)
        logger.info(msg)

    def _log_info(self, msg: str):
        try:
            db_manager.add_log('INFO', f"[GoodsPipeline] {msg}")
        except Exception:
            pass
        logger.info(msg)

    def _log_error(self, msg: str):
        try:
            db_manager.add_log('ERROR', f"[GoodsPipeline] {msg}")
        except Exception:
            pass
        logger.error(msg)

    def run(self):
        try:
            if not self.title:
                raise RuntimeError("商品标题不能为空")
            if not self.main_image_path:
                raise RuntimeError("请先选择主图")

            self._log_info(f"开始流水线：title='{self.title[:60]}', image='{self.main_image_path}'")
            self._emit("开始上传主图到图床…")
            main_image_url = upload_image_to_bed(self.main_image_path)
            self._emit(f"主图已上传: {main_image_url}")
            self._log_info(f"主图上传完成，URL={main_image_url}")

            self._emit("调用 NanoBanana 生成白底图…")
            generation_prompt = (
                f"{self.main_prompt_text}\n"
                f"商品标题：{self.title}\n"
                f"风格要求：纯白背景，居中构图，简洁干净，高分辨率，正方形或接近正方形。\n"
                f"参考主图链接（可忽略）：{main_image_url}"
            )
            nb_resp = call_nano_banana_image_generation(
                prompt=generation_prompt,
                model="nano-banana",
                timeout=180,
            )
            white_image_url = _extract_image_url_from_generation_response(nb_resp)
            if not white_image_url:
                raise RuntimeError("未能从返回中解析白底图URL")
            self._emit(f"白底图生成完成: {white_image_url}")
            self._log_info(f"白底图生成完成，URL={white_image_url}")

            # 生成视频提示词（gpt-5-chat-latest），包含白底图与标题
            self._emit("根据白底图与标题生成视频提示词…")

            # 固定 base_url，api_key 来自配置
            base_url = API_BASE_URL
            api_key = db_manager.load_config('api_key', '') or ''
            if not api_key:
                raise RuntimeError("未配置API Key")
            self._log_info("提示词生成：调用 gpt-5-chat-latest /v1/chat/completions")

            url = API_CHAT_COMPLETIONS_URL
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": self.scene_prompt_text}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"商品标题：{self.title}"},
                        {"type": "image_url", "image_url": {"url": white_image_url}},
                    ],
                },
            ]

            payload = {
                "model": "gpt-5-chat-latest",
                "stream": False,
                "messages": messages,
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f"生成提示词失败: {resp.status_code} - {resp.text}")
            j = resp.json()
            # 提取文本提示词（兼容字符串与分段内容两种结构）
            video_prompt: str = ""
            try:
                choices = j.get('choices') or []
                if choices:
                    msg = choices[0].get('message') or {}
                    content = msg.get('content')
                    if isinstance(content, str):
                        video_prompt = content.strip()
                    elif isinstance(content, list):
                        texts: List[str] = []
                        for part in content:
                            if isinstance(part, dict):
                                if part.get('type') == 'text' and isinstance(part.get('text'), str):
                                    texts.append(part.get('text'))
                        video_prompt = "\n".join([t.strip() for t in texts if isinstance(t, str) and t.strip()])
                    else:
                        # 有些实现可能把文本放在 message.text
                        t = msg.get('text')
                        if isinstance(t, str) and t.strip():
                            video_prompt = t.strip()
                # 顶层兜底：某些返回可能包含 output_text
                if not video_prompt and isinstance(j.get('output_text'), str):
                    video_prompt = j.get('output_text').strip()
            except Exception as _e:
                logger.warning(f"解析提示词结构时异常：{_e}")
            if not video_prompt:
                # 最后兜底才使用原始JSON文本，避免再次出现未解析情况
                logger.warning("未能解析到结构化提示词，使用原始字符串兜底。")
                video_prompt = json.dumps(j, ensure_ascii=False)
            preview_text = video_prompt[:120].replace('\n', ' ')
            self._log_info(f"提示词生成完成，长度={len(video_prompt)}，预览='{preview_text}'")

            # 提示词生成完成，直接进入创建任务（不再写入 goods_videos）
            self._emit("提示词生成完成，准备创建视频任务…")

            # 创建视频生成任务（Sora2），竖屏15秒，使用白底图
            self._emit("创建视频生成任务…")
            client = SoraClient(base_url=base_url, api_key=api_key)
            result = client.create_sora2_video(
                prompt=video_prompt,
                model="sora-2",
                aspect_ratio="9:16",
                hd=False,
                duration="15",
                images=[white_image_url],
            )

            # 解析 task_id
            task_id = None
            try:
                task_id = result.get('task_id') or result.get('id')
            except Exception:
                task_id = None
            if not task_id:
                raise RuntimeError(f"未获取到任务ID: {result}")
            self._log_info(f"Sora2 任务创建成功，task_id={task_id}")

            # 写入 tasks 表（与主流程保持一致字段）
            task_data = {
                'task_id': task_id,
                'prompt': video_prompt,
                'model': 'sora-2',
                'orientation': 'portrait',
                'size': 'small',
                'duration': 15,
                'images': [white_image_url],
                'status': 'pending',
                'progress': 0,
            }
            db_manager.add_task(task_data)
            self._log_info(f"tasks 记录已写入，task_id={task_id}")

            self._emit("流水线完成")
            self._log_info("流水线完成")
            self.finished.emit(True, {
                'main_image_url': main_image_url,
                'white_image_url': white_image_url,
                'video_prompt': video_prompt,
                'task_id': task_id,
            })

        except Exception as e:
            err = str(e)
            logger.error(f"带货流水线失败: {err}")
            self._log_error(f"流水线失败：{err}")
            self.finished.emit(False, {'error': err})
