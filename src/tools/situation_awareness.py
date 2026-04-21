"""
态势感知模块 - 配网调度运行态势综合分析

功能：
1. 运行态势评估：综合评估当前配网调度运行状态
2. 态势指标计算：计算态势感知指标
3. 态势趋势分析：分析运行态势变化趋势
4. 态势预警：识别异常态势并预警
5. 态势报告生成：生成态势分析报告

态势维度：
- 业务量态势：计划任务量、非计划任务量、工作当量
- 人员态势：人员配置、技能分布、工作负荷
- 设备态势：设备状态、缺陷情况、重过载情况
- 天气势态：天气情况、极端天气预警、季节特点
- 事件态势：故障事件、重过载事件、应急事件
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 态势等级定义
# ============================================================

class SituationLevel(Enum):
    """态势等级"""
    EXCELLENT = "优秀"
    GOOD = "良好"
    NORMAL = "正常"
    WARNING = "警告"
    CRITICAL = "危急"

    @staticmethod
    def get_score(level: str) -> int:
        """获取态势等级对应的分数"""
        scores = {
            "优秀": 100,
            "良好": 80,
            "正常": 60,
            "警告": 40,
            "危急": 20
        }
        return scores.get(level, 60)


# ============================================================
# 态势指标定义
# ============================================================

class SituationIndicator(Enum):
    """态势指标"""
    # 业务量指标
    PLAN_WORKLOAD_RATE = "计划工作完成率"
    NON_PLAN_WORKLOAD_TREND = "非计划工作趋势"
    WORKLOAD_EFFICIENCY = "工作效率"

    # 人员指标
    STAFF_UTILIZATION = "人员利用率"
    STAFF_SKILL_COVERAGE = "技能覆盖率"
    STAFF_FATIGUE_INDEX = "疲劳指数"

    # 设备指标
    EQUIPMENT_HEALTH = "设备健康度"
    DEFECT_RESOLUTION_RATE = "缺陷解决率"
    OVERLOAD_CONTROL = "过载控制率"

    # 天气指标
    WEATHER_IMPACT = "天气影响度"
    EXTREME_WEATHER_RISK = "极端天气风险"

    # 事件指标
    FAULT_FREQUENCY = "故障频次"
    INCIDENT_RESPONSE_TIME = "事件响应时间"
    EMERGENCY_PREPAREDNESS = "应急准备度"


# ============================================================
# 态势感知器
# ============================================================

class SituationAwareness:
    """态势感知器"""

    @staticmethod
    def assess_overall_situation(
        workload_score: float,
        staff_score: float,
        equipment_score: float,
        weather_score: float,
        event_score: float
    ) -> Dict:
        """
        评估整体态势

        参数：
            workload_score: 业务量得分（0-100）
            staff_score: 人员得分（0-100）
            equipment_score: 设备得分（0-100）
            weather_score: 天气得分（0-100）
            event_score: 事件得分（0-100）

        返回：态势评估结果
        """
        # 加权计算综合得分
        weights = {
            "workload": 0.25,
            "staff": 0.25,
            "equipment": 0.2,
            "weather": 0.15,
            "event": 0.15
        }

        overall_score = (
            workload_score * weights["workload"] +
            staff_score * weights["staff"] +
            equipment_score * weights["equipment"] +
            weather_score * weights["weather"] +
            event_score * weights["event"]
        )

        # 确定态势等级
        if overall_score >= 90:
            level = SituationLevel.EXCELLENT.value
        elif overall_score >= 75:
            level = SituationLevel.GOOD.value
        elif overall_score >= 60:
            level = SituationLevel.NORMAL.value
        elif overall_score >= 40:
            level = SituationLevel.WARNING.value
        else:
            level = SituationLevel.CRITICAL.value

        return {
            "overall_score": round(overall_score, 2),
            "situation_level": level,
            "dimension_scores": {
                "workload": round(workload_score, 2),
                "staff": round(staff_score, 2),
                "equipment": round(equipment_score, 2),
                "weather": round(weather_score, 2),
                "event": round(event_score, 2)
            },
            "weights": weights
        }

    @staticmethod
    def analyze_situation_trend(
        historical_scores: List[Dict],
        days: int = 7
    ) -> Dict:
        """
        分析态势趋势

        参数：
            historical_scores: 历史得分列表
            days: 分析天数

        返回：趋势分析结果
        """
        if len(historical_scores) < 2:
            return {
                "trend": "数据不足",
                "trend_direction": "unknown",
                "average_score": 0,
                "max_score": 0,
                "min_score": 0
            }

        scores = [s.get("overall_score", 0) for s in historical_scores[-days:]]

        # 计算趋势
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / min(3, len(scores))
            earlier_avg = sum(scores[-6:-3]) / min(3, len(scores) - 3) if len(scores) >= 6 else sum(scores[:-3]) / max(1, len(scores) - 3)

            if recent_avg > earlier_avg + 5:
                trend = "上升趋势"
                direction = "up"
            elif recent_avg < earlier_avg - 5:
                trend = "下降趋势"
                direction = "down"
            else:
                trend = "平稳"
                direction = "stable"
        else:
            trend = "数据不足"
            direction = "unknown"

        return {
            "trend": trend,
            "trend_direction": direction,
            "average_score": round(sum(scores) / len(scores), 2),
            "max_score": round(max(scores), 2),
            "min_score": round(min(scores), 2),
            "latest_score": round(scores[-1], 2) if scores else 0,
            "score_series": scores
        }


# ============================================================
# 态势感知工具
# ============================================================

@tool
def assess_situation_awareness(
    target_date: str,
    workload_data: str = "{}",
    staff_data: str = "{}",
    equipment_data: str = "{}",
    weather_data: str = "{}",
    event_data: str = "{}",
    runtime: ToolRuntime = None
) -> str:
    """
    态势感知评估

    参数：
        target_date: 目标日期 (YYYY-MM-DD)
        workload_data: 工作量数据JSON字符串
        staff_data: 人员数据JSON字符串
        equipment_data: 设备数据JSON字符串
        weather_data: 天气数据JSON字符串
        event_data: 事件数据JSON字符串

    返回：态势感知评估结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="assess_situation_awareness")

    try:
        # 解析输入数据
        workload = json.loads(workload_data) if workload_data else {}
        staff = json.loads(staff_data) if staff_data else {}
        equipment = json.loads(equipment_data) if equipment_data else {}
        weather = json.loads(weather_data) if weather_data else {}
        event = json.loads(event_data) if event_data else {}

        # 计算各维度得分（简化版，实际应该基于具体数据计算）
        workload_score = 85.0  # 模拟得分
        staff_score = 78.0
        equipment_score = 90.0
        weather_score = 75.0
        event_score = 82.0

        # 评估整体态势
        overall = SituationAwareness.assess_overall_situation(
            workload_score, staff_score, equipment_score, weather_score, event_score
        )

        # 生成态势描述
        level = overall["situation_level"]
        if level == "优秀":
            description = "配网调度运行态势优秀，各项指标表现良好"
        elif level == "良好":
            description = "配网调度运行态势良好，大部分指标正常"
        elif level == "正常":
            description = "配网调度运行态势正常，各项指标在可控范围内"
        elif level == "警告":
            description = "配网调度运行态势存在警告，需关注部分指标"
        else:
            description = "配网调度运行态势危急，需立即采取措施"

        result = {
            "success": True,
            "target_date": target_date,
            "overall_assessment": overall,
            "description": description,
            "dimension_analysis": {
                "workload": {
                    "score": workload_score,
                    "status": "良好" if workload_score >= 80 else "正常",
                    "details": workload
                },
                "staff": {
                    "score": staff_score,
                    "status": "良好" if staff_score >= 80 else "正常",
                    "details": staff
                },
                "equipment": {
                    "score": equipment_score,
                    "status": "优秀" if equipment_score >= 90 else "良好",
                    "details": equipment
                },
                "weather": {
                    "score": weather_score,
                    "status": "正常" if weather_score >= 70 else "需关注",
                    "details": weather
                },
                "event": {
                    "score": event_score,
                    "status": "良好" if event_score >= 80 else "正常",
                    "details": event
                }
            },
            "recommendations": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 生成建议
        if workload_score < 80:
            result["recommendations"].append("建议优化工作量分配，提升工作效率")
        if staff_score < 80:
            result["recommendations"].append("建议加强人员培训，提升技能水平")
        if equipment_score < 80:
            result["recommendations"].append("建议加强设备巡检，及时处理缺陷")
        if weather_score < 70:
            result["recommendations"].append("建议关注天气变化，做好应急准备")

        if not result["recommendations"]:
            result["recommendations"].append("当前运行态势良好，继续保持")

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"态势感知评估失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "态势感知评估失败"
        }, ensure_ascii=False)


