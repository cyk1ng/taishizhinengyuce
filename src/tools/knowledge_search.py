"""
知识库搜索工具 - 使用本地 ChromaDB 向量知识库
数据存储在 assets/knowledge/ 目录下
"""

import logging
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

logger = logging.getLogger(__name__)


@tool
def search_knowledge(query: str, top_k: int = 3) -> str:
    """搜索本地向量知识库，当需要查询系统架构、技术栈、业务规则、排班规则、工作当量计算、数据库表结构、风险预警规则等信息时使用"""
    ctx = request_context.get() or new_context(method="search_knowledge")
    
    try:
        from tools.local_knowledge import search_knowledge as local_search
        results = local_search(query=query, top_k=top_k)
    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索失败: {e}"
    
    if not results:
        return f"未找到与「{query}」相关的知识"
    
    output = [f"找到 {len(results)} 条相关内容：\n"]
    for i, r in enumerate(results, 1):
        content = r["content"].strip()
        source = r.get("source", "未知")
        score = r.get("score", 0)
        output.append(f"--- 结果 {i} (匹配度: {score:.3f}, 来源: {source}) ---")
        output.append(content)
        output.append("")
    
    return "\n".join(output)


@tool
def import_knowledge(text: str, source_name: str = "用户导入") -> str:
    """向本地知识库导入新内容，当用户要求将信息加入知识库时使用"""
    ctx = request_context.get() or new_context(method="import_knowledge")
    
    try:
        from tools.local_knowledge import import_document
        result = import_document(text, source_name=source_name)
        if result["code"] == 0:
            return f"✅ 导入成功！共导入 {result['count']} 个知识片段，来源: {source_name}"
        else:
            return f"❌ 导入失败: {result['msg']}"
    except Exception as e:
        logger.error(f"知识库导入失败: {e}")
        return f"❌ 导入失败: {e}"