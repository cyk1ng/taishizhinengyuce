#!/usr/bin/env python3
"""
向量知识库导入工具
用法：
  # 导入文本
  python scripts/knowledge_import.py text "你要导入的内容"
  
  # 导入文件内容
  python scripts/knowledge_import.py file /path/to/file.txt
  
  # 导入网页内容
  python scripts/knowledge_import.py url https://example.com/doc
  
  # 搜索知识库
  python scripts/knowledge_import.py search "查询关键词"
  
  # 指定数据集（默认 coze_doc_knowledge）
  python scripts/knowledge_import.py text "内容" --dataset my_dataset
"""

import sys
import os
import logging
logging.getLogger("cozeloop").setLevel(logging.WARNING)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from coze_coding_dev_sdk import KnowledgeClient, Config, KnowledgeDocument, DataSourceType, ChunkConfig


def add_text(text: str, dataset: str = "coze_doc_knowledge"):
    """导入纯文本"""
    config = Config()
    client = KnowledgeClient(config=config)

    doc = KnowledgeDocument(
        source=DataSourceType.TEXT,
        raw_data=text
    )
    chunk_config = ChunkConfig(
        separator="",
        max_tokens=3000,
        remove_extra_spaces=True
    )
    resp = client.add_documents(
        documents=[doc],
        table_name=dataset,
        chunk_config=chunk_config
    )
    if resp.code == 0:
        print(f"✅ 导入成功！文档ID: {resp.doc_ids}")
    else:
        print(f"❌ 导入失败: code={resp.code}, msg={resp.msg}")
    return resp


def add_file(filepath: str, dataset: str = "coze_doc_knowledge"):
    """导入文件内容"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"📄 读取文件: {filepath} ({len(content)} 字符)")
    return add_text(content, dataset)


def add_url(url: str, dataset: str = "coze_doc_knowledge"):
    """导入网页内容"""
    config = Config()
    client = KnowledgeClient(config=config)

    doc = KnowledgeDocument(
        source=DataSourceType.URL,
        raw_data=url
    )
    chunk_config = ChunkConfig(
        separator="\n\n",
        max_tokens=2000,
        remove_extra_spaces=True
    )
    resp = client.add_documents(
        documents=[doc],
        table_name=dataset,
        chunk_config=chunk_config
    )
    if resp.code == 0:
        print(f"✅ 网页导入成功！文档ID: {resp.doc_ids}")
    else:
        print(f"❌ 导入失败: code={resp.code}, msg={resp.msg}")
    return resp


def search(query: str, top_k: int = 3, dataset: str = None):
    """搜索知识库"""
    config = Config()
    client = KnowledgeClient(config=config)

    kwargs = {"query": query, "top_k": top_k}
    if dataset:
        kwargs["table_names"] = [dataset]

    resp = client.search(**kwargs)
    
    if resp.code == 0:
        print(f"🔍 找到 {len(resp.chunks)} 条结果:\n")
        for i, chunk in enumerate(resp.chunks):
            print(f"--- 结果 {i+1} (匹配度: {chunk.score:.3f}) ---")
            print(chunk.content[:300])
            print()
    else:
        print(f"❌ 搜索失败: code={resp.code}")
    return resp


def print_usage():
    print(__doc__)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="向量知识库管理工具")
    parser.add_argument("action", choices=["text", "file", "url", "search"], help="操作类型")
    parser.add_argument("input", help="文本内容 / 文件路径 / URL / 搜索关键词")
    parser.add_argument("--dataset", "-d", default="coze_doc_knowledge", help="数据集名称")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="搜索结果数量")

    args = parser.parse_args()

    if args.action == "text":
        add_text(args.input, args.dataset)
    elif args.action == "file":
        add_file(args.input, args.dataset)
    elif args.action == "url":
        add_url(args.input, args.dataset)
    elif args.action == "search":
        search(args.input, args.top_k, args.dataset)