@tool
def generate_situation_report(
    situation_data: str,
    target_date: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    生成态势分析报告

    参数：
        situation_data: 态势数据JSON字符串（从assess_situation_awareness获取）
        target_date: 目标日期（可选）

    返回：态势分析报告JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="generate_situation_report")

    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        situation = json.loads(situation_data)
        overall = situation.get("overall_assessment", {})
        level = overall.get("situation_level", "正常")
        score = overall.get("overall_score", 60)

        # 生成Markdown报告
        report_lines = [
            f"# 配网调度运行态势分析报告",
            f"",
            f"**日期**: {target_date}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 🎯 整体态势评估",
            f"",
            f"**态势等级**: **{level}**",
            f"**综合得分**: {score}/100",
            f"**态势描述**: {situation.get('description', '')}",
            f"",
            f"## 📊 各维度态势",
            f"",
        ]

        # 各维度详情
        dimensions = situation.get("dimension_analysis", {})
        for dim_name, dim_info in dimensions.items():
            dim_score = dim_info.get("score", 0)
            dim_status = dim_info.get("status", "未知")
            dim_name_cn = {
                "workload": "业务量态势",
                "staff": "人员态势",
                "equipment": "设备态势",
                "weather": "天气态势",
                "event": "事件态势"
            }.get(dim_name, dim_name)

            report_lines.extend([
                f"### {dim_name_cn}",
                f"",
                f"**得分**: {dim_score}/100",
                f"**状态**: {dim_status}",
                f""
            ])

        # 建议
        recommendations = situation.get("recommendations", [])
        if recommendations:
            report_lines.extend([
                f"## 💡 改进建议",
                f""
            ])
            for rec in recommendations:
                report_lines.append(f"- {rec}")
            report_lines.append(f"")

        # 结束语
        if score >= 90:
            report_lines.append(f"✨ **运行态势优秀，继续保持！**")
        elif score >= 75:
            report_lines.append(f"✅ **运行态势良好，维持现有水平！**")
        elif score >= 60:
            report_lines.append(f"⚡ **运行态势正常，持续优化！**")
        elif score >= 40:
            report_lines.append(f"⚠️ **运行态势警告，需关注改进！**")
        else:
            report_lines.append(f"🚨 **运行态势危急，需立即行动！**")

        result = {
            "success": True,
            "target_date": target_date,
            "situation_level": level,
            "overall_score": score,
            "report_markdown": "\n".join(report_lines),
            "report_plain": "\n".join(report_lines),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"生成态势分析报告失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "生成态势分析报告失败"
        }, ensure_ascii=False)


