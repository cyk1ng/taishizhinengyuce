"""coze_coding_utils 兼容替身 - openai.handler"""
from typing import Any, Dict

class OpenAIChatHandler:
    """OpenAI 聊天处理器 - 替身"""
    def __init__(self, *args, **kwargs):
        pass

    async def handle(self, *args, **kwargs) -> Dict[str, Any]:
        return {"role": "assistant", "content": "stub response"}