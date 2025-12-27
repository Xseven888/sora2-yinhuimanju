"""
模型信息数据模型
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelInfo:
    """模型信息"""
    name: str = ""
    description: str = ""
    type: str = "standard"
    orientation: str = "auto"
    quality: str = "standard"