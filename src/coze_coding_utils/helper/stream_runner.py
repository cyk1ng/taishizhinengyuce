"""coze_coding_utils 兼容替身 - helper"""
from typing import Any, Dict

graph_helper = object()


class AgentStreamRunner:
    """Agent 流式运行器 - 替身"""
    def __init__(self, *args, **kwargs):
        pass


class WorkflowStreamRunner:
    """工作流流式运行器 - 替身"""
    def __init__(self, *args, **kwargs):
        pass


class RunOpt:
    """运行选项 - 替身"""
    def __init__(self, *args, **kwargs):
        pass


async def agent_stream_handler(*args, **kwargs) -> Any:
    """Agent 流式处理器 - 替身"""
    async def _empty_gen():
        yield b''
    return _empty_gen()


async def workflow_stream_handler(*args, **kwargs) -> Any:
    """工作流流式处理器 - 替身"""
    async def _empty_gen():
        yield b''
    return _empty_gen()