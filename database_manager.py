"""
数据库管理模块
用于存储历史记录和用户设置
"""

import sqlite3
import json
import os
import sys
import platform
from constants import API_BASE_URL
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from loguru import logger


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        """初始化数据库管理器"""
        # 获取应用数据目录
        self.app_data_dir = self._get_app_data_dir()

        # 在Sora2文件夹下创建两个文件夹：logs和database
        self.logs_dir = os.path.join(self.app_data_dir, "logs")
        self.database_dir = os.path.join(self.app_data_dir, "database")
        self.db_path = os.path.join(self.database_dir, "sora2.db")

        # 确保所有目录存在
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.database_dir, exist_ok=True)

        # 配置日志
        self._setup_logging()

        logger.info(f"数据库路径: {self.db_path}")
        logger.info(f"日志目录: {self.logs_dir}")
        logger.info(f"数据库备份目录: {self.database_dir}")

        # 检查和初始化数据库
        self._check_and_init_database()
    
    def _get_app_data_dir(self) -> str:
        """获取应用数据目录（跨平台兼容）"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # ~/Library/Application Support/Sora2
            app_dir = os.path.expanduser("~/Library/Application Support/Sora2")
        elif system == "Windows":  # Windows
            # %APPDATA%\Sora2
            app_dir = os.path.join(os.environ.get("APPDATA", ""), "Sora2")
        else:  # Linux和其他Unix系统
            # ~/.local/share/sora2
            app_dir = os.path.expanduser("~/.local/share/sora2")
            
        return app_dir

    def _setup_logging(self):
        """配置日志系统"""
        try:
            from datetime import datetime

            # 生成带日期时间的日志文件名
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"sora2_{current_time}.log"
            log_file_path = os.path.join(self.logs_dir, log_filename)

            # 移除默认的日志处理器
            logger.remove()

            # 添加控制台输出（彩色）
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level="INFO"
            )

            # 添加文件输出
            logger.add(
                log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="DEBUG",
                rotation="50 MB",  # 文件大小超过50MB时轮转
                retention="7 days",  # 保留7天的日志
                compression="zip",  # 压缩旧日志文件
                encoding="utf-8"
            )

            logger.info(f"日志系统初始化完成，日志文件: {log_file_path}")

        except Exception as e:
            # 如果日志配置失败，使用基本配置
            print(f"日志配置失败: {e}")

    def get_current_log_file(self) -> str:
        """获取当前日志文件路径"""
        try:
            # 查找最新的日志文件
            log_files = [f for f in os.listdir(self.logs_dir) if f.startswith('sora2_') and f.endswith('.log')]
            if log_files:
                latest_log = max(log_files, key=lambda f: os.path.getctime(os.path.join(self.logs_dir, f)))
                return os.path.join(self.logs_dir, latest_log)
            return ""
        except Exception:
            return ""

    def _check_and_init_database(self):
        """检查并初始化数据库"""
        try:
            # 检查数据库文件是否存在
            db_exists = os.path.exists(self.db_path)

            if not db_exists:
                logger.info("数据库文件不存在，正在创建...")
            else:
                logger.info("数据库文件已存在，检查表结构...")

            # 连接数据库并检查表
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            logger.info(f"现有数据表: {existing_tables}")

            # 需要创建的表（已移除 goods_videos）
            required_tables = ['config', 'tasks', 'voice_library']

            # 检查每个表是否存在
            for table in required_tables:
                if table not in existing_tables:
                    logger.info(f"创建数据表: {table}")

            conn.close()

            # 初始化所有表结构
            self._init_database()

            # 验证表是否创建成功
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            final_tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            missing_tables = [t for t in required_tables if t not in final_tables]
            if missing_tables:
                logger.error(f"以下表创建失败: {missing_tables}")
                raise Exception(f"数据库表创建失败: {missing_tables}")
            else:
                logger.info("所有数据表创建/验证完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建logs表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

        # 创建config、tasks和chat_tasks表
        self.create_config_table()
        self.create_tasks_table()
        self.create_chat_tasks_table()
        # 创建高清放大服务器表
        self.create_upscale_servers_table()
        # 创建项目相关表
        self.create_projects_table()
        self.create_episodes_table()
        self.create_characters_table()
        self.create_storyboards_table()
        # 创建音色库表
        self.create_voice_library_table()
        # 删除已废弃的带货视频表（如果存在）
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DROP TABLE IF EXISTS goods_videos')
            conn.commit()
            conn.close()
            logger.info("已删除废弃的 goods_videos 表（如存在）")
        except Exception as e:
            logger.warning(f"尝试删除 goods_videos 表失败: {e}")

    def init_db(self):
        """公开的初始化数据库方法"""
        self._init_database()
    
  
  
    def add_log(self, level: str, message: str) -> bool:
        """添加日志记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO logs (level, message)
                VALUES (?, ?)
            ''', (level, message))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"添加日志失败: {e}")
            return False

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取日志记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, level, message, created_at
                FROM logs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))

            logs = []
            for row in cursor.fetchall():
                log = {
                    'id': row[0],
                    'level': row[1],
                    'message': row[2],
                    'created_at': row[3]
                }
                logs.append(log)

            conn.close()
            return logs
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            return []

    
    def clear_logs(self) -> bool:
        """清空日志"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM logs')

            conn.commit()
            conn.close()
            logger.info("日志已清空")
            return True
        except Exception as e:
            logger.error(f"清空日志失败: {e}")
            return False

    
    def create_config_table(self) -> bool:
        """创建config配置表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    type TEXT DEFAULT 'string',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 插入默认配置
            default_configs = [
                ('api_key', '', 'string', 'Sora API Key'),
                ('api_base_url', API_BASE_URL, 'string', 'API Base URL'),
                ('image_token', '1c17b11693cb5ec63859b091c5b9c1b2', 'string', '图床Token'),
                ('default_model', 'sora-2', 'string', '默认模型'),
                ('default_duration', '10', 'integer', '默认时长(秒)'),
                ('add_task_default_resolution', '16:9', 'string', '添加任务默认分辨率'),
                ('add_task_default_duration', '10', 'integer', '添加任务默认时长'),
                ('auto_download', 'true', 'boolean', '自动下载视频'),
                ('video_save_path', '', 'string', '视频保存路径'),
                ('theme', 'auto', 'string', '主题设置(light/dark/auto)'),
                # AI 标题相关默认配置
                ('ai_title_enabled', 'false', 'boolean', 'AI标题开关'),
                ('ai_title_prompt', '只返回一个中文视频标题，不要返回任何解释或额外内容；不使用引号、编号、前后缀；不换行；不超过30字，风格有趣吸引人', 'string', 'AI标题提示词'),
                # 提示词设置默认值
                ('main_image_prompt', '根据提供的商品主图生成标准电商白底图：\n- 背景：纯白(#FFFFFF)，干净无纹理；\n- 主体：保持原始外观与质感，不改变颜色与结构；\n- 抠图：边缘干净无锯齿，无残留背景；\n- 光线：均匀柔和，无明显阴影或色偏；\n- 构图：产品居中，适度留白，画面整洁；\n- 分辨率：至少 2048×2048；\n- 输出：PNG(透明背景)或JPEG(白底)，适合电商展示。', 'string', '主图处理提示词(白底图生成)'),
                ('scene_generation_prompt', '请基于白底图与商品标题生成一个 15 秒的产品介绍视频脚本与镜头计划。要求：\n1) 产品简短描述与核心卖点(中文)。\n2) 旁白文案(中文、自然口语，节奏紧凑)。\n3) 背景音乐风格：轻快现代，音量不压旁白。\n4) 运镜设计：推进/摇移/环绕等，流畅自然。\n5) 时间轴划分为 2–3 个镜头，每个镜头标注【时长/画面内容/镜头运动/旁白/字幕】。\n6) 画面以白底图为核心，可加入品牌色点缀。\n7) 结尾包含行动号召(如“立即了解/购买”)。\n总时长严格控制在 15 秒。\n请按如下格式输出：\nShot 1（0–5s）：画面内容…｜镜头运动…｜旁白…｜字幕…\nShot 2（5–10s）：…\nShot 3（10–15s）：…', 'string', '场景生成提示词(15秒产品介绍)')
            ]

            for key, value, type_, desc in default_configs:
                cursor.execute('''
                    INSERT OR IGNORE INTO config (key, value, type, description)
                    VALUES (?, ?, ?, ?)
                ''', (key, value, type_, desc))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"创建config表失败: {e}")
            return False

    def create_tasks_table(self) -> bool:
        """创建tasks任务表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    prompt TEXT NOT NULL,
                    model TEXT DEFAULT 'sora-2',
                    orientation TEXT DEFAULT 'portrait',
                    size TEXT DEFAULT 'small',
                    duration INTEGER DEFAULT 10,
                    images TEXT,
                    video_url TEXT,
                    thumbnail_url TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    progress INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)')

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"创建tasks表失败: {e}")
            return False

    def create_chat_tasks_table(self) -> bool:
        """创建chat_tasks表 - 记录Chat模式的任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    model TEXT NOT NULL,
                    is_chat_mode INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_tasks_task_id ON chat_tasks(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_tasks_model ON chat_tasks(model)')

            conn.commit()
            conn.close()
            logger.info("chat_tasks表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建chat_tasks表失败: {e}")
            return False

    def create_upscale_servers_table(self) -> bool:
        """创建高清放大服务器表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS upscale_servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 为url建立唯一索引，避免重复配置同一地址
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_upscale_servers_url ON upscale_servers(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_upscale_servers_enabled ON upscale_servers(enabled)')

            conn.commit()
            conn.close()
            logger.info("upscale_servers表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建upscale_servers表失败: {e}")
            return False

    def create_goods_videos_table(self) -> bool:
        """创建带货视频表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS goods_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    main_image TEXT,
                    white_image TEXT,
                    prompt TEXT,
                    task_id INTEGER, -- 关联tasks表的ID，可空
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
                )
            ''')

            # 索引：按创建时间与任务ID查询方便
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_goods_videos_created_at ON goods_videos(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_goods_videos_task_id ON goods_videos(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_goods_videos_title ON goods_videos(title)')

            conn.commit()
            conn.close()
            logger.info("goods_videos表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建goods_videos表失败: {e}")
            return False

    # === 带货视频 CRUD 方法 ===
    def add_goods_video(self, title: str, main_image: str = None, white_image: str = None,
                        prompt: str = None, task_id: Optional[int] = None) -> Optional[int]:
        """新增一条带货视频记录，返回插入的ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO goods_videos (title, main_image, white_image, prompt, task_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (title, main_image, white_image, prompt, task_id))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            logger.info(f"新增 goods_videos 记录: id={new_id}, title={title}")
            return int(new_id)
        except Exception as e:
            logger.error(f"新增 goods_videos 失败: {e}")
            return None

    def update_goods_video(self, goods_id: int, updates: Dict[str, Any]) -> bool:
        """根据ID更新带货视频记录，updates为要更新的字段字典"""
        if not updates:
            return True
        try:
            # 允许更新的字段白名单
            allowed = {"title", "main_image", "white_image", "prompt", "task_id", "updated_at"}
            set_clauses = []
            values: List[Any] = []
            for k, v in updates.items():
                if k in allowed and k != "updated_at":
                    set_clauses.append(f"{k} = ?")
                    values.append(v)
            # 始终更新更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            sql = f"UPDATE goods_videos SET {', '.join(set_clauses)} WHERE id = ?"
            values.append(goods_id)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(sql, tuple(values))
            conn.commit()
            conn.close()
            logger.info(f"更新 goods_videos 记录: id={goods_id}, updates={updates}")
            return True
        except Exception as e:
            logger.error(f"更新 goods_videos 失败: {e}")
            return False

    def get_goods_videos(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """分页查询带货视频记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, main_image, white_image, prompt, task_id, created_at, updated_at
                FROM goods_videos
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            rows = cursor.fetchall()
            conn.close()

            result: List[Dict[str, Any]] = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'title': r[1],
                    'main_image': r[2],
                    'white_image': r[3],
                    'prompt': r[4],
                    'task_id': r[5],
                    'created_at': r[6],
                    'updated_at': r[7],
                })
            return result
        except Exception as e:
            logger.error(f"查询 goods_videos 失败: {e}")
            return []

    def get_goods_video_by_id(self, goods_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取带货视频记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, main_image, white_image, prompt, task_id, created_at, updated_at
                FROM goods_videos
                WHERE id = ?
            ''', (goods_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return {
                'id': row[0],
                'title': row[1],
                'main_image': row[2],
                'white_image': row[3],
                'prompt': row[4],
                'task_id': row[5],
                'created_at': row[6],
                'updated_at': row[7],
            }
        except Exception as e:
            logger.error(f"获取 goods_videos 失败: {e}")
            return None

    def get_upscale_servers(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取高清放大服务器列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if enabled_only:
                cursor.execute('''
                    SELECT id, name, url, enabled, created_at, updated_at
                    FROM upscale_servers
                    WHERE enabled = 1
                    ORDER BY id ASC
                ''')
            else:
                cursor.execute('''
                    SELECT id, name, url, enabled, created_at, updated_at
                    FROM upscale_servers
                    ORDER BY id ASC
                ''')

            servers = []
            for row in cursor.fetchall():
                servers.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'enabled': bool(row[3]),
                    'created_at': row[4],
                    'updated_at': row[5]
                })

            conn.close()
            return servers
        except Exception as e:
            logger.error(f"获取upscale服务器列表失败: {e}")
            return []

    def add_upscale_server(self, name: str, url: str, enabled: bool = True) -> bool:
        """添加高清放大服务器"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO upscale_servers (name, url, enabled)
                VALUES (?, ?, ?)
            ''', (name, url, 1 if enabled else 0))

            conn.commit()
            conn.close()
            logger.info(f"添加高清放大服务器: {name} -> {url}")
            return True
        except Exception as e:
            logger.error(f"添加upscale服务器失败: {e}")
            return False

    def update_upscale_server(self, server_id: int, name: Optional[str] = None, url: Optional[str] = None, enabled: Optional[bool] = None) -> bool:
        """更新高清放大服务器"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            set_clauses = []
            values: List[Any] = []

            if name is not None:
                set_clauses.append("name = ?")
                values.append(name)
            if url is not None:
                set_clauses.append("url = ?")
                values.append(url)
            if enabled is not None:
                set_clauses.append("enabled = ?")
                values.append(1 if enabled else 0)

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(server_id)

            if not set_clauses:
                conn.close()
                return True

            cursor.execute(f'''
                UPDATE upscale_servers
                SET {", ".join(set_clauses)}
                WHERE id = ?
            ''', values)

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新upscale服务器失败: {e}")
            return False

    def delete_upscale_server(self, server_id: int) -> bool:
        """删除高清放大服务器"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM upscale_servers WHERE id = ?', (server_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除upscale服务器失败: {e}")
            return False

    def get_enabled_upscale_servers(self) -> List[Dict[str, Any]]:
        """获取已启用的高清放大服务器列表"""
        return self.get_upscale_servers(enabled_only=True)

    def save_config(self, key: str, value: Any, type_: str = 'string', description: Optional[str] = None) -> bool:
        """保存配置到config表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 转换值为字符串
            if isinstance(value, bool):
                value_str = 'true' if value else 'false'
            elif isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)

            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value, type, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value_str, type_, description))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def load_config(self, key: str, default: Any = None) -> Any:
        """从config表加载配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT value, type FROM config WHERE key = ?', (key,))
            row = cursor.fetchone()

            conn.close()

            if row:
                value_str, type_ = row
                # 根据类型转换值
                if type_ == 'boolean':
                    return value_str.lower() == 'true'
                elif type_ == 'integer':
                    return int(value_str)
                elif type_ == 'float':
                    return float(value_str)
                elif type_ == 'json':
                    return json.loads(value_str)
                else:
                    return value_str
            else:
                return default
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return default

    def add_task(self, task_data: Dict[str, Any]) -> bool:
        """添加任务到tasks表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            images_json = json.dumps(task_data.get('images', []))

            cursor.execute('''
                INSERT INTO tasks
                (task_id, prompt, model, orientation, size, duration, images,
                 status, progress, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data.get('task_id'),
                task_data.get('prompt'),
                task_data.get('model', 'sora-2'),
                task_data.get('orientation', 'portrait'),
                task_data.get('size', 'small'),
                task_data.get('duration', 10),
                images_json,
                task_data.get('status', 'pending'),
                task_data.get('progress', 0),
                task_data.get('error_message')
            ))

            conn.commit()
            conn.close()
            logger.info(f"添加任务成功: {task_data.get('task_id')}")
            return True
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False

    def get_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取任务列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status:
                cursor.execute('''
                    SELECT id, task_id, prompt, model, orientation, size, duration, images,
                           video_url, thumbnail_url, status, error_message, progress,
                           created_at, started_at, completed_at, updated_at
                    FROM tasks
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT id, task_id, prompt, model, orientation, size, duration, images,
                           video_url, thumbnail_url, status, error_message, progress,
                           created_at, started_at, completed_at, updated_at
                    FROM tasks
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))

            tasks = []
            for row in cursor.fetchall():
                task = {
                    'id': row[0],
                    'task_id': row[1],
                    'prompt': row[2],
                    'model': row[3],
                    'orientation': row[4],
                    'size': row[5],
                    'duration': row[6],
                    'images': json.loads(row[7]) if row[7] else [],
                    'video_url': row[8],
                    'thumbnail_url': row[9],
                    'status': row[10],
                    'error_message': row[11],
                    'progress': row[12],
                    'created_at': row[13],
                    'started_at': row[14],
                    'completed_at': row[15],
                    'updated_at': row[16]
                }
                tasks.append(task)

            conn.close()
            return tasks
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return []

    def get_tasks_paginated(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取任务列表（支持分页）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, task_id, prompt, model, orientation, size, duration, images,
                       video_url, thumbnail_url, status, error_message, progress,
                       created_at, started_at, completed_at, updated_at
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            tasks = []
            for row in cursor.fetchall():
                task = {
                    'id': row[0],
                    'task_id': row[1],
                    'prompt': row[2],
                    'model': row[3],
                    'orientation': row[4],
                    'size': row[5],
                    'duration': row[6],
                    'images': json.loads(row[7]) if row[7] else [],
                    'video_url': row[8],
                    'thumbnail_url': row[9],
                    'status': row[10],
                    'error_message': row[11],
                    'progress': row[12],
                    'created_at': row[13],
                    'started_at': row[14],
                    'completed_at': row[15],
                    'updated_at': row[16]
                }
                tasks.append(task)

            conn.close()
            return tasks
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return []

    def get_tasks_count(self) -> int:
        """获取任务总数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM tasks')
            count = cursor.fetchone()[0]

            conn.close()
            return count
        except Exception as e:
            logger.error(f"获取任务总数失败: {e}")
            return 0

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            set_clauses = []
            values = []

            for key, value in updates.items():
                if key == 'images':
                    value = json.dumps(value)

                set_clauses.append(f"{key} = ?")
                values.append(value)

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(task_id)

            cursor.execute(f'''
                UPDATE tasks
                SET {", ".join(set_clauses)}
                WHERE task_id = ?
            ''', values)

            conn.commit()
            conn.close()
            logger.info(f"更新任务成功: {task_id}")
            return True
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务(同时会自动删除chat_tasks表中的关联记录)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先删除chat_tasks表中的记录(如果存在)
            cursor.execute('DELETE FROM chat_tasks WHERE task_id = ?', (task_id,))
            chat_deleted = cursor.rowcount
            
            # 再删除tasks表中的记录
            cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
            tasks_deleted = cursor.rowcount

            conn.commit()
            conn.close()

            if tasks_deleted > 0:
                if chat_deleted > 0:
                    logger.info(f"删除Chat任务成功: {task_id} (tasks:{tasks_deleted}条, chat_tasks:{chat_deleted}条)")
                else:
                    logger.info(f"删除任务成功: {task_id} (删除了{tasks_deleted}条记录)")
                return True
            else:
                logger.warning(f"未找到要删除的任务: {task_id}")
                return False
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    def add_chat_task(self, task_id: str, model: str) -> bool:
        """添加Chat模式任务记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO chat_tasks (task_id, model)
                VALUES (?, ?)
            ''', (task_id, model))

            conn.commit()
            conn.close()
            logger.info(f"Chat任务记录已添加: {task_id} (model: {model})")
            return True
        except Exception as e:
            logger.error(f"添加Chat任务记录失败: {e}")
            return False
    
    def is_chat_task(self, task_id: str) -> bool:
        """检查是否为Chat模式任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM chat_tasks WHERE task_id = ?', (task_id,))
            count = cursor.fetchone()[0]

            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"检查Chat任务状态失败: {e}")
            return False
    
    def get_chat_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有Chat模式任务列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT ct.task_id, ct.model, ct.created_at,
                       t.prompt, t.status, t.video_url
                FROM chat_tasks ct
                LEFT JOIN tasks t ON ct.task_id = t.task_id
                ORDER BY ct.created_at DESC
                LIMIT ?
            ''', (limit,))

            columns = ['task_id', 'model', 'created_at', 'prompt', 'status', 'video_url']
            chat_tasks = []
            
            for row in cursor.fetchall():
                task = dict(zip(columns, row))
                chat_tasks.append(task)

            conn.close()
            return chat_tasks
        except Exception as e:
            logger.error(f"获取Chat任务列表失败: {e}")
            return []

    def clear_tasks(self) -> bool:
        """清空所有任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM tasks')

            conn.commit()
            conn.close()
            logger.info("所有任务已清空")
            return True
        except Exception as e:
            logger.error(f"清空任务失败: {e}")
            return False

    def delete_completed_tasks(self) -> int:
        """删除所有状态为 completed 和 failed 的任务，同时清理关联的 chat_tasks 记录。
        返回删除的任务数量。"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先删除关联的 chat_tasks 记录（若未启用外键约束，手动清理）
            cursor.execute('''
                DELETE FROM chat_tasks
                WHERE task_id IN (
                    SELECT task_id FROM tasks WHERE status IN ('completed', 'failed')
                )
            ''')

            # 再删除已完成/失败的任务
            cursor.execute("DELETE FROM tasks WHERE status IN ('completed', 'failed')")
            deleted_count = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(f"已删除 {deleted_count} 条已完成/失败任务")
            return deleted_count
        except Exception as e:
            logger.error(f"删除已完成任务失败: {e}")
            return 0

    def get_task_statistics(self) -> Dict[str, int]:
        """获取任务统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM tasks
                GROUP BY status
            ''')

            stats = {
                'total': 0,
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0
            }

            for row in cursor.fetchall():
                status, count = row
                stats['total'] += count
                if status in stats:
                    stats[status] = count

            conn.close()
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            health_info = {
                'database_exists': os.path.exists(self.db_path),
                'database_path': self.db_path,
                'tables': {},
                'overall_status': 'healthy'
            }

            if not health_info['database_exists']:
                health_info['overall_status'] = 'error'
                health_info['error'] = '数据库文件不存在'
                return health_info

            # 检查表结构
            conn = sqlite3.connect(self.db_path)
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
            logger.error(f"数据库健康检查失败: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'database_path': self.db_path
            }

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库详细信息"""
        try:
            info = {
                'path': self.db_path,
                'size': 0,
                'created_time': None,
                'modified_time': None,
                'tables_summary': {}
            }

            if os.path.exists(self.db_path):
                stat = os.stat(self.db_path)
                info['size'] = stat.st_size
                info['created_time'] = stat.st_ctime
                info['modified_time'] = stat.st_mtime

                # 获取表统计信息
                conn = sqlite3.connect(self.db_path)
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
            logger.error(f"获取数据库信息失败: {e}")
            return {'error': str(e), 'path': self.db_path}

    def create_projects_table(self) -> bool:
        """创建项目表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    cover_image TEXT,
                    novel_file_path TEXT,
                    novel_folder_path TEXT,
                    style TEXT,
                    aspect_ratio TEXT DEFAULT '9:16',
                    description TEXT,
                    chapter_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)')
            conn.commit()
            conn.close()
            logger.info("projects表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建projects表失败: {e}")
            return False

    def create_episodes_table(self) -> bool:
        """创建剧集表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    episode_name TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_project_id ON episodes(project_id)')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_episodes_project_episode ON episodes(project_id, episode_number)')
            conn.commit()
            conn.close()
            logger.info("episodes表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建episodes表失败: {e}")
            return False

    def create_characters_table(self) -> bool:
        """创建角色表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    front_image TEXT,
                    side_image TEXT,
                    back_image TEXT,
                    id_card_image TEXT,
                    sora_character_id TEXT,
                    sora_character_username TEXT,
                    sora_status TEXT DEFAULT '未上传',
                    voice_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (voice_id) REFERENCES voice_library(id) ON DELETE SET NULL
                )
            ''')
            
            # 检查并添加voice_id列（如果表已存在但列不存在）
            cursor.execute("PRAGMA table_info(characters)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'voice_id' not in columns:
                cursor.execute('ALTER TABLE characters ADD COLUMN voice_id INTEGER')
                logger.info("已为characters表添加voice_id列")

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_characters_project_id ON characters(project_id)')
            conn.commit()
            conn.close()
            logger.info("characters表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建characters表失败: {e}")
            return False

    def create_storyboards_table(self) -> bool:
        """创建分镜表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS storyboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id INTEGER NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    storyboard_detail TEXT,
                    scene_image TEXT,
                    video_prompt TEXT,
                    video_url TEXT,
                    video_task_id TEXT,
                    video_status TEXT DEFAULT '未生成',
                    title TEXT,
                    duration TEXT,
                    dialogue TEXT,
                    screen_content TEXT,
                    sound_effect TEXT,
                    camera_movement TEXT,
                    prompt TEXT,
                    video_file TEXT,
                    thumbnail_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
                )
            ''')
            
            # 检查并添加缺失的列（用于兼容旧表结构）
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN title TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN duration TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN dialogue TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN screen_content TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN sound_effect TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN camera_movement TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN prompt TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN video_file TEXT")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE storyboards ADD COLUMN thumbnail_path TEXT")
            except:
                pass

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_storyboards_episode_id ON storyboards(episode_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_storyboards_sequence ON storyboards(episode_id, sequence_number)')
            conn.commit()
            conn.close()
            logger.info("storyboards表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建storyboards表失败: {e}")
            return False
    
    def create_voice_library_table(self) -> bool:
        """创建音色库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_number INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_voice_library_sequence ON voice_library(sequence_number)')
            conn.commit()
            conn.close()
            logger.info("voice_library表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建voice_library表失败: {e}")
            return False

    def update_storyboard_video_info(
        self,
        storyboard_id: int,
        video_task_id: str = None,
        video_url: str = None,
        video_status: str = None
    ) -> bool:
        """更新分镜的视频相关信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = []
            values = []
            
            if video_task_id is not None:
                updates.append("video_task_id = ?")
                values.append(video_task_id)
            
            if video_url is not None:
                updates.append("video_url = ?")
                values.append(video_url)
            
            if video_status is not None:
                updates.append("video_status = ?")
                values.append(video_status)
            
            if not updates:
                conn.close()
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(storyboard_id)
            
            query = f"""
                UPDATE storyboards
                SET {', '.join(updates)}
                WHERE id = ?
            """
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            logger.info(f"更新分镜 {storyboard_id} 的视频信息成功")
            return True
        except Exception as e:
            logger.error(f"更新分镜视频信息失败: {e}")
            return False

    def get_storyboard_by_id(self, storyboard_id: int) -> Optional[Dict]:
        """根据ID获取分镜信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, episode_id, sequence_number, title, screen_content,
                       sound_effect, dialogue, duration, camera_movement,
                       thumbnail_path, prompt, video_url, video_task_id, video_status
                FROM storyboards
                WHERE id = ?
            """, (storyboard_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'episode_id': row[1],
                    'sequence_number': row[2],
                    'title': row[3],
                    'screen_content': row[4],
                    'sound_effect': row[5],
                    'dialogue': row[6],
                    'duration': row[7],
                    'camera_movement': row[8],
                    'thumbnail_path': row[9],
                    'prompt': row[10],
                    'video_url': row[11],
                    'video_task_id': row[12],
                    'video_status': row[13]
                }
            return None
        except Exception as e:
            logger.error(f"获取分镜信息失败: {e}")
            return None


class ModelManager:
    """模型管理器"""

    def __init__(self):
        self.models = {
            'sora-2': {
                'name': 'Sora 2 标准版',
                'description': 'Sora 2 现已推出，openai最新的视频生成模型比之前的系统更加物理精准、逼真，并且更易于控制。它还支持同步对话和音效。',
                'type': 'standard',
                'orientation': 'auto',
                'quality': 'standard'
            },
            'sora-2-landscape': {
                'name': 'Sora 2 横屏版',
                'description': '调用新版本的 Sora 生成横屏视频。',
                'type': 'landscape',
                'orientation': 'landscape',
                'quality': 'standard'
            }
        }

    def get_all_models(self):
        """获取所有模型"""
        return self.models

    def get_model_info(self, model_id):
        """获取指定模型信息"""
        return self.models.get(model_id, {})

    def get_models_by_type(self, model_type):
        """根据类型获取模型"""
        return {k: v for k, v in self.models.items() if v['type'] == model_type}

    def get_models_by_quality(self, quality):
        """根据画质获取模型"""
        return {k: v for k, v in self.models.items() if v['quality'] == quality}


# 全局实例
db_manager = DatabaseManager()
model_manager = ModelManager()
