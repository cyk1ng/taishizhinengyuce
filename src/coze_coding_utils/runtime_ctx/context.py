"""coze_coding_utils 兼容替身 - runtime_ctx.context"""
import os
from typing import Optional, Dict, Any


class Context:
    """Context 替身类"""
    def __init__(self, ctx_id: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        self.ctx_id = ctx_id or ""
        self.run_id = ""
        self._data: Dict[str, Any] = {}
        self.headers = headers or {}

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default=None):
        return self._data.get(key, default)


def new_context(ctx=None, method: str = "", headers: Optional[Dict[str, str]] = None) -> Context:
    """创建新的上下文"""
    return Context(ctx_id=f"stub-{method}", headers=headers)


def default_headers(ctx=None) -> Dict[str, str]:
    """获取默认请求头"""
    return {}