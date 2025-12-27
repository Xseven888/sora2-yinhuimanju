"""
数据库工具类
"""

import sqlite3
import os
from pathlib import Path
from typing import Dict, Any

def check_database_health(db_path: str) -> Dict[str, Any]:
    """
    检查数据库健康状态
    
    Args:
        db_path: 数据库路径
        
    Returns:
        Dict[str, Any]: 健康状态信息
    """
    try:
        health_info = {
            'database_exists': os.path.exists(db_path),
            'database_path': db_path,
            'tables': {},
            'overall_status': 'healthy'
        }

        if not health_info['database_exists']:
            health_info['overall_status'] = 'error'
            health_info['error'] = '数据库文件不存在'
            return health_info

        # 检查表结构
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = ['config', 'tasks']

        for table in required_tables:
            table_info = {
                'exists': table in tables,
                'record_count': 0
            }

            if table_info['exists']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_info['record_count'] = cursor.fetchone()[0]

            health_info['tables'][table] = table_info

        conn.close()

        # 检查是否有缺失的表
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            health_info['overall_status'] = 'warning'
            health_info['missing_tables'] = missing_tables

        return health_info

    except Exception as e:
        return {
            'overall_status': 'error',
            'error': str(e),
            'database_path': db_path
        }

def get_database_info(db_path: str) -> Dict[str, Any]:
    """
    获取数据库详细信息
    
    Args:
        db_path: 数据库路径
        
    Returns:
        Dict[str, Any]: 数据库信息
    """
    try:
        info = {
            'path': db_path,
            'size': 0,
            'created_time': None,
            'modified_time': None,
            'tables_summary': {}
        }

        if os.path.exists(db_path):
            stat = os.stat(db_path)
            info['size'] = stat.st_size
            info['created_time'] = stat.st_ctime
            info['modified_time'] = stat.st_mtime

            # 获取表统计信息
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                info['tables_summary'][table] = count

            conn.close()

        return info

    except Exception as e:
        return {'error': str(e), 'path': db_path}