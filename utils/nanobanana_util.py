"""
nanobanana_util

功能：
- 将本地图片上传到图床（与主页添加任务一致的上传方式），获取可访问的图片URL。
- 使用 chat completions 接口（gemini-2.5-flash-image）结合提示词与图片URL进行调用。
- 提供命令行入口 main，用法：

  python3 utils/nanobanana_util.py --prompt "修改这个图片" --image /path/to/image.png \
    [--api-key YOUR_API_KEY] [--base-url https://api.shaohua.fun]

默认从配置表读取 `api_key`、`api_base_url`、`image_token`，命令行传入则覆盖。
"""

import sys
import argparse
from pathlib import Path
import requests
import http.client
import json
from typing import Optional, Dict, Any

from database_manager import db_manager
from constants import API_BASE_URL, API_HOST, API_CHAT_COMPLETIONS_URL


def upload_image_to_bed(file_path: str, token: Optional[str] = None, timeout: int = 180) -> str:
    if not file_path:
        raise ValueError("file_path 不能为空")
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"图片文件不存在: {file_path}")

    base_url = API_BASE_URL
    api_key = db_manager.load_config('api_key', '') or ''
    endpoint = f"{base_url.rstrip('/')}/v1/files"

    def _ct(suf: str) -> str:
        s = suf.lower()
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

    suffix = p.suffix or '.jpg'
    content_type = _ct(suffix)

    headers = {
        'Accept': 'application/json',
    }
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"

    f = open(file_path, 'rb')
    files = {
        'file': (p.name, f, content_type)
    }

    session = requests.Session()
    session.trust_env = False
    try:
        resp = session.post(
            endpoint,
            files=files,
            headers=headers,
            timeout=timeout,
            proxies={"http": None, "https": None}
        )
    finally:
        try:
            session.close()
        except Exception:
            pass
        try:
            f.close()
        except Exception:
            pass

    if resp.status_code == 200:
        try:
            data = resp.json()
        except Exception:
            raise RuntimeError(f"解析响应失败（非JSON）: {resp.text[:200]}")

        image_url = data.get('url') or ''
        if not image_url:
            file_id = data.get('id')
            filename = data.get('filename') or p.name
            possible = f"{base_url.rstrip('/')}/v1/files/{file_id}/content" if file_id else ''
            image_url = possible

        if image_url:
            return image_url
        raise RuntimeError("上传成功但响应未提供可访问URL")

    raise RuntimeError(f"上传失败: {resp.status_code} - {resp.text[:200]}")


def call_image_chat_completion(
    prompt: str,
    image_url: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gemini-2.5-flash-image",
    stream: bool = False,
    timeout: int = 180,
) -> Dict[str, Any]:
    """调用 /v1/chat/completions 接口，使用指定 prompt 与 image_url。
    JSON 结构严格按用户给的 curl 示例：messages[0].content 包含 text 与 image_url 两段。
    返回响应 JSON，非 200 状态或解析失败抛出异常。
    """
    if not prompt:
        raise ValueError("prompt 不能为空")
    if not image_url:
        raise ValueError("image_url 不能为空")

    # 强制使用固定 base_url 与配置中的 api_key
    base_url = API_BASE_URL
    api_key = db_manager.load_config('api_key', '') or ''
    if not api_key:
        raise RuntimeError("未配置 API Key（config.api_key），且未通过参数提供")

    url = API_CHAT_COMPLETIONS_URL
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "stream": stream,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"API 调用失败: {resp.status_code} - {resp.text}")
    return resp.json()


def call_nano_banana_image_generation(
    prompt: str,
    model: str = "nano-banana",
    timeout: int = 180,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """直接调用 NanoBanana 图片生成接口 /v1/images/generations。

    使用标准库 http.client 建立 HTTPS 连接，固定 base_url 为 https://api.shaohua.fun，
    并从配置表读取 api_key（config.api_key）。

    参数：
    - prompt: 提示词
    - model: 模型名，默认 nano-banana
    - timeout: 连接/读取超时秒数
    - extra: 额外可选参数（如 size、n 等）会并入 payload

    返回：响应 JSON；非 200 状态码时抛出异常。
    """
    if not prompt:
        raise ValueError("prompt 不能为空")

    api_key = db_manager.load_config('api_key', '') or ''
    if not api_key:
        raise RuntimeError("未配置 API Key（config.api_key）")

    host = API_HOST
    path = '/v1/images/generations'

    payload: Dict[str, Any] = {
        "prompt": prompt,
        "model": model,
    }
    if extra:
        # 仅合并简单键值对，避免覆盖核心字段
        for k, v in extra.items():
            if k not in payload:
                payload[k] = v

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    conn = http.client.HTTPSConnection(host, timeout=timeout)
    try:
        body = json.dumps(payload)
        conn.request('POST', path, body, headers)
        res = conn.getresponse()
        data = res.read()
        text = data.decode('utf-8')

        if res.status != 200:
            raise RuntimeError(f"NanoBanana 接口失败: {res.status} - {text}")

        try:
            return json.loads(text)
        except Exception:
            # 返回原始文本以便上层记录
            return {"raw": text}
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="nanobanana_util: 上传图片到图床并调用图像生成接口")
    parser.add_argument("--prompt", required=True, help="提示词文本，例如：修改这个图片")
    parser.add_argument("--image", required=False, help="(可选) 本地图片路径，例如：/path/to/image.png")
    parser.add_argument("--api-key", dest="api_key", default=None, help="(已忽略) 始终使用配置 config.api_key")
    from constants import API_BASE_URL
    parser.add_argument("--base-url", dest="base_url", default=None, help=f"(已忽略) 始终使用 {API_BASE_URL}")
    parser.add_argument("--model", default="nano-banana", help="模型名，默认 nano-banana")
    parser.add_argument("--timeout", type=int, default=180, help="请求超时秒数，默认 180")

    args = parser.parse_args()

    try:
        result: Dict[str, Any]
        if args.model == 'nano-banana':
            # 直接调用 /v1/images/generations
            result = call_nano_banana_image_generation(
                prompt=args.prompt,
                model=args.model,
                timeout=args.timeout,
            )
        else:
            if not args.image:
                raise RuntimeError("使用非 nano-banana 模型时需要提供 --image")
            # 兼容旧用法：上传图片并调用 chat completions（图文）
            image_url = upload_image_to_bed(args.image, timeout=args.timeout)
            print(f"图片已上传，URL: {image_url}")
            result = call_image_chat_completion(
                prompt=args.prompt,
                image_url=image_url,
                api_key=None,
                base_url=None,
                model=args.model,
                stream=False,
                timeout=args.timeout,
            )

        # 3) 打印响应
        # 为简洁直接打印 JSON
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
