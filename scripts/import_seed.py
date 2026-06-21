"""一键导入 seed_data.json 到本地 ChromaDB（批量直接写入）"""
import sys
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# 把项目根目录加入 PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seed_path = os.path.join(project_root, "assets", "knowledge", "seed_data.json")

if not os.path.exists(seed_path):
    logger.error(f"❌ 种子文件不存在: {seed_path}")
    sys.exit(1)

with open(seed_path, "r", encoding="utf-8") as f:
    entries = json.load(f)

logger.info(f"📦 共 {len(entries)} 条知识条目，准备导入...")

# 直接操作 ChromaDB
import chromadb
KB_DIR = os.path.join(project_root, "assets", "knowledge")
os.makedirs(KB_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=KB_DIR)

# 删除已有集合（如果存在）
try:
    client.delete_collection("coze_doc_knowledge")
except Exception:
    pass

# 创建新集合
collection = client.create_collection(
    "coze_doc_knowledge",
    metadata={"hnsw:space": "cosine"}
)

# 分段和分词
from tools.local_knowledge import _chunk_text, _segment, _get_vectorizer, _save_vectorizer
import hashlib

all_texts = []
all_ids = []
all_metadatas = []

for entry in entries:
    content = entry.get("content", "")
    source = entry.get("source", "unknown")
    if not content:
        continue
    chunks = _chunk_text(content)
    for ci, chunk in enumerate(chunks):
        text = chunk["text"]
        summary = chunk["summary"]
        unique = f"{source}_{ci}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        if unique not in all_ids:
            all_texts.append(text)
            all_ids.append(unique)
            all_metadatas.append({
                "source": source,
                "summary": summary[:120],
                "index": ci
            })

if not all_texts:
    logger.error("❌ 没有有效的知识条目")
    sys.exit(1)

logger.info(f"✂️  分割后共 {len(all_texts)} 个文本块，正在向量化...")

# 分词
all_segs = [_segment(t) for t in all_texts]

# 训练向量化器
vec = _get_vectorizer(force_rebuild=True)
vec.fit(all_segs)
_save_vectorizer()

# 生成向量
from tools.local_knowledge import _embed_texts
all_embeddings = _embed_texts(all_texts)

if not all_embeddings or len(all_embeddings) != len(all_texts):
    logger.error("❌ 向量生成失败")
    sys.exit(1)

# 分批写入
batch_size = 100
for i in range(0, len(all_texts), batch_size):
    end = min(i + batch_size, len(all_texts))
    collection.add(
        ids=all_ids[i:end],
        embeddings=all_embeddings[i:end],
        documents=all_texts[i:end],
        metadatas=all_metadatas[i:end]
    )

actual_count = collection.count()
logger.info(f"\n✅ 导入完成！ChromaDB 中共 {actual_count} 条知识条目")
logger.info(f"   种子文件: {seed_path}")
logger.info(f"   存储目录: {KB_DIR}")