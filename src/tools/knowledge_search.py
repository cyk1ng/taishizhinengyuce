"""
知识库搜索工具

基于 coze-coding-dev-sdk 的 KnowledgeClient 实现语义搜索。
文档（架构说明、业务规则）已预导入到 coze_doc_knowledge 数据集。
"""
import logging
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """懒加载 KnowledgeClient"""
    global _client
    if _client is None:
        from coze_coding_dev_sdk import KnowledgeClient, Config
        config = Config()
        _client = KnowledgeClient(config=config)
    return _client


@tool
def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中搜索相关文档内容，返回最匹配的结果。

    用法示例：
    - 搜索排班规则：query="排班规则是什么？"
    - 搜索工作当量计算：query="工作当量怎么计算"
    - 搜索数据库表：query="数据库有哪些表"

    Args:
        query: 搜索关键词或问题
        top_k: 返回结果数量，默认5条，最大20条

    Returns:
        知识库匹配结果文本
    """
    ctx = request_context.get() or new_context(method="search_knowledge")

    try:
        top_k = max(1, min(top_k, 20))
        client = _get_client()
        response = client.search(query=query, top_k=top_k)

        if response.code != 0:
            return f"搜索失败: {response.msg}"

        chunks = response.chunks
        if not chunks:
            return "知识库中未找到相关内容。"

        results = []
        for i, chunk in enumerate(chunks):
            results.append(
                f"【结果 {i + 1}】(匹配度: {chunk.score:.2f})\n"
                f"{chunk.content.strip()}"
            )

        return "\n\n".join(results)

    except Exception as e:
        logger.error("知识库搜索异常: %s", str(e), exc_info=True)
        return f"知识库搜索异常: {str(e)}"