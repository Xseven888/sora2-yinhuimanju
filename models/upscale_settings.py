"""
高清放大设置数据模型
"""

from dataclasses import dataclass

@dataclass
class UpscaleSettings:
    """高清放大设置模型"""
    mode: str = "tiny"  # tiny, tiny-long, full
    scale: int = 2  # 2, 3, 4