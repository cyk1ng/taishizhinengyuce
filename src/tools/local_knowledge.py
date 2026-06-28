"""
知识库查询工具 - 使用官方 KnowledgeClient 替代手动 ChromaDB

基于 coze_coding_dev_sdk 的 KnowledgeClient 实现语义搜索，
首次使用时自动从 seed_data_v3.json 导入种子文档。
"""

import os
import json
import logging
from typing import Optional
from langchain.tools import tool
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context as req_ctx

logger = logging.getLogger(__name__)

# 知识库数据集名称
KNOWLEDGE_TABLE = "coze_doc_knowledge"

# 种子文档路径（按优先级从新到旧）
SEED_FILES = [
    "assets/knowledge/seed_data_v3.json",
    "assets/knowledge/seed_data_final.json",
    "assets/knowledge/seed_data.json",
]

_seeded = False


def _get_client(ctx=None):
    """获取 KnowledgeClient 实例"""
    from coze_coding_dev_sdk import KnowledgeClient, Config

    config = Config()
    client = KnowledgeClient(config=config, ctx=ctx, verbose=False)
    return client


def _load_latest_seed() -> list:
    """加载最新的种子文档数据"""
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")

    for rel_path in SEED_FILES:
        full_path = os.path.join(workspace_path, rel_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"从 {rel_path} 加载种子文档: {len(data)} 条")
                return data
            except Exception as e:
                logger.warning(f"读取 {rel_path} 失败: {e}")

    logger.warning("未找到种子文档文件")
    return []


def _auto_seed():
    """自动导入种子文档到知识库（仅首次调用生效）"""
    global _seeded
    if _seeded:
        return
    _seeded = True

    docs = _load_latest_seed()
    if not docs:
        return

    ctx = req_ctx.get() or new_context(method="knowledge_auto_seed")
    client = _get_client(ctx)

    from coze_coding_dev_sdk import KnowledgeDocument, DataSourceType

    try:
        # 先搜索一下，看知识库是否已有数据
        search_resp = client.search(query="test", table_names=[KNOWLEDGE_TABLE], top_k=1)
        if search_resp.code == 0 and len(search_resp.chunks) > 0:
            logger.info("知识库已有数据，跳过种子导入")
            return
    except Exception:
        pass  # 知识库不存在或空，继续导入

    # 分批导入种子文档
    from coze_coding_dev_sdk import ChunkConfig

    chunk_config = ChunkConfig(
        separator="\n",
        max_tokens=1000,
        remove_extra_spaces=True,
    )

    batch_size = 10
    total = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        documents = []
        for doc in batch:
            content = doc.get("content") or doc.get("text", "")
            if not content:
                continue
            documents.append(
                KnowledgeDocument(
                    source=DataSourceType.TEXT,
                    raw_data=content,
                )
            )

        if documents:
            try:
                resp = client.add_documents(
                    documents=documents,
                    table_name=KNOWLEDGE_TABLE,
                    chunk_config=chunk_config,
                )
                if resp.code == 0:
                    total += len(resp.doc_ids)
                    logger.info(f"已导入 {total}/{len(docs)} 条文档")
            except Exception as e:
                logger.warning(f"导入批次 {i//batch_size} 失败: {e}")

    logger.info(f"种子文档导入完成，共 {total} 条")


def _search_raw(query: str, top_k: int = 5) -> list:
    """内部搜索函数（无 @tool 装饰），返回结构化结果列表。"""
    ctx = req_ctx.get() or new_context(method="search_knowledge")
    _auto_seed()
    client = _get_client(ctx)
    try:
        response = client.search(
            query=query,
            table_names=[KNOWLEDGE_TABLE],
            top_k=top_k,
            min_score=0.0,
        )
        if response.code != 0:
            return [{"error": f"搜索失败: {response.msg}"}]
        if not response.chunks:
            return []
        return [
            {"text": c.content, "score": getattr(c, "score", 0.0)}
            for c in response.chunks
        ]
    except Exception as e:
        return [{"error": f"搜索异常: {str(e)}"}]


@tool
def search_knowledge(query: str, top_k: int = 5) -> str:
    """
    在知识库中搜索相关信息。当需要查询知识库文档、规则、流程等信息时使用此工具。
    知识库包含调度规程、设备参数、操作流程等业务知识。

    Args:
        query: 搜索关键词，如"调度规程"、"设备操作流程"等
        top_k: 返回结果数量，默认5条

    Returns:
        知识库搜索结果文本
    """
    results = _search_raw(query, top_k)
    if not results:
        return f"未找到与 '{query}' 相关的知识内容。"
    if "error" in results[0]:
        return results[0]["error"]
    parts = []
    for i, r in enumerate(results):
        parts.append(f"[结果 {i + 1}] (相关度: {r.get('score', 0):.2f})\n{r.get('text', '')}")
    return "\n\n---\n\n".join(parts)