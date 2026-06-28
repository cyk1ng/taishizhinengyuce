"""
知识库查询工具 - 使用官方 KnowledgeClient 替代手动 ChromaDB

基于 coze_coding_dev_sdk 的 KnowledgeClient 实现语义搜索，
首次使用时自动从 seed_data_v3.json 导入种子文档。
"""

import os
import json
import uuid
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
    global _seeded, _seed_docs, _memory_docs
    if _seeded:
        return
    _seeded = True

    docs = _load_latest_seed()
    if not docs:
        return

    # 先将种子文档加载到全局变量（即使 SDK 不可用也能保底搜索）
    for doc in docs:
        content = doc.get("content") or doc.get("text", "")
        if content:
            doc_id = str(uuid.uuid4())
            _seed_docs.append({
                "id": doc_id,
                "content": content,
                "source": doc.get("source", "seed"),
                "_type": "seed"
            })
            # 同时加入 memory_docs，使所有 API 都能检索到
            _memory_docs.append({
                "id": doc_id,
                "content": content,
                "source": doc.get("source", "seed"),
                "_type": "seed"
            })

    logger.info(f"种子文档已加载到内存: {len(_seed_docs)} 条")

    # 尝试通过 SDK 导入知识库（沙箱环境可能不可用）
    ctx = req_ctx.get() or new_context(method="knowledge_auto_seed")
    try:
        client = _get_client(ctx)
    except Exception as e:
        logger.warning(f"KnowledgeClient 不可用，使用内存模式: {e}")
        return

    from coze_coding_dev_sdk import KnowledgeDocument, DataSourceType

    try:
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

    # 优先使用 SDK 搜索
    try:
        client = _get_client(ctx)
        response = client.search(
            query=query,
            table_names=[KNOWLEDGE_TABLE],
            top_k=top_k,
            min_score=0.0,
        )
        if response.code == 0 and response.chunks:
            return [
                {"text": c.content, "score": getattr(c, "score", 0.0)}
                for c in response.chunks
            ]
        if response.code != 0:
            logger.warning(f"SDK 搜索返回错误: {response.msg}，降级到内存搜索")
    except Exception as e:
        logger.warning(f"SDK 搜索异常: {e}，降级到内存搜索")

    # 降级：内存模糊搜索
    if not _memory_docs:
        return []

    query_lower = query.lower()
    scored = []
    for doc in _memory_docs:
        content = doc.get("content", "")
        if not content:
            continue
        # 简单关键词匹配得分（出现次数 / 文档长度）
        text_lower = content.lower()
        count = text_lower.count(query_lower)
        if count > 0:
            score = count / max(len(content), 1) * 100
            scored.append({"text": content[:500], "score": min(score, 1.0), "id": doc.get("id", "")})

    # 按得分排序取 top_k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


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


# ─── 全局变量初始化 ──────────────────────────────────
_memory_docs = []
_seed_docs = []
_kb_initialized = False

# ─── 文档管理 API（供 main.py 调用） ─────────────────────────────

def import_document(content: str, source_name: str = None) -> dict:
    """导入文档到知识库"""
    global _memory_docs, _seed_docs, _kb_initialized
    ctx = req_ctx.get() or new_context(method="import_document")
    try:
        client = _get_client(ctx)
        meta = {"source": source_name or "user_import"}
        if client:
            client.add_documents(
                documents=[{"content": content, "metadata": meta}],
                dataset_name="dispatch_knowledge"
            )
        _memory_docs.append({"content": content, "source": meta["source"], "id": str(uuid.uuid4())})
        return {"success": True, "result": "文档导入成功"}
    except Exception as e:
        logger.warning(f"KnowledgeClient import failed, using memory: {e}")
        _memory_docs.append({"content": content, "source": source_name or "user_import", "id": str(uuid.uuid4())})
        return {"success": True, "result": "文档已导入（内存模式）"}


def get_all_documents(page: int = 1, page_size: int = 20) -> dict:
    """获取知识库文档列表"""
    _auto_seed()  # 确保种子文档已加载
    offset = (page - 1) * page_size
    docs = _memory_docs[offset:offset + page_size]
    return {
        "total": len(_memory_docs),
        "page": page,
        "page_size": page_size,
        "documents": [{"id": d["id"], "content": d["content"][:200], "source": d.get("source", "")} for d in docs],
        "seed_count": len(_seed_docs)
    }


def delete_document(doc_id: str) -> dict:
    """删除知识库文档"""
    global _memory_docs, _seed_docs, _kb_initialized
    _memory_docs = [d for d in _memory_docs if d["id"] != doc_id]
    return {"success": True}


def update_document(doc_id: str, content: str, source_name: str = None) -> dict:
    """更新知识库文档"""
    for d in _memory_docs:
        if d["id"] == doc_id:
            d["content"] = content
            if source_name:
                d["source"] = source_name
            return {"success": True}
    return {"success": False, "error": "文档不存在"}


def count_documents() -> dict:
    """统计知识库文档数量"""
    _auto_seed()  # 确保种子文档已加载
    return {"total": len(_memory_docs), "seed": len(_seed_docs)}


def get_info() -> dict:
    """获取知识库信息"""
    _auto_seed()  # 确保种子文档已加载
    return {
        "type": "local",
        "total_documents": len(_memory_docs),
        "seed_count": len(_seed_docs),
        "memory_count": len(_memory_docs)
    }