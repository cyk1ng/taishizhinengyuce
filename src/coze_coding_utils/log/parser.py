"""coze_coding_utils 兼容替身 - log.parser"""
from typing import Any, Dict


class LangGraphParser:
    """LangGraph 日志解析器替身"""
    @staticmethod
    def parse(data: Any) -> Dict[str, Any]:
        return {"parsed": str(data)}