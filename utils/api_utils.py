"""
API工具类
"""

import json
from typing import Dict, Any, Optional

def extract_video_url_from_response(response_data: Dict[str, Any]) -> Optional[str]:
    """
    从API响应中提取视频URL
    
    Args:
        response_data: API响应数据
        
    Returns:
        Optional[str]: 视频URL，如果未找到则返回None
    """
    # 方式1: 直接获取 video_url 字段
    if 'video_url' in response_data:
        video_url = response_data.get('video_url')
        if video_url:
            return video_url
    
    # 方式2: 从 detail.url 获取
    if 'detail' in response_data:
        detail = response_data.get('detail', {})
        if isinstance(detail, dict) and 'url' in detail:
            video_url = detail.get('url')
            if video_url:
                return video_url
    
    # 方式3: 从 data.video_url 获取
    if 'data' in response_data:
        data = response_data.get('data', {})
        if isinstance(data, dict) and 'video_url' in data:
            video_url = data.get('video_url')
            if video_url:
                return video_url
    
    # 方式4: 从 url 字段直接获取
    if 'url' in response_data:
        video_url = response_data.get('url')
        if video_url:
            return video_url
    
    return None

def parse_api_error(response_data: Dict[str, Any]) -> str:
    """
    解析API错误信息
    
    Args:
        response_data: API响应数据
        
    Returns:
        str: 错误信息
    """
    # 优先使用message字段
    if 'message' in response_data:
        return response_data['message']
    
    # 尝试从error字段获取
    if 'error' in response_data:
        error = response_data['error']
        if isinstance(error, dict) and 'message' in error:
            return error['message']
        return str(error)
    
    # 尝试从detail字段获取
    if 'detail' in response_data:
        detail = response_data['detail']
        if isinstance(detail, dict):
            # 从pending_info获取失败原因
            if 'pending_info' in detail:
                pending_info = detail['pending_info']
                if isinstance(pending_info, dict) and 'failure_reason' in pending_info:
                    return pending_info['failure_reason']
            # 直接从detail获取
            if 'message' in detail:
                return detail['message']
        return str(detail)
    
    return "未知错误"