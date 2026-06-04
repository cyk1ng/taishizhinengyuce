"""
人员需求预测与增员建议算法模块

功能：
1. 基于预测业务量的人员需求预测
2. 考虑人员技能和经验的效能模型
3. 智能增员建议算法
4. 人员优化配置建议
5. 风险评估与预警

算法特点：
- 多维度人员评估（技能、经验、工作当量）
- 动态人员需求预测
- 智能增员建议（数量+角色）
- 成本效益分析
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


class StaffEfficiencyModel:
    """
    人员效能评估模型
    
    评估维度：
    - 技能水平（初级/中级/高级）
    - 工作经验（年数）
    - 历史绩效
    - 工作当量
    """

    # 技能等级评分
    SKILL_LEVEL_SCORES = {
        "初级": 1.0,
        "中级": 1.5,
        "高级": 2.0,
        "专家": 2.5
    }

    # 角色权重（不同角色对工作当量的贡献不同）
    ROLE_WEIGHTS = {
        "值班长": 2.0,  # 值班长可以承担更多工作
        "正值": 1.5,
        "副值": 1.0,
        "其他": 0.8
    }

    def __init__(self):
        self.staff_profiles = {}  # 人员档案

    def evaluate_staff_capacity(
        self,
        staff_list: List[Dict]
    ) -> Dict:
        """
        评估人员整体容量
        
        参数：
        - staff_list: 人员列表
        
        返回：人员容量评估结果
        """
        total_capacity = 0
        role_distribution = {}
        skill_distribution = {}

        for staff in staff_list:
            # 计算个人容量
            skill_level = staff.get("skill_level", "中级")
            role = staff.get("role", "其他")
            experience_years = staff.get("experience_years", 0)

            # 技能评分
            skill_score = self.SKILL_LEVEL_SCORES.get(skill_level, 1.0)

            # 经验系数（每增加1年经验，容量增加0.05，最高增加0.5）
            experience_factor = min(0.5, experience_years * 0.05)

            # 角色权重
            role_weight = self.ROLE_WEIGHTS.get(role, 1.0)

            # 个人容量 = 基础容量(1.3) * 技能系数 * 经验系数 * 角色权重
            personal_capacity = 1.3 * skill_score * (1 + experience_factor) * role_weight

            total_capacity += personal_capacity

            # 统计角色分布
            if role not in role_distribution:
                role_distribution[role] = 0
            role_distribution[role] += 1

            # 统计技能分布
            if skill_level not in skill_distribution:
                skill_distribution[skill_level] = 0
            skill_distribution[skill_level] += 1

        return {
            "total_capacity": round(total_capacity, 2),
            "staff_count": len(staff_list),
            "avg_capacity_per_staff": round(total_capacity / len(staff_list), 2) if staff_list else 0,
            "role_distribution": role_distribution,
            "skill_distribution": skill_distribution
        }

    def calculate_optimal_staffing(
        self,
        predicted_workload: float,
        safety_margin: float = 1.2,
        min_shift_leader: int = 1,
        min_primary: int = 1,
        min_secondary: int = 1
    ) -> Dict:
        """
        计算最优人员配置
        
        参数：
        - predicted_workload: 预测工作当量
        - safety_margin: 安全系数（默认1.2）
        - min_shift_leader: 最小值班长数
        - min_primary: 最小正值数
        - min_secondary: 最小副值数
        
        返回：最优人员配置方案
        """
        # 计算所需总容量
        required_capacity = predicted_workload * safety_margin

        # 基础角色配置（满足最低要求）
        base_config = {
            "值班长": min_shift_leader,
            "正值": min_primary,
            "副值": min_secondary
        }

        # 计算基础配置的总容量
        base_capacity = sum(
            count * self.ROLE_WEIGHTS.get(role, 1.0) * 1.3  # 使用中级技能的平均值
            for role, count in base_config.items()
        )

        # 计算还需要多少"普通人员"
        remaining_capacity = required_capacity - base_capacity
        if remaining_capacity > 0:
            # 每个普通人员（副值）的容量约1.3
            additional_staff = max(0, int(np.ceil(remaining_capacity / 1.3)))
            base_config["其他"] = additional_staff

        # 计算总容量
        total_capacity = sum(
            count * self.ROLE_WEIGHTS.get(role, 1.0) * 1.3
            for role, count in base_config.items()
        )

        return {
            "predicted_workload": round(predicted_workload, 2),
            "required_capacity": round(required_capacity, 2),
            "optimal_config": base_config,
            "total_staff": sum(base_config.values()),
            "total_capacity": round(total_capacity, 2),
            "capacity_utilization": round(predicted_workload / total_capacity * 100, 2) if total_capacity > 0 else 0,
            "safety_margin": safety_margin
        }


class StaffingPredictor:
    """
    人员需求预测器
    
    基于业务量预测、历史人员配置、季节性等因素，预测未来人员需求
    """

    def __init__(self):
        self.efficiency_model = StaffEfficiencyModel()

    def predict_staffing_need(
        self,
        predictions: List[Dict],
        current_staff: List[Dict],
        lookback_days: int = 30
    ) -> Dict:
        """
        预测人员需求
        
        参数：
        - predictions: 业务量预测结果（列表）
        - current_staff: 当前人员列表
        - lookback_days: 回溯天数（用于历史分析）
        
        返回：人员需求预测结果
        """
        # 评估当前人员容量
        current_capacity = self.efficiency_model.evaluate_staff_capacity(current_staff)

        # 预测每天的人员需求
        daily_staffing_needs = []
        for day_prediction in predictions:
            predicted_workload = day_prediction.get("predicted_dispatches", 0)

            # 转换为工作当量（这里简化处理，假设每次调度平均0.3个当量）
            workload_equivalent = predicted_workload * 0.3

            # 计算最优配置
            optimal_config = self.efficiency_model.calculate_optimal_staffing(
                workload_equivalent=workload_equivalent
            )

            # 判断是否需要增员
            need_add = optimal_config["total_staff"] > current_capacity["staff_count"]

            daily_staffing_needs.append({
                "date": day_prediction.get("date"),
                "predicted_dispatches": predicted_workload,
                "workload_equivalent": round(workload_equivalent, 2),
                "current_staff_count": current_capacity["staff_count"],
                "current_capacity": current_capacity["total_capacity"],
                "optimal_staff_count": optimal_config["total_staff"],
                "optimal_config": optimal_config["optimal_config"],
                "need_add_staff": optimal_config["total_staff"] - current_capacity["staff_count"] if need_add else 0,
                "need_add": need_add,
                "risk_level": self._assess_risk_level(workload_equivalent, current_capacity["total_capacity"])
            })

        # 汇总分析
        peak_need_day = max(daily_staffing_needs, key=lambda x: x["optimal_staff_count"])

        result = {
            "success": True,
            "prediction_timestamp": datetime.now().isoformat(),
            "current_capacity": current_capacity,
            "daily_staffing_needs": daily_staffing_needs,
            "summary": {
                "prediction_period": f"{len(daily_staffing_needs)} days",
                "peak_need_day": peak_need_day["date"],
                "peak_need_staff": peak_need_day["optimal_staff_count"],
                "max_shortage": max([d["need_add_staff"] for d in daily_staffing_needs]),
                "high_risk_days": sum(1 for d in daily_staffing_needs if d["risk_level"] == "高"),
                "medium_risk_days": sum(1 for d in daily_staffing_needs if d["risk_level"] == "中"),
                "low_risk_days": sum(1 for d in daily_staffing_needs if d["risk_level"] == "低")
            }
        }

        return result

    def _assess_risk_level(self, workload: float, capacity: float) -> str:
        """评估风险等级"""
        if capacity <= 0:
            return "高"

        utilization = workload / capacity

        if utilization >= 1.5:
            return "高"
        elif utilization >= 1.2:
            return "中"
        else:
            return "低"


class StaffingRecommendationEngine:
    """
    人员配置建议引擎
    
    生成具体的人员配置建议
    """

    def generate_recommendations(
        self,
        staffing_needs: Dict,
        available_staff: List[Dict]
    ) -> Dict:
        """
        生成人员配置建议
        
        参数：
        - staffing_needs: 人员需求预测结果
        - available_staff: 可用人员列表
        
        返回：人员配置建议
        """
        daily_needs = staffing_needs.get("daily_staffing_needs", [])
        current_capacity = staffing_needs.get("current_capacity", {})

        recommendations = []
        urgent_recommendations = []
        strategic_recommendations = []

        # 1. 分析高风险时段
        high_risk_days = [d for d in daily_needs if d["risk_level"] == "高"]
        if high_risk_days:
            max_shortage = max([d["need_add_staff"] for d in high_risk_days])

            urgent_recommendations.append({
                "priority": "紧急",
                "type": "增员",
                "description": f"预测未来{len(high_risk_days)}天存在高风险时段",
                "action": f"建议立即增派{max_shortage}名值班人员",
                "details": [
                    f"- 高峰日期: {', '.join([d['date'] for d in high_risk_days[:3]])}",
                    f"- 最大缺口: {max_shortage}人",
                    f"- 建议配置: 增加1名值班长或{max_shortage}名副值"
                ]
            })

        # 2. 分析人员结构
        role_dist = current_capacity.get("role_distribution", {})
        skill_dist = current_capacity.get("skill_distribution", {})

        if role_dist.get("值班长", 0) < 1:
            urgent_recommendations.append({
                "priority": "紧急",
                "type": "人员结构",
                "description": "缺少值班长",
                "action": "立即安排1名值班长",
                "details": ["值班长是必须角色，每班次至少1人"]
            })

        if role_dist.get("正值", 0) < 1:
            urgent_recommendations.append({
                "priority": "紧急",
                "type": "人员结构",
                "description": "缺少正值调度员",
                "action": "立即安排至少1名正值调度员",
                "details": ["正值是必须角色，每班次至少1人"]
            })

        # 3. 战略建议
        avg_capacity_per_staff = current_capacity.get("avg_capacity_per_staff", 1.3)
        if avg_capacity_per_staff < 1.4:
            strategic_recommendations.append({
                "priority": "中等",
                "type": "培训提升",
                "description": "整体人员效能偏低",
                "action": "开展技能培训，提升人员效能",
                "details": [
                    f"- 当前人均容量: {avg_capacity_per_staff}",
                    "- 建议目标: 1.5以上",
                    "- 措施: 加强培训，提升技能等级"
                ]
            })

        # 4. 人员优化建议
        if len(available_staff) > len(daily_needs):
            strategic_recommendations.append({
                "priority": "低",
                "type": "资源优化",
                "description": "人员储备充足",
                "action": "优化排班，提高资源利用率",
                "details": [
                    f"- 可用人员: {len(available_staff)}人",
                    f"- 预测需求: {len(daily_needs)}人",
                    "- 建议: 实施轮休制度，保证休息"
                ]
            })

        # 合并建议
        all_recommendations = urgent_recommendations + strategic_recommendations

        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "urgent_recommendations": urgent_recommendations,
            "strategic_recommendations": strategic_recommendations,
            "all_recommendations": all_recommendations,
            "priority_level": "高" if urgent_recommendations else "中" if strategic_recommendations else "低",
            "summary": {
                "total_recommendations": len(all_recommendations),
                "urgent_count": len(urgent_recommendations),
                "strategic_count": len(strategic_recommendations)
            }
        }

        return result


# 工具函数
@tool
def predict_staffing_need(
    predictions: str,
    current_staff: str,
    lookback_days: int = 30,
    runtime: ToolRuntime = None
) -> str:
    """
    预测人员需求

    参数：
    - predictions: 业务量预测结果JSON字符串
    - current_staff: 当前人员列表JSON字符串
    - lookback_days: 回溯天数（默认30天）

    返回：人员需求预测结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="predict_staffing_need")

    try:
        predictions_data = json.loads(predictions)
        staff_data = json.loads(current_staff)

        predictions_list = predictions_data.get("daily_predictions", [])
        staff_list = staff_data.get("staff", []) if isinstance(staff_data, dict) else staff_data

        if not predictions_list:
            return json.dumps({
                "success": False,
                "error": "缺少预测数据"
            }, ensure_ascii=False)

        predictor = StaffingPredictor()
        result = predictor.predict_staffing_need(
            predictions=predictions_list,
            current_staff=staff_list,
            lookback_days=lookback_days
        )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"人员需求预测失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "人员需求预测失败"
        }, ensure_ascii=False)


