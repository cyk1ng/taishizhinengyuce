"""
本地向量知识库 - 完全本地离线运行
- 分词：jieba（中文）
- 向量化：TF-IDF（scikit-learn）
- 存储：ChromaDB（本地持久化）
- 无任何云端依赖
"""

import os
import json
import hashlib
import logging
import pickle
import re
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "knowledge")
VECTORIZER_PATH = os.path.join(KB_DIR, "vectorizer.pkl")

_chroma_collection = None
_vectorizer = None


def _get_vectorizer(force_rebuild: bool = False):
    """获取/创建 TF-IDF 向量化器（本地，无需云端）"""
    global _vectorizer
    
    # 不需要重建：优先从本地加载，其次用全局缓存
    if not force_rebuild:
        if os.path.exists(VECTORIZER_PATH):
            try:
                with open(VECTORIZER_PATH, "rb") as f:
                    _vectorizer = pickle.load(f)
                logger.debug(f"从本地加载向量化器，词汇量: {len(_vectorizer.get_feature_names_out())}")
                return _vectorizer
            except Exception as e:
                logger.warning(f"加载本地向量化器失败，将重建: {e}")
        if _vectorizer is not None:
            try:
                _ = _vectorizer.get_feature_names_out()
                return _vectorizer
            except Exception:
                pass  # 未训练，继续重建
    
    # 需要重建：创建新的
    from sklearn.feature_extraction.text import TfidfVectorizer
    _vectorizer = TfidfVectorizer(
        max_features=5000,
        analyzer="word",
        token_pattern=r'(?u)\b\w+\b',
        ngram_range=(1, 2),
    )
    return _vectorizer


def _save_vectorizer():
    """保存向量化器到本地"""
    global _vectorizer
    if _vectorizer is not None:
        os.makedirs(KB_DIR, exist_ok=True)
        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(_vectorizer, f)


def _segment(text: str) -> str:
    """jieba 分词，返回空格分隔的词汇"""
    import jieba
    return " ".join(jieba.lcut(text))


