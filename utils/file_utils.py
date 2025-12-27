"""
文件工具类
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

def open_folder(folder_path: str) -> bool:
    """
    打开文件夹
    
    Args:
        folder_path: 文件夹路径
        
    Returns:
        bool: 是否成功打开
    """
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path])
        return True
    except Exception as e:
        print(f"打开文件夹失败: {e}")
        return False

def open_file_location(file_path: str) -> bool:
    """
    打开文件所在位置
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否成功打开
    """
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.run(["explorer", "/select,", file_path])
        elif system == "Darwin":  # macOS
            subprocess.run(["open", "-R", file_path])
        else:  # Linux
            subprocess.run(["xdg-open", str(Path(file_path).parent)])
        return True
    except Exception as e:
        print(f"打开文件位置失败: {e}")
        return False

def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小
    """
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"