"""
风险预警模块 - 配网调度业务量风险识别与预警

功能：
1. 多维度风险识别：业务量风险、人员配置风险、设备状态风险、天气风险
2. 风险等级评估：低、中、高、紧急
3. 风险预警推送：生成预警信息和应对建议
4. 风险趋势分析：分析风险变化趋势
5. 风险报告生成：生成综合风险分析报告
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from langchain.tools import tool
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 风险等级定义
# ============================================================

class RiskLevel(Enum):
    """风险等级"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "紧急"

    @staticmethod
    def get_level(value: float, thresholds: List[float]) -> str:
        """根据数值获取风险等级"""
        if value < thresholds[0]:
            return RiskLevel.LOW.value
        elif value < thresholds[1]:
            return RiskLevel.MEDIUM.value
        elif value < thresholds[2]:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.CRITICAL.value

    @staticmethod
    def get_color(level: str) -> str:
        """获取风险等级对应的颜色"""
        colors = {
            "低": "#52c41a",      # 绿色
            "中": "#faad14",      # 黄色
            "高": "#ff4d4f",      # 红色
            "紧急": "#722ed1"     # 紫色
        }
        return colors.get(level, "#d9d9d9")


# ============================================================
# 风险类型定义
# ============================================================

class RiskType(Enum):
    """风险类型"""
    WORKLOAD_OVERLOAD = "业务量超负荷风险"
    STAFF_SHORTAGE = "人员配置不足风险"
    EQUIPMENT_STATUS = "设备状态风险"
    WEATHER_IMPACT = "天气影响风险"
    HIGH_INCIDENT = "高发事件风险"
    SCHEDULE_FAIRNESS = "排班公平性风险"
    HOLIDAY_PEAK = "节假日高峰风险"
    SEASONAL_PEAK = "季节性高峰风险"


# ============================================================
# 风险阈值配置
# ============================================================

RISK_THRESHOLDS = {
    "workload_overload": [1.0, 1.2, 1.5],      # [低, 中, 高]
    "staff_shortage": [0.6, 0.8, 1.0],
    "equipment_overload": [0.8, 0.9, 1.0],
    "weather_impact": [1.0, 1.3, 1.5],
    "incident_count": [3, 5, 8]
}


# ============================================================
# 风险检测类
# ============================================================

class RiskDetector:
    """风险检测器"""

    @staticmethod
    def detect_workload_overload_risk(
        total_workload: float,
        staff_capacity: float,
        threshold: float = 1.5
    ) -> Dict:
        """检测业务量超负荷风险"""
        if staff_capacity == 0:
            ratio = float('inf')
        else:
            ratio = total_workload / staff_capacity

        thresholds = RISK_THRESHOLDS["workload_overload"]
        level = RiskLevel.get_level(ratio, thresholds)

        suggestions = []
        if ratio >= threshold:
            suggestions.append(f"⚠️ 业务量超负荷（比值 {ratio:.2f}），建议增派人员")
        elif ratio >= 1.2:
            suggestions.append(f"⚡ 业务量偏高（比值 {ratio:.2f}），建议加强协作")
        elif ratio >= 1.0:
            suggestions.append(f"✅ 业务量适中（比值 {ratio:.2f}）")
        else:
            suggestions.append(f"ℹ️ 业务量较低（比值 {ratio:.2f}）")

        return {
            "risk_type": RiskType.WORKLOAD_OVERLOAD.value,
            "risk_level": level,
            "risk_value": round(ratio, 2),
            "threshold": threshold,
            "description": f"业务量与人员承载能力比值为 {ratio:.2f}",
            "suggestions": suggestions
        }

    @staticmethod
    def detect_staff_shortage_risk(
        current_staff: int,
        required_staff: int
    ) -> Dict:
        """检测人员配置不足风险"""
        if required_staff == 0:
            ratio = 1.0
        else:
            ratio = current_staff / required_staff

        level = "低" if ratio >= 1.0 else ("中" if ratio >= 0.8 else ("高" if ratio >= 0.6 else "紧急"))

        suggestions = []
        shortage = max(0, required_staff - current_staff)
        if shortage > 0:
            suggestions.append(f"⚠️ 人员不足，缺少 {shortage} 人")
        else:
            suggestions.append(f"✅ 人员配置充足")

        return {
            "risk_type": RiskType.STAFF_SHORTAGE.value,
            "risk_level": level,
            "risk_value": round(ratio, 2),
            "current_staff": current_staff,
            "required_staff": required_staff,
            "shortage_count": shortage,
            "suggestions": suggestions
        }

    @staticmethod
    def detect_weather_impact_risk(
        weather_impact_factor: float,
        extreme_weather: List[str]
    ) -> Dict:
        """检测天气影响风险"""
        thresholds = RISK_THRESHOLDS["weather_impact"]
        level = RiskLevel.get_level(weather_impact_factor, thresholds)

        suggestions = []
        if extreme_weather:
            suggestions.append(f"⚠️ 存在极端天气：{', '.join(extreme_weather)}")
        if weather_impact_factor >= 1.5:
            suggestions.append(f"🚨 天气影响严重（因子 {weather_impact_factor:.2f}）")
        elif weather_impact_factor >= 1.3:
            suggestions.append(f"⚡ 天气影响较大（因子 {weather_impact_factor:.2f}）")

        return {
            "risk_type": RiskType.WEATHER_IMPACT.value,
            "risk_level": level,
            "risk_value": round(weather_impact_factor, 2),
            "extreme_weather": extreme_weather,
            "suggestions": suggestions if suggestions else ["✅ 天气状况良好"]
        }

    @staticmethod
    def detect_high_incident_risk(
        fault_count: int,
        overload_count: int
    ) -> Dict:
        """检测高发事件风险"""
        total_incidents = fault_count + overload_count
        thresholds = RISK_THRESHOLDS["incident_count"]
        level = RiskLevel.get_level(total_incidents, thresholds)

        suggestions = []
        if fault_count >= 5:
            suggestions.append(f"🚨 故障频发（{fault_count} 次）")
        if overload_count >= 3:
            suggestions.append(f"⚠️ 重过载频繁（{overload_count} 次）")

        return {
            "risk_type": RiskType.HIGH_INCIDENT.value,
            "risk_level": level,
            "risk_value": total_incidents,
            "fault_count": fault_count,
            "overload_count": overload_count,
            "suggestions": suggestions if suggestions else ["✅ 近期运行平稳"]
        }


