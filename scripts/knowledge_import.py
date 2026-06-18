"""
本地知识库导入/搜索脚本
数据存储在 assets/knowledge/ 目录下（ChromaDB）
"""

import argparse
import sys
import os

# 加入项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cmd_add_text(text, source_name="手动导入"):
    """导入文本"""
    from src.tools.local_knowledge import import_document
    result = import_document(text, source_name=source_name)
    print(f"✅ 导入完成: {result.get('count', 0)} 个知识片段")
    return result


def cmd_add_file(filepath, source_name=None):
    """导入文件"""
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    name = source_name or os.path.basename(filepath)
    return cmd_add_text(content, name)


def cmd_search(query, top_k=3):
    """搜索知识库"""
    from src.tools.local_knowledge import search_knowledge as local_search
    results = local_search(query=query, top_k=top_k)
    if not results:
        print("未找到相关内容")
        return
    print(f"找到 {len(results)} 条相关内容：\n")
    for i, r in enumerate(results, 1):
        preview = r["content"].replace('\n', ' ')[:150]
        print(f"--- 结果 {i} (匹配度: {r['score']:.3f}, 来源: {r.get('source', '?')}) ---")
        print(f"  {preview}...\n")


def cmd_info():
    """查看知识库信息"""
    from src.tools.local_knowledge import get_info, count_documents
    info = get_info()
    count = count_documents()
    print(f"📚 本地知识库信息")
    print(f"  类型: {info.get('type', 'local')}")
    print(f"  引擎: {info.get('engine', 'chromadb + tfidf + jieba')}")
    print(f"  知识片段数: {count}")
    print(f"  存储路径: {info.get('storage_path', '/workspace/projects/assets/knowledge')}")
    print(f"  云端依赖: {info.get('cloud_dependency', 'none')}")


def main():
    parser = argparse.ArgumentParser(description="本地知识库管理工具")
    subparsers = parser.add_subparsers(dest="command")

    # add text
    p_text = subparsers.add_parser("text", help="导入文本")
    p_text.add_argument("content", help="要导入的文本内容")
    p_text.add_argument("--name", "-n", default="手动导入", help="来源名称")

    # add file
    p_file = subparsers.add_parser("file", help="导入文件")
    p_file.add_argument("filepath", help="文件路径")
    p_file.add_argument("--name", "-n", default=None, help="来源名称（默认文件名）")

    # search
    p_search = subparsers.add_parser("search", help="搜索知识库")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--topk", "-k", type=int, default=3, help="返回结果数")

    # info
    subparsers.add_parser("info", help="查看知识库信息")

    args = parser.parse_args()

    if args.command == "text":
        cmd_add_text(args.content, args.name)
    elif args.command == "file":
        cmd_add_file(args.filepath, args.name)
    elif args.command == "search":
        cmd_search(args.query, args.topk)
    elif args.command == "info":
        cmd_info()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()