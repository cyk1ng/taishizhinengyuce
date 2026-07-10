"""
页面快照读取工具
==============
Agent 在分析页面数据时，优先通过此工具读取当前页面快照，
确保分析的是用户当前看到的（可能已修改过的）数据，而非原始数据库数据。
"""

import json
import datetime
import logging
from typing import Optional
from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
def read_page_snapshot(target_date: Optional[str] = None) -> str:
    """
    读取当前页面的数据快照（用户看到的页面数据，可能已手动修改过）。
    优先使用此工具获取页面数据进行分析，而非从数据库重新查询。

    参数：
        target_date: 目标日期，格式 YYYY-MM-DD，不传则默认为今天

    返回：
        页面数据 JSON 字符串，包含：
        - statistics: 统计卡片数据（总计划量、进行中、已完成、非计划总量等）
        - plan_workload: 计划工作量各分类详情（检修、方式单、设备投退、周计划、保供电）
        - non_plan_workload: 非计划工作量各分类（故障、缺陷、重过载）
        - weather: 天气数据（温度、降水、风力、极端天气）
        - staff: 人员信息（当前值班人数、班组、超负荷状态）
        - captured_at: 快照采集时间
    """
    today = target_date or datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        from snapshot_manager import get_snapshot
        data = get_snapshot(today)

        if data:
            result = {
                "success": True,
                "source": "snapshot",
                "date": today,
                "data": data
            }
            logger.info(f"[Tool:read_page_snapshot] 成功读取 {today} 快照")
            return json.dumps(result, ensure_ascii=False, default=str)
        else:
            # 没有快照，返回空数据并提示
            result = {
                "success": False,
                "source": "snapshot",
                "date": today,
                "message": f"{today} 暂无页面快照数据，请先加载页面或使用其他工具查询数据库",
            }
            logger.info(f"[Tool:read_page_snapshot] {today} 无快照数据")
            return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        error_result = {
            "success": False,
            "source": "snapshot",
            "date": today,
            "error": f"读取快照失败: {str(e)}"
        }
        logger.error(f"[Tool:read_page_snapshot] 读取失败: {e}")
        return json.dumps(error_result, ensure_ascii=False, default=str)