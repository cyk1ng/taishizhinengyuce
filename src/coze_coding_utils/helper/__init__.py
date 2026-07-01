"""coze_coding_utils 兼容替身 - helper"""
from typing import Any, Optional


class _GraphHelper:
    """GraphHelper 替身类"""

    def is_agent_proj(self) -> bool:
        """判断是否为 Agent 项目"""
        return True

    def get_agent_instance(self, agent_path: str, ctx=None) -> Any:
        """获取 Agent 实例"""
        from src.agents import agent
        return agent.build_agent(ctx)

    def get_graph_node_func_with_inout(self, graph, node_id: str):
        """获取图节点函数"""
        return None, None, None


graph_helper = _GraphHelper()

from . import stream_runner
from . import agent_helper