# ============================================================
# 风险预警工具
# ============================================================

@tool
def assess_comprehensive_risk(
    target_date: str,
    workload_data: str = "{}",
    staff_data: str = "{}",
    weather_data: str = "{}",
    incident_data: str = "{}") -> str:
    """
    综合风险评估

    参数：
        target_date: 目标日期 (YYYY-MM-DD)
        workload_data: 工作量数据JSON字符串
        staff_data: 人员数据JSON字符串
        weather_data: 天气数据JSON字符串
        incident_data: 事件数据JSON字符串

    返回：综合风险评估报告JSON字符串
    """
    ctx = request_context.get() or new_context(method="assess_comprehensive_risk")

    try:
        # 解析输入数据
        workload = json.loads(workload_data) if workload_data else {}
        staff = json.loads(staff_data) if staff_data else {}
        weather = json.loads(weather_data) if weather_data else {}
        incident = json.loads(incident_data) if incident_data else {}

        # 执行各类风险检测
        risks = []

        # 1. 业务量超负荷风险
        if workload and staff:
            total_workload = workload.get("total_weight", 0)
            staff_capacity = len(staff.get("staff_list", [])) * 1.3  # 假设每人1.3当量
            risks.append(RiskDetector.detect_workload_overload_risk(total_workload, staff_capacity))

        # 2. 人员配置不足风险
        if staff:
            current = len(staff.get("staff_list", []))
            required = staff.get("required_count", current)
            risks.append(RiskDetector.detect_staff_shortage_risk(current, required))

        # 3. 天气影响风险
        if weather:
            impact_factor = weather.get("weather_impact_factor", 1.0)
            extreme = weather.get("extreme_weather", [])
            risks.append(RiskDetector.detect_weather_impact_risk(impact_factor, extreme))

        # 4. 高发事件风险
        if incident:
            fault_count = incident.get("fault_count", 0)
            overload_count = incident.get("overload_count", 0)
            risks.append(RiskDetector.detect_high_incident_risk(fault_count, overload_count))

        # 综合评估
        critical_count = sum(1 for r in risks if r["risk_level"] == "紧急")
        high_count = sum(1 for r in risks if r["risk_level"] == "高")
        medium_count = sum(1 for r in risks if r["risk_level"] == "中")

        if critical_count > 0:
            overall_level = "紧急"
        elif high_count > 0:
            overall_level = "高"
        elif medium_count > 0:
            overall_level = "中"
        else:
            overall_level = "低"

        # 生成建议
        all_suggestions = []
        for risk in risks:
            all_suggestions.extend(risk.get("suggestions", []))

        result = {
            "success": True,
            "target_date": target_date,
            "overall_risk_level": overall_level,
            "risk_summary": {
                "total_risks": len(risks),
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "low": len(risks) - critical_count - high_count - medium_count
            },
            "risks": risks,
            "recommendations": all_suggestions,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"综合风险评估失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "综合风险评估失败"
        }, ensure_ascii=False)