def _embed_text(text: str) -> list[float]:
    """本地生成文本向量（TF-IDF）"""
    vec = _get_vectorizer()
    seg = _segment(text)
    
    # 训练时：如果向量化器还没fit，先fit
    try:
        X = vec.transform([seg])
    except Exception:
        # 向量化器未训练，用该文本初始化
        vec.fit([seg])
        _save_vectorizer()
        X = vec.transform([seg])
    
    return X.toarray()[0].tolist()


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成文本向量（本地）"""
    vec = _get_vectorizer()
    segs = [_segment(t) for t in texts]
    
    try:
        X = vec.transform(segs)
    except Exception:
        vec.fit(segs)
        _save_vectorizer()
        X = vec.transform(segs)
    
    return X.toarray().tolist()


def _get_chroma_collection():
    """获取 ChromaDB 集合（持久化到本地）"""
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        os.makedirs(KB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=KB_DIR)
        is_new = False
        try:
            _chroma_collection = _chroma_client.get_collection("coze_doc_knowledge")
        except Exception:
            _chroma_collection = _chroma_client.create_collection(
                "coze_doc_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            is_new = True
        
        # 首次创建 或 集合为空时自动播种默认数据
        if is_new:
            _auto_seed(_chroma_collection)
        elif _chroma_collection.count() == 0:
            logger.info("知识库为空，尝试自动播种种子数据...")
            _auto_seed(_chroma_collection)
    return _chroma_collection


def _auto_seed(collection):
    """首次运行时自动从种子文件导入默认知识库"""
    seed_path = os.path.join(KB_DIR, "seed_data.json")
    if not os.path.exists(seed_path):
        logger.warning(f"种子文件不存在: {seed_path}，跳过自动播种")
        return
    
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        
        if not entries:
            return
        
        logger.info(f"自动播种: 加载 {len(entries)} 条默认知识条目...")
        
        # 准备训练数据
        all_texts = [e["content"] for e in entries if e.get("content")]
        all_ids = [e["id"] for e in entries if e.get("id")]
        all_sources = [e["source"] for e in entries if e.get("source")]
        
        if not all_texts:
            return
        
        # 分词并训练向量化器
        global _vectorizer
        _vectorizer = _get_vectorizer(force_rebuild=True)
        segs = [_segment(t) for t in all_texts]
        _vectorizer.fit(segs)
        _save_vectorizer()
        
        # 生成向量
        all_embeddings = _embed_texts(all_texts)
        if not all_embeddings or len(all_embeddings) != len(all_texts):
            logger.error("自动播种: 向量生成失败")
            return
        
        # 分批存入
        batch_size = 100
        for i in range(0, len(all_texts), batch_size):
            end = min(i + batch_size, len(all_texts))
            collection.add(
                ids=all_ids[i:end],
                embeddings=all_embeddings[i:end],
                documents=all_texts[i:end],
                metadatas=[{"source": s, "summary": t[:120].replace('\n',' ').strip(), "index": idx}
                          for idx, (s, t) in enumerate(zip(all_sources[i:end], all_texts[i:end]))]
            )
        
        logger.info(f"自动播种完成: {len(all_texts)} 条")
    except Exception as e:
        logger.error(f"自动播种失败: {e}")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """按段落和长度分割文本为chunks"""
    # 先按 ## 标题分割（Markdown章节）
    sections = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        if len(section) <= chunk_size:
            summary = section[:120].replace('\n', ' ').strip()
            chunks.append({"text": section, "summary": summary[:120]})
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


def _reset_collection():
    """删除并重建集合（用于向量维度变化时）"""
    global _chroma_collection
    try:
        import chromadb
        _chroma_collection = None
        client = chromadb.PersistentClient(path=KB_DIR)
        try:
            client.delete_collection("coze_doc_knowledge")
        except Exception:
            pass
        _chroma_collection = client.create_collection(
            "coze_doc_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        return _chroma_collection
    except Exception as e:
        logger.error(f"重建集合失败: {e}")
        return _get_chroma_collection()


def import_document(content: str, source_name: str = "unknown") -> dict:
    """导入文档到本地知识库（完全本地运行）
    注：每次导入会重建整个向量空间，确保维度一致
    """
    collection = _get_chroma_collection()
    
    chunks = _chunk_text(content)
    if not chunks:
        return {"code": -1, "msg": "文档内容为空", "count": 0}
    
    new_texts = [c["text"] for c in chunks]
    new_summaries = [c["summary"] for c in chunks]
    
    # === 读取已有文档 + 新增文档 ===
    all_texts = []
    all_ids = []
    all_metadatas = []
    
    # 先读取已有
    existing_count = collection.count()
    if existing_count > 0:
        try:
            existing = collection.get(include=["documents", "metadatas"])
            if existing and existing.get("documents"):
                for i, doc in enumerate(existing["documents"]):
                    if doc:
                        all_texts.append(doc)
                        all_ids.append(existing["ids"][i])
                        meta = existing["metadatas"][i] if existing["metadatas"] else {}
                        all_metadatas.append(meta)
        except Exception:
            pass
    
    # 再追加新增
    for i, text in enumerate(new_texts):
        unique = f"{source_name}_{i}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        # 去重
        if unique not in all_ids:
            all_texts.append(text)
            all_ids.append(unique)
            all_metadatas.append({"source": source_name, "summary": new_summaries[i][:120], "index": i})
    
    if len(all_texts) == existing_count:
        return {"code": 0, "msg": "文档已存在，无新增内容", "count": 0}
    
    # 分词
    all_segs = []
    for text in all_texts:
        try:
            all_segs.append(_segment(text))
        except Exception:
            all_segs.append("")
    
    # 训练向量化器
    global _vectorizer
    _vectorizer = _get_vectorizer(force_rebuild=True)
    try:
        _vectorizer.fit(all_segs)
        _save_vectorizer()
    except Exception as e:
        logger.error(f"向量化器训练失败: {e}")
        return {"code": -2, "msg": f"向量化器初始化失败: {e}"}
    
    # 生成向量
    all_embeddings = _embed_texts(all_texts)
    if not all_embeddings:
        return {"code": -2, "msg": "向量生成失败", "count": 0}
    
    # 重建集合
    collection = _reset_collection()
    
    # 分批存入
    batch_size = 100
    total = 0
    for i in range(0, len(all_texts), batch_size):
        end = min(i + batch_size, len(all_texts))
        collection.add(
            ids=all_ids[i:end],
            embeddings=all_embeddings[i:end],
            documents=all_texts[i:end],
            metadatas=all_metadatas[i:end]
        )
        total += (end - i)
    
    return {"code": 0, "msg": "导入成功", "count": total}


def search_knowledge(query: str, top_k: int = 3, min_score: float = 0.1) -> list[dict]:
    """搜索本地知识库（完全本地运行）"""
    collection = _get_chroma_collection()
    
    try:
        query_emb = _embed_text(query)
    except Exception as e:
        logger.error(f"查询向量生成失败: {e}")
        return []
    
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k * 2,
        include=["documents", "metadatas", "distances"]
    )
    
    if not results["ids"] or not results["ids"][0]:
        return []
    
    output = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i] if results["distances"] else 0
        score = 1.0 - distance
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
        has_vec = os.path.exists(VECTORIZER_PATH)
        return {
            "type": "local",
            "engine": "chromadb + tfidf + jieba",
            "documents": count,
            "storage_path": KB_DIR,
            "has_vectorizer": has_vec,
            "cloud_dependency": "none"
        }
    except Exception as e:
        return {"type": "local", "error": str(e)}


def get_all_documents(page: int = 1, page_size: int = 20) -> dict:
    """获取所有文档（分页）"""
    try:
        collection = _get_chroma_collection()
        offset = (page - 1) * page_size
        results = collection.get(limit=page_size, offset=offset)
        total = collection.count()

        docs = []
        for i in range(len(results["ids"])):
            docs.append({
                "id": results["ids"][i],
                "content": results["documents"][i] if results["documents"] else "",
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
                "source": (results["metadatas"][i] or {}).get("source", "unknown") if results["metadatas"] else "unknown"
            })

        return {"total": total, "page": page, "page_size": page_size, "documents": docs}
    except Exception as e:
        return {"total": 0, "page": page, "page_size": page_size, "documents": [], "error": str(e)}


def delete_document(doc_id: str) -> dict:
    """删除指定文档"""
    try:
        collection = _get_chroma_collection()
        collection.delete(ids=[doc_id])
        return {"success": True, "id": doc_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_document(doc_id: str, content: str, source_name: str = None) -> dict:
    """更新指定文档（重新计算向量）"""
    try:
        collection = _get_chroma_collection()
        # 获取旧的 metadata
        old = collection.get(ids=[doc_id])
        if not old["ids"]:
            return {"success": False, "error": "文档不存在"}

        old_meta = (old["metadatas"] or [{}])[0] or {}
        meta = {"source": source_name or old_meta.get("source", "unknown")}

        # 重新计算向量
        seg_text = _segment(content)
        vec = _get_vectorizer()
        embedding = vec.transform([seg_text]).toarray()[0].tolist()

        collection.update(ids=[doc_id], embeddings=[embedding], documents=[content], metadatas=[meta])
        return {"success": True, "id": doc_id}
    except Exception as e:
        return {"success": False, "error": str(e)}