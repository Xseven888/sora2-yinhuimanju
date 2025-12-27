"""
日志工具类
"""

import zipfile
import datetime
from pathlib import Path
from typing import List

def pack_logs(log_dir: str, app_data_dir: str, db_path: str) -> tuple[bool, str]:
    """
    打包日志文件
    
    Args:
        log_dir: 日志目录
        app_data_dir: 应用数据目录
        db_path: 数据库路径
        
    Returns:
        tuple[bool, str]: (是否成功, 打包文件路径或错误信息)
    """
    try:
        log_path = Path(log_dir)
        
        # 创建打包文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"sora2_logs_{timestamp}.zip"
        zip_path = Path(app_data_dir) / zip_name

        # 创建zip文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加日志文件
            for log_file in log_path.glob("*.log"):
                zipf.write(log_file, log_file.name)

            # 添加压缩的日志文件
            for log_file in log_path.glob("*.log.zip"):
                zipf.write(log_file, log_file.name)

            # 添加数据库文件
            db_file = Path(db_path)
            if db_file.exists():
                zipf.write(db_file, "sora2.db")

        return True, str(zip_path)
    except Exception as e:
        return False, str(e)

def get_log_file_count(log_dir: str) -> int:
    """
    获取日志文件数量
    
    Args:
        log_dir: 日志目录
        
    Returns:
        int: 日志文件数量
    """
    try:
        log_path = Path(log_dir)
        return len(list(log_path.glob("*.log"))) + len(list(log_path.glob("*.log.zip")))
    except Exception:
        return 0