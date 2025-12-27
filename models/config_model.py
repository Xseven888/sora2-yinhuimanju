"""
配置数据模型
"""

from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class ConfigModel:
    """配置模型"""
    id: Optional[int] = None
    key: str = ""
    value: str = ""
    type: str = "string"
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None