"""
子线程：批量移除视频首帧（覆盖原视频）
"""

import os
import subprocess
from typing import List
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
import imageio_ffmpeg


class VideoFirstFrameRemovalThread(QThread):
    """批量移除视频首帧（覆盖原文件）"""
    progress = pyqtSignal(str)  # 进度消息
    item_finished = pyqtSignal(bool, str, str)  # success, path, error
    finished_summary = pyqtSignal(int, int)  # total, success_count

    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        total = len(self.file_paths)
        logger.info(f"首帧移除任务启动，总文件数: {total}")
        success_count = 0
        for idx, path in enumerate(self.file_paths, start=1):
            try:
                self.progress.emit(f"[{idx}/{total}] 处理: {os.path.basename(path)}")
                logger.info(f"开始处理[{idx}/{total}] 文件: {path}")
                if not os.path.isfile(path):
                    logger.warning(f"文件不存在: {path}")
                    raise FileNotFoundError("文件不存在")

                # 输出到临时文件，然后覆盖原文件
                tmp_out = path + ".tmp.mp4"

                # ffmpeg命令：移除第一帧视频并重置时间戳
                # -y 覆盖输出；-hide_banner 减少日志；-loglevel error 仅输出错误
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                cmd = [
                    ffmpeg_exe,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-i", path,
                    "-vf", "select='not(eq(n,0))',setpts=PTS-STARTPTS",
                    "-af", "asetpts=PTS-STARTPTS",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    tmp_out
                ]
                logger.debug(f"执行ffmpeg命令: {' '.join(cmd)}")

                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode != 0:
                    err = (proc.stderr or "ffmpeg执行失败").strip()
                    logger.error(f"ffmpeg处理失败 code={proc.returncode} file={path} err={err}")
                    # 清理临时文件
                    if os.path.exists(tmp_out):
                        try:
                            os.remove(tmp_out)
                        except Exception:
                            pass
                    self.item_finished.emit(False, path, err)
                    continue

                # 覆盖原文件
                try:
                    os.replace(tmp_out, path)
                except Exception as e:
                    logger.error(f"覆盖原文件失败 file={path} err={e}")
                    # 回滚：删除临时文件
                    if os.path.exists(tmp_out):
                        try:
                            os.remove(tmp_out)
                        except Exception:
                            pass
                    self.item_finished.emit(False, path, str(e))
                    continue

                success_count += 1
                logger.info(f"首帧移除成功: {path}")
                self.item_finished.emit(True, path, "")
            except Exception as e:
                logger.exception(f"处理异常 file={path} err={e}")
                self.item_finished.emit(False, path, str(e))

        logger.info(f"首帧移除任务完成: 成功/总 = {success_count}/{total}")
        self.finished_summary.emit(total, success_count)
