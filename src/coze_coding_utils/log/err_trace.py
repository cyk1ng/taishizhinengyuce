"""coze_coding_utils 兼容替身 - log.err_trace"""
from typing import Optional


def extract_core_stack(error: Optional[Exception] = None) -> str:
    """提取核心堆栈 - 替身"""
    import traceback
    if error:
        return "".join(traceback.format_exception_only(type(error), error))
    return "stub traceback: no active exception"