"""一键导入 seed_data.json 到本地 ChromaDB（完全自包含，不依赖项目路径配置）"""
import sys
import os
import json
import hashlib
import re
import pickle
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# === 路径计算（从脚本位置推断项目根目录） ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
KB_DIR = os.path.join(PROJECT_ROOT, "assets", "knowledge")
SEED_PATH = os.path.join(KB_DIR, "seed_data.json")
VECTORIZER_PATH = os.path.join(KB_DIR, "vectorizer.pkl")

if not os.path.exists(SEED_PATH):
    logger.error(f"❌ 种子文件不存在: {SEED_PATH}")
    sys.exit(1)

# === 分词 ===
try:
    import jieba
except ImportError:
    logger.error("❌ jieba 未安装，请先运行: uv add jieba")
    sys.exit(1)

def _segment(text: str) -> str:
    """中文分词 + 保留原文（提升召回率）"""
    words = jieba.lcut(text)
    return " ".join(words) + " " + text

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """按段落和长度分割文本为 chunks"""
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

# === 向量化 ===
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    logger.error("❌ scikit-learn 未安装，请先运行: uv add scikit-learn")
    sys.exit(1)

# === ChromaDB ===
try:
    import chromadb
except ImportError:
    logger.error("❌ chromadb 未安装，请先运行: uv add chromadb")
    sys.exit(1)

# === 主流程 ===
with open(SEED_PATH, "r", encoding="utf-8") as f:
    entries = json.load(f)

logger.info(f"📦 种子文件共 {len(entries)} 条，正在分割...")

# 1. 分段
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

logger.info(f"✂️  分割后共 {len(all_texts)} 个文本块")

# 2. 分词
logger.info("🔧 正在分词（jieba）...")
all_segs = [_segment(t) for t in all_texts]

# 3. 训练向量化器
logger.info("📐 正在训练 TF-IDF 向量化器...")
vec = TfidfVectorizer(max_features=5000)
vec.fit(all_segs)
os.makedirs(KB_DIR, exist_ok=True)
with open(VECTORIZER_PATH, "wb") as f:
    pickle.dump(vec, f)
logger.info(f"   已保存向量化器: {VECTORIZER_PATH}")

# 4. 生成向量
logger.info("📊 正在生成向量...")
X = vec.transform(all_segs)
all_embeddings = X.toarray().tolist()

# 5. 写入 ChromaDB
logger.info("💾 正在写入 ChromaDB...")
os.makedirs(KB_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=KB_DIR)
try:
    client.delete_collection("coze_doc_knowledge")
except Exception:
    pass

collection = client.create_collection(
    "coze_doc_knowledge",
    metadata={"hnsw:space": "cosine"}
)

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
logger.info(f"\n✅ 导入完成！")
logger.info(f"   ChromaDB 存储目录: {KB_DIR}")
logger.info(f"   知识条目总数: {actual_count}")
logger.info(f"\n👉 重启服务后即可在知识库列表中看到全部数据")