"""coze_coding_utils 兼容替身 - helper.agent_helper"""
from typing import Any


def to_stream_input(query: str, thread_id: str) -> Any:
    """转换为流输入格式 - 替身"""
    return {"query": query, "thread_id": thread_id}