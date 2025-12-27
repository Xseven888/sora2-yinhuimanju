"""
任务数据模型
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class TaskModel:
    """任务模型"""
    id: Optional[int] = None
    task_id: Optional[str] = None
    prompt: Optional[str] = None
    model: str = "sora-2"
    orientation: str = "portrait"
    size: str = "small"
    duration: int = 10
    images: List[str] = field(default_factory=list)
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None
    progress: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.images is None:
            self.images = []