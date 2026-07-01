"""coze_coding_utils 兼容替身 - log"""
import logging
import os
from typing import Optional


LOG_FILE = "/tmp/work/logs/bypass/app.log"
LOG_LEVEL = "INFO"


class _RequestContext:
    """请求上下文 - 替身"""
    def get(self) -> Optional[object]:
        return None


request_context = _RequestContext()


def setup_logging(
    log_file: str = LOG_FILE,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 3,
    log_level: str = "INFO",
    use_json_format: bool = False,
    console_output: bool = True,
):
    """设置日志 - 替身"""
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )