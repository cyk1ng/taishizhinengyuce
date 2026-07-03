"""
coze_coding_dev_sdk - Stub for Docker deployment
Falls back to langchain ChatOpenAI (Ollama) when SDK is unavailable.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Stub Config class"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class KnowledgeClient:
    """Stub KnowledgeClient - falls back to memory mode"""
    def __init__(self, ctx=None, **kwargs):
        self._ctx = ctx
        logger.info("KnowledgeClient: 使用内存模式 (Docker stub)")

    def search(self, query: str, table_names: list = None, top_k: int = 5, min_score: float = 0.0):
        """Return empty result - memory fallback handles this"""
        from types import SimpleNamespace
        return SimpleNamespace(code=-1, msg="SDK not available (Docker)", chunks=[])

    def create_knowledge_base(self, **kwargs):
        """Stub"""
        from types import SimpleNamespace
        return SimpleNamespace(code=-1, msg="SDK not available (Docker)")

    def add_document(self, **kwargs):
        """Stub"""
        from types import SimpleNamespace
        return SimpleNamespace(code=-1, msg="SDK not available (Docker)")

    def list_documents(self, **kwargs):
        """Stub"""
        return {"code": -1, "msg": "SDK not available (Docker)", "documents": []}

    def delete_document(self, **kwargs):
        """Stub"""
        from types import SimpleNamespace
        return SimpleNamespace(code=-1, msg="SDK not available (Docker)")


class LLMClient:
    """Stub LLMClient - uses ChatOpenAI (Ollama) under the hood"""
    def __init__(self, ctx=None, model: Optional[str] = None, **kwargs):
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:14b")
        self._base_url = os.environ.get("COZE_INTEGRATION_MODEL_BASE_URL", "http://host.docker.internal:11434/v1")
        self._api_key = os.environ.get("COZE_WORKLOAD_IDENTITY_API_KEY", "ollama")
        logger.info(f"LLMClient: 使用 Ollama ({self._model}) @ {self._base_url}")

    def invoke(self, messages: list) -> str:
        """Call Ollama via ChatOpenAI"""
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=self._model,
                base_url=self._base_url,
                api_key=self._api_key,
                temperature=0.3,
                timeout=120,
            )
            result = llm.invoke(messages)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            logger.error(f"LLMClient invoke 失败: {e}")
            return f'{{"error": "LLM调用失败: {str(e)}"}}'