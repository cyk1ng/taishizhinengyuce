"""coze_coding_utils 兼容替身 - log.parser"""
from typing import Any, Dict


class LangGraphParser:
    """LangGraph 日志解析器替身"""
    def __init__(self, graph=None):
        self._graph = graph

    def get_node_metadata(self, node_id: str) -> Dict[str, Any]:
        """获取节点元数据"""
        return {}

    @staticmethod
    def parse(data: Any) -> Dict[str, Any]:
        return {"parsed": str(data)}