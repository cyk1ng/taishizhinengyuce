"""coze_coding_utils 兼容替身 - log.err_trace"""
from typing import Optional


def extract_core_stack(error: Exception) -> str:
    """提取核心堆栈 - 替身"""
    import traceback
    return "".join(traceback.format_exception_only(type(error), error))