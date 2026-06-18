"""
本地向量知识库 - 数据存储在 assets/knowledge/ 目录下
使用 ChromaDB + EmbeddingClient 实现
"""

import os
import json
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 知识库存储路径
KB_DIR = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "knowledge")

# 延迟导入（避免启动时加载全部依赖）
_embedding_client = None
_chroma_client = None
_chroma_collection = None


def _get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        from coze_coding_dev_sdk import EmbeddingClient
        _embedding_client = EmbeddingClient()
    return _embedding_client


def _get_chroma_collection():
    """获取 ChromaDB 集合（持久化到本地）"""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        import chromadb
        os.makedirs(KB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=KB_DIR)
        # 获取或创建集合
        try:
            _chroma_collection = _chroma_client.get_collection("coze_doc_knowledge")
        except Exception:
            _chroma_collection = _chroma_client.create_collection(
                "coze_doc_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
    return _chroma_collection


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """按段落和长度分割文本为chunks"""
    import re
    
    # 先按 ## 标题分割（Markdown章节）
    sections = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # 如果章节内容较短，直接作为一个chunk
        if len(section) <= chunk_size:
            # 取前120字符作为摘要
            summary = section[:120].replace('\n', ' ').strip()
            chunks.append({
                "text": section,
                "summary": summary[:120]
            })
        else:
            # 较长的章节按句子分割
            sentences = re.split(r'(?<=[。！？\n])\s*', section)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) > chunk_size and current:
                    summary = current[:120].replace('\n', ' ').strip()
                    chunks.append({"text": current, "summary": summary[:120]})
                    current = sent
                else:
                    current += sent
            if current:
                summary = current[:120].replace('\n', ' ').strip()
                chunks.append({"text": current, "summary": summary[:120]})
    
    return chunks


def import_document(content: str, source_name: str = "unknown") -> dict:
    """导入文档到本地知识库"""
    ec = _get_embedding_client()
    collection = _get_chroma_collection()
    
    # 分块
    chunks = _chunk_text(content)
    
    if not chunks:
        return {"code": -1, "msg": "文档内容为空", "count": 0}
    
    texts = [c["text"] for c in chunks]
    summaries = [c["summary"] for c in chunks]
    
    # 逐条生成向量（embed_texts 返回的是单条合并向量）
    embeddings = []
    for i, text in enumerate(texts):
        try:
            emb = ec.embed_text(text)
            embeddings.append(emb)
        except Exception as e:
            logger.error(f"第{i}条向量生成失败: {e}")
            continue
    
    if not embeddings:
        return {"code": -2, "msg": "向量全部生成失败", "count": 0}
    
    # 取成功生成的文本
    texts = texts[:len(embeddings)]
    summaries = summaries[:len(embeddings)]
    
    # 生成唯一ID
    ids = []
    for i, text in enumerate(texts):
        unique = f"{source_name}_{i}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        ids.append(unique)
    
    metadatas = [
        {"source": source_name, "summary": summaries[i][:120], "index": i}
        for i in range(len(texts))
    ]
    
    # 分批存入 ChromaDB（每批100条）
    batch_size = 100
    total = 0
    for i in range(0, len(texts), batch_size):
        end = min(i + batch_size, len(texts))
        collection.add(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end]
        )
        total += (end - i)
    
    return {"code": 0, "msg": "导入成功", "count": total}


def search_knowledge(query: str, top_k: int = 3, min_score: float = 0.3) -> list[dict]:
    """搜索本地知识库"""
    ec = _get_embedding_client()
    collection = _get_chroma_collection()
    
    # 生成查询向量
    try:
        query_emb = ec.embed_text(query)
    except Exception as e:
        logger.error(f"查询向量生成失败: {e}")
        return []
    
    # 搜索
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k * 2,  # 多取一些，按分数过滤
        include=["documents", "metadatas", "distances"]
    )
    
    if not results["ids"] or not results["ids"][0]:
        return []
    
    # 转换为统一格式（distance越小越相似，转为score=1-distance）
    output = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i] if results["distances"] else 0
        score = 1.0 - distance  # cosine distance → similarity
        if score < min_score:
            continue
        output.append({
            "chunk_id": results["ids"][0][i],
            "score": round(score, 4),
            "content": results["documents"][0][i],
            "source": results["metadatas"][0][i].get("source", "unknown") if results["metadatas"] else "unknown",
            "summary": results["metadatas"][0][i].get("summary", "")[:120] if results["metadatas"] else ""
        })
    
    return output[:top_k]


def count_documents() -> int:
    """统计本地知识库的文档块数量"""
    try:
        collection = _get_chroma_collection()
        return collection.count()
    except Exception:
        return 0


def get_info() -> dict:
    """获取知识库信息"""
    try:
        count = count_documents()
        return {
            "type": "local",
            "path": KB_DIR,
            "chunk_count": count,
            "collection": "coze_doc_knowledge"
        }
    except Exception as e:
        return {"type": "local", "path": KB_DIR, "error": str(e)}