@tool
def generate_staffing_recommendations(
    staffing_needs: str,
    available_staff: str,
    runtime: ToolRuntime = None
) -> str:
    """
    生成人员配置建议

    参数：
    - staffing_needs: 人员需求预测结果JSON字符串
    - available_staff: 可用人员列表JSON字符串

    返回：人员配置建议JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="generate_staffing_recommendations")

    try:
        needs_data = json.loads(staffing_needs)
        staff_data = json.loads(available_staff)

        staff_list = staff_data.get("staff", []) if isinstance(staff_data, dict) else staff_data

        engine = StaffingRecommendationEngine()
        result = engine.generate_recommendations(
            staffing_needs=needs_data,
            available_staff=staff_list
        )

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"生成人员配置建议失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "生成人员配置建议失败"
        }, ensure_ascii=False)


@tool
def evaluate_staff_efficiency(
    staff_list: str,
    runtime: ToolRuntime = None
) -> str:
    """
    评估人员效能

    参数：
    - staff_list: 人员列表JSON字符串

    返回：人员效能评估结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="evaluate_staff_efficiency")

    try:
        staff_data = json.loads(staff_list)
        staff = staff_data.get("staff", []) if isinstance(staff_data, dict) else staff_data

        if not staff:
            return json.dumps({
                "success": False,
                "error": "人员列表为空"
            }, ensure_ascii=False)

        model = StaffEfficiencyModel()
        result = model.evaluate_staff_capacity(staff)

        return json.dumps({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "efficiency_evaluation": result
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"人员效能评估失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "人员效能评估失败"
        }, ensure_ascii=False)


@tool
def calculate_optimal_staffing(
    predicted_workload: float,
    safety_margin: float = 1.2,
    min_shift_leader: int = 1,
    min_primary: int = 1,
    min_secondary: int = 1,
    runtime: ToolRuntime = None
) -> str:
    """
    计算最优人员配置

    参数：
    - predicted_workload: 预测工作当量
    - safety_margin: 安全系数（默认1.2）
    - min_shift_leader: 最小值班长数（默认1）
    - min_primary: 最小正值数（默认1）
    - min_secondary: 最小副值数（默认1）

    返回：最优人员配置方案JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="calculate_optimal_staffing")

    try:
        model = StaffEfficiencyModel()
        result = model.calculate_optimal_staffing(
            predicted_workload=predicted_workload,
            safety_margin=safety_margin,
            min_shift_leader=min_shift_leader,
            min_primary=min_primary,
            min_secondary=min_secondary
        )

        return json.dumps({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "optimal_staffing": result
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"计算最优人员配置失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "计算最优人员配置失败"
        }, ensure_ascii=False)