@tool
def generate_risk_alert_report(
    risk_data: str,
    target_date: str = "") -> str:
    """
    生成风险预警报告

    参数：
        risk_data: 风险数据JSON字符串（从assess_comprehensive_risk获取）
        target_date: 目标日期（可选）

    返回：风险预警报告JSON字符串
    """
    ctx = request_context.get() or new_context(method="generate_risk_alert_report")

    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        risk = json.loads(risk_data)
        overall_level = risk.get("overall_risk_level", "低")

        # 生成Markdown报告
        report_lines = [
            f"# 配网调度风险预警报告",
            f"",
            f"**日期**: {target_date}",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 🎯 综合风险等级",
            f"",
            f"**当前风险等级**: <span style='color:{RiskLevel.get_color(overall_level)}'>**{overall_level}**</span>",
            f"",
        ]

        # 风险汇总
        summary = risk.get("risk_summary", {})
        report_lines.extend([
            f"## 📊 风险概览",
            f"",
            f"| 风险等级 | 数量 |",
            f"|---------|------|",
            f"| 🚨 紧急 | {summary.get('critical', 0)} |",
            f"| ⚠️ 高 | {summary.get('high', 0)} |",
            f"| ⚡ 中 | {summary.get('medium', 0)} |",
            f"| ✅ 低 | {summary.get('low', 0)} |",
            f"",
        ])

        # 详细风险
        report_lines.append(f"## 🔍 详细风险分析")
        report_lines.append(f"")

        for idx, risk_item in enumerate(risk.get("risks", []), 1):
            level = risk_item.get("risk_level", "低")
            risk_type = risk_item.get("risk_type", "未知")
            description = risk_item.get("description", "")
            suggestions = risk_item.get("suggestions", [])

            report_lines.extend([
                f"### {idx}. {risk_type}",
                f"",
                f"**风险等级**: <span style='color:{RiskLevel.get_color(level)}'>**{level}**</span>",
                f"**描述**: {description}",
                f"",
                f"**应对建议**:",
                f""
            ])
            for suggestion in suggestions:
                report_lines.append(f"- {suggestion}")
            report_lines.append(f"")

        # 综合建议
        recommendations = risk.get("recommendations", [])
        if recommendations:
            report_lines.extend([
                f"## 💡 综合建议",
                f""
            ])
            for rec in recommendations:
                report_lines.append(f"- {rec}")
            report_lines.append(f"")

        # 结束语
        if overall_level == "紧急":
            report_lines.append(f"⚠️ **系统处于紧急风险状态，请立即采取应对措施！**")
        elif overall_level == "高":
            report_lines.append(f"⚠️ **系统存在高风险，请密切关注并及时处理！**")
        elif overall_level == "中":
            report_lines.append(f"⚡ **系统存在中等风险，建议提前做好应对准备！**")
        else:
            report_lines.append(f"✅ **系统运行状态良好，继续保持！**")

        result = {
            "success": True,
            "target_date": target_date,
            "overall_risk_level": overall_level,
            "report_markdown": "\n".join(report_lines),
            "report_plain": "\n".join(report_lines),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"生成风险预警报告失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "生成风险预警报告失败"
        }, ensure_ascii=False)


@tool
def check_daily_risks(
    target_date: str = "") -> str:
    """
    每日风险检查（简化版，用于快速评估）

    参数：
        target_date: 目标日期 (YYYY-MM-DD)，默认今天

    返回：风险检查结果JSON字符串
    """
    ctx = request_context.get() or new_context(method="check_daily_risks")

    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        # 这里简化处理，实际应该从数据库或API获取实时数据
        # 模拟数据
        simulated_risks = {
            "workload": {
                "total_workload": 2.5,
                "staff_capacity": 1.5,
                "risk_level": "高"
            },
            "staff": {
                "current": 3,
                "required": 4,
                "risk_level": "中"
            },
            "weather": {
                "impact_factor": 1.2,
                "extreme_weather": ["小雨"],
                "risk_level": "中"
            },
            "incident": {
                "fault_count": 2,
                "overload_count": 1,
                "risk_level": "低"
            }
        }

        # 综合评估
        levels = [r["risk_level"] for r in simulated_risks.values()]
        if "高" in levels or any(r.get("risk_level") == "紧急" for r in simulated_risks.values()):
            overall = "高"
        elif "中" in levels:
            overall = "中"
        else:
            overall = "低"

        result = {
            "success": True,
            "target_date": target_date,
            "overall_risk_level": overall,
            "risk_details": simulated_risks,
            "recommendations": [
                "建议加强值班人员协作",
                "关注天气变化对业务量的影响"
            ],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"每日风险检查失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "每日风险检查失败"
        }, ensure_ascii=False)