@tool
def get_situation_dashboard(
    target_date: str = "",
    days_back: int = 7,
    runtime: ToolRuntime = None
) -> str:
    """
    获取态势看板数据（简化版）

    参数：
        target_date: 目标日期 (YYYY-MM-DD)，默认今天
        days_back: 向前追溯天数，默认7天

    返回：态势看板数据JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_situation_dashboard")

    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        # 模拟历史数据
        historical_scores = []
        base_score = 75
        for i in range(days_back):
            score = base_score + (i % 5) * 2
            historical_scores.append({
                "date": (datetime.now() - timedelta(days=days_back - i - 1)).strftime("%Y-%m-%d"),
                "overall_score": score,
                "situation_level": "良好" if score >= 75 else "正常"
            })

        # 分析趋势
        trend = SituationAwareness.analyze_situation_trend(historical_scores, days_back)

        # 当前态势
        current_situation = {
            "date": target_date,
            "overall_score": 82.0,
            "situation_level": "良好",
            "dimensions": {
                "workload": 85.0,
                "staff": 78.0,
                "equipment": 90.0,
                "weather": 75.0,
                "event": 82.0
            }
        }

        result = {
            "success": True,
            "target_date": target_date,
            "current_situation": current_situation,
            "historical_trend": trend,
            "historical_scores": historical_scores,
            "key_indicators": {
                "avg_score": trend["average_score"],
                "max_score": trend["max_score"],
                "min_score": trend["min_score"],
                "trend": trend["trend"]
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"获取态势看板数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取态势看板数据失败"
        }, ensure_ascii=False)
