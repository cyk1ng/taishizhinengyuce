"""
值班人员调整决策引擎 - 配网调度业务量智能预测系统

功能：
1. 基于业务量预测的人员需求计算
2. 技能匹配与资源配置优化
3. 班次调整建议生成
4. 成本效益分析

决策逻辑：
- 业务量-人员匹配模型
- 技能覆盖率优化
- 工作负荷平衡
- 合规性检查
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from coze_coding_utils.runtime_ctx.context import new_context
from coze_coding_utils.log.write_log import request_context


# 配置文件路径
DECISION_CONFIG = "assets/decision_config.json"


class DecisionConfig:
    """决策配置管理"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"),
            DECISION_CONFIG
        )
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """默认配置"""
        return {
            "staffing_rules": {
                "base_ratio": {
                    "dispatches_per_person": 8,
                    "faults_per_person": 2,
                    "description": "每人每日处理调度次数和故障数基准"
                },
                "shift_structure": {
                    "shifts_per_day": 3,
                    "shift_hours": [8, 8, 8],
                    "shift_names": ["早班", "中班", "晚班"],
                    "min_staff_per_shift": 2
                },
                "skills": [
                    {
                        "name": "调度操作",
                        "category": "core",
                        "required_count": 1,
                        "description": "基础调度操作能力"
                    },
                    {
                        "name": "故障处理",
                        "category": "specialized",
                        "required_count": 1,
                        "description": "故障诊断与处理能力"
                    },
                    {
                        "name": "应急响应",
                        "category": "advanced",
                        "required_count": 1,
                        "description": "紧急事件处理能力"
                    }
                ]
            },
            "constraints": {
                "max_work_hours_per_day": 12,
                "min_rest_hours_between_shifts": 8,
                "max_consecutive_work_days": 6,
                "compliance_check": True
            },
            "optimization": {
                "objective": "balance_workload",
                "factors": {
                    "workload_balance": 0.4,
                    "skill_coverage": 0.3,
                    "cost_efficiency": 0.3
                }
            }
        }
    
    @property
    def staffing_rules(self) -> Dict:
        return self._config.get("staffing_rules", {})
    
    @property
    def constraints(self) -> Dict:
        return self._config.get("constraints", {})
    
    @property
    def optimization(self) -> Dict:
        return self._config.get("optimization", {})


class StaffingDecisionEngine:
    """
    人员配置决策引擎
    
    移植说明：
    - 可集成专业优化算法（线性规划、遗传算法等）
    - 保持接口：generate_decision(prediction, current_staffing) -> Dict
    """
    
    def __init__(self, config: Optional[DecisionConfig] = None):
        self.config = config or DecisionConfig()
        self.llm_client = None
    
    def _init_llm_client(self, ctx):
        """初始化LLM客户端"""
        if self.llm_client is None:
            import importlib
            _sdk = importlib.import_module('coze_coding_dev_sdk')
            LLMClient = _sdk.LLMClient
            self.llm_client = LLMClient(ctx=ctx)
        return self.llm_client
    
    def _calculate_staffing_requirement(
        self,
        predicted_dispatches: int,
        predicted_faults: int
    ) -> Dict:
        """
        计算人员需求
        
        基于业务量预测计算所需人员数量
        """
        base_ratio = self.config.staffing_rules.get("base_ratio", {})
        dispatches_per_person = base_ratio.get("dispatches_per_person", 8)
        faults_per_person = base_ratio.get("faults_per_person", 2)
        
        # 计算基础需求
        dispatch_staff = predicted_dispatches / dispatches_per_person
        fault_staff = predicted_faults / faults_per_person
        
        # 综合需求（取最大值并加冗余）
        base_requirement = max(dispatch_staff, fault_staff)
        recommended_staff = int(base_requirement * 1.2)  # 20%冗余
        
        # 最小人员配置
        min_staff = self.config.staffing_rules.get("shift_structure", {}).get(
            "min_staff_per_shift", 2
        )
        
        return {
            "base_requirement": round(base_requirement, 1),
            "recommended_staff": max(recommended_staff, min_staff),
            "min_staff": min_staff,
            "dispatch_driven_staff": round(dispatch_staff, 1),
            "fault_driven_staff": round(fault_staff, 1),
            "calculation_basis": {
                "dispatches_per_person": dispatches_per_person,
                "faults_per_person": faults_per_person
            }
        }
    
    def _build_decision_prompt(
        self,
        prediction_summary: Dict,
        daily_predictions: List[Dict],
        risk_warnings: List[Dict],
        current_staffing: Optional[Dict] = None
    ) -> str:
        """构建决策提示词"""
        
        current_staffing_str = json.dumps(
            current_staffing or {"current_staff": 10, "shift_schedule": "标准三班制"},
            ensure_ascii=False,
            indent=2
        )
        
        prompt = f"""
你是一位专业的配网调度人员配置专家。请基于业务量预测结果，生成值班人员调整决策建议。

## 业务量预测摘要
{json.dumps(prediction_summary, ensure_ascii=False, indent=2)}

## 每日预测详情
{json.dumps(daily_predictions, ensure_ascii=False, indent=2)}

## 风险预警
{json.dumps(risk_warnings, ensure_ascii=False, indent=2)}

## 当前人员配置
{current_staffing_str}

## 决策规则
{json.dumps(self.config.staffing_rules, ensure_ascii=False, indent=2)}

## 约束条件
{json.dumps(self.config.constraints, ensure_ascii=False, indent=2)}

## 优化目标
{json.dumps(self.config.optimization, ensure_ascii=False, indent=2)}

## 决策要求
1. 为每一天计算最优人员配置
2. 确保技能覆盖完整
3. 平衡工作负荷
4. 遵守劳动法规约束
5. 优化成本效益
6. 提供应急预案

## 输出格式（JSON）
请严格按照以下JSON格式输出：

```json
{{
  "decision_summary": {{
    "total_additional_staff_needed": 数字,
    "peak_staffing_date": "YYYY-MM-DD",
    "peak_staffing_count": 数字,
    "average_daily_staff": 数字,
    "cost_impact_estimate": "成本影响估算说明"
  }},
  "daily_staffing_decisions": [
    {{
      "date": "YYYY-MM-DD",
      "predicted_dispatches": 数字,
      "predicted_faults": 数字,
      "recommended_staff": 数字,
      "current_staff": 数字,
      "staff_adjustment": 数字（正数为增加，负数为减少）,
      "shift_allocation": {{
        "早班": 数字,
        "中班": 数字,
        "晚班": 数字
      }},
      "skill_coverage": {{
        "调度操作": 数字,
        "故障处理": 数字,
        "应急响应": 数字
      }},
      "workload_per_person": 数字,
      "rationale": "调整理由说明"
    }}
  ],
  "risk_mitigation": [
    {{
      "risk_date": "YYYY-MM-DD",
      "risk_type": "风险类型",
      "mitigation_strategy": "缓解策略",
      "additional_resources_needed": 数字,
      "priority": "高/中/低"
    }}
  ],
  "implementation_recommendations": [
    "实施建议1",
    "实施建议2"
  ],
  "compliance_check": {{
    "labor_law_compliance": true/false,
    "safety_standards_met": true/false,
    "issues": ["问题列表"]
  }},
  "cost_benefit_analysis": {{
    "additional_cost_estimate": "成本估算",
    "efficiency_gain_estimate": "效率提升估算",
    "risk_reduction_value": "风险降低价值"
  }}
}}
```

请开始决策分析：
"""
        return prompt
    
    def generate_decision(
        self,
        prediction_result: Dict,
        current_staffing: Optional[Dict] = None,
        ctx=None
    ) -> Dict:
        """
        生成人员调整决策
        
        参数：
        - prediction_result: 业务量预测结果
        - current_staffing: 当前人员配置
        - ctx: 运行时上下文
        
        返回：决策建议字典
        """
        try:
            # 初始化LLM
            client = self._init_llm_client(ctx)
            
            # 提取预测数据
            prediction_summary = prediction_result.get("prediction_summary", {})
            daily_predictions = prediction_result.get("daily_predictions", [])
            risk_warnings = prediction_result.get("risk_warnings", [])
            
            # 构建提示词
            prompt = self._build_decision_prompt(
                prediction_summary,
                daily_predictions,
                risk_warnings,
                current_staffing
            )
            
            # 调用LLM
            messages = [
                SystemMessage(content="你是一位专业的配网调度人员配置专家，擅长基于业务预测进行精准的人员配置决策。"),
                HumanMessage(content=prompt)
            ]
            
            response = client.invoke(
                messages=messages,
                model="doubao-seed-1-8-251228",
                temperature=0.3,
                max_completion_tokens=4000
            )
            
            # 解析响应
            content = response.content
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 提取JSON
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_str = content[json_start + 7:json_end].strip()
                decision_result = json.loads(json_str)
            else:
                decision_result = json.loads(content)
            
            # 添加元数据
            decision_result["metadata"] = {
                "decision_time": datetime.now().isoformat(),
                "model": "doubao-seed-1-8-251228",
                "prediction_reference": prediction_result.get("metadata", {})
            }
            
            return decision_result
            
        except Exception as e:
            return {
                "error": str(e),
                "message": "决策生成过程发生错误",
                "timestamp": datetime.now().isoformat()
            }


# 工具函数
@tool
def generate_staffing_decision(
    prediction_summary: str,
    daily_predictions: str,
    current_staff_count: int = 10) -> str:
    """
    生成值班人员调整决策建议
    
    参数：
    - prediction_summary: 预测摘要JSON字符串（包含total_predicted_dispatches, total_predicted_faults等）
    - daily_predictions: 每日预测JSON数组字符串（包含date, predicted_dispatches, predicted_faults等）
    - current_staff_count: 当前值班人员总数
    
    返回：人员调整决策建议JSON字符串
    """
    ctx = request_context.get() or new_context(method="generate_staffing_decision")
    
    try:
        # 解析预测摘要
        summary = json.loads(prediction_summary) if isinstance(prediction_summary, str) else prediction_summary
        # 解析每日预测
        daily = json.loads(daily_predictions) if isinstance(daily_predictions, str) else daily_predictions
        
        # 构建预测结果对象
        prediction_result = {
            "prediction_summary": summary,
            "daily_predictions": daily,
            "risk_warnings": []
        }
        
        # 当前人员配置
        current_staffing = {
            "current_staff": current_staff_count,
            "shift_schedule": "标准三班制"
        }
        
        # 生成决策
        engine = StaffingDecisionEngine()
        decision_result = engine.generate_decision(
            prediction_result=prediction_result,
            current_staffing=current_staffing,
            ctx=ctx
        )
        
        # 整合结果
        result = {
            "success": True,
            "decision_timestamp": datetime.now().isoformat(),
            "input_parameters": {
                "current_staff_count": current_staff_count,
                "current_shift_schedule": "标准三班制"
            },
            "decision": decision_result,
            "action_required": decision_result.get("decision_summary", {}).get(
                "total_additional_staff_needed", 0
            ) > 0
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "人员调整决策生成失败"
        }, ensure_ascii=False)


@tool
def optimize_shift_schedule(
    staffing_decision: str,
    optimization_objective: str = "balance_workload") -> str:
    """
    优化班次安排
    
    参数：
    - staffing_decision: 人员配置决策JSON字符串
    - optimization_objective: 优化目标（balance_workload/cost_efficiency/skill_coverage）
    
    返回：优化后的班次安排JSON字符串
    """
    ctx = request_context.get() or new_context(method="optimize_shift_schedule")
    
    try:
        decision_data = json.loads(staffing_decision)
        
        if not decision_data.get("success"):
            raise ValueError("无效的人员配置决策")
        
        daily_decisions = decision_data.get("decision", {}).get(
            "daily_staffing_decisions", []
        )
        
        # 班次优化分析
        shift_optimization = {
            "success": True,
            "optimization_timestamp": datetime.now().isoformat(),
            "optimization_objective": optimization_objective,
            "optimized_schedule": []
        }
        
        for day_decision in daily_decisions:
            date = day_decision.get("date")
            recommended_staff = day_decision.get("recommended_staff", 0)
            
            # 优化班次分配
            if recommended_staff <= 4:
                shift_allocation = {
                    "早班": 2,
                    "中班": 1,
                    "晚班": 1
                }
            elif recommended_staff <= 6:
                shift_allocation = {
                    "早班": 2,
                    "中班": 2,
                    "晚班": 2
                }
            else:
                # 按比例分配
                base_per_shift = recommended_staff // 3
                remainder = recommended_staff % 3
                shift_allocation = {
                    "早班": base_per_shift + (1 if remainder > 0 else 0),
                    "中班": base_per_shift + (1 if remainder > 1 else 0),
                    "晚班": base_per_shift
                }
            
            shift_optimization["optimized_schedule"].append({
                "date": date,
                "shift_allocation": shift_allocation,
                "total_staff": recommended_staff,
                "optimization_notes": f"基于{optimization_objective}目标优化"
            })
        
        # 优化效果评估
        total_staff_before = sum(
            day.get("current_staff", 0) for day in daily_decisions
        )
        total_staff_after = sum(
            day.get("recommended_staff", 0) for day in daily_decisions
        )
        
        shift_optimization["optimization_metrics"] = {
            "total_staff_before": total_staff_before,
            "total_staff_after": total_staff_after,
            "staff_change": total_staff_after - total_staff_before,
            "optimization_efficiency": f"{abs(total_staff_after - total_staff_before) / max(total_staff_before, 1) * 100:.1f}%"
        }
        
        return json.dumps(shift_optimization, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "班次优化失败"
        }, ensure_ascii=False)


@tool
def generate_decision_report(
    prediction_result: str,
    staffing_decision: str,
    output_format: str = "markdown") -> str:
    """
    生成综合决策报告
    
    参数：
    - prediction_result: 业务量预测结果JSON字符串
    - staffing_decision: 人员配置决策JSON字符串
    - output_format: 输出格式（markdown/json）
    
    返回：决策报告
    """
    ctx = request_context.get() or new_context(method="generate_decision_report")
    
    try:
        prediction_data = json.loads(prediction_result)
        decision_data = json.loads(staffing_decision)
        
        if output_format == "json":
            report = {
                "success": True,
                "report_timestamp": datetime.now().isoformat(),
                "prediction_summary": prediction_data.get("prediction", {}).get(
                    "prediction_summary", {}
                ),
                "decision_summary": decision_data.get("decision", {}).get(
                    "decision_summary", {}
                ),
                "daily_predictions": prediction_data.get("prediction", {}).get(
                    "daily_predictions", []
                ),
                "daily_staffing": decision_data.get("decision", {}).get(
                    "daily_staffing_decisions", []
                ),
                "risk_warnings": prediction_data.get("prediction", {}).get(
                    "risk_warnings", []
                ),
                "recommendations": decision_data.get("decision", {}).get(
                    "implementation_recommendations", []
                )
            }
            return json.dumps(report, ensure_ascii=False, indent=2)
        
        else:  # markdown格式
            prediction = prediction_data.get("prediction", {})
            decision = decision_data.get("decision", {})
            
            report_md = f"""# 配网调度业务量智能预测与人员调整决策报告

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 一、业务量预测摘要

### 预测概况
- **预测总调度次数**: {prediction.get("prediction_summary", {}).get("total_predicted_dispatches", "N/A")}
- **预测总故障数**: {prediction.get("prediction_summary", {}).get("total_predicted_faults", "N/A")}
- **日均调度次数**: {prediction.get("prediction_summary", {}).get("avg_daily_dispatches", "N/A")}
- **峰值日期**: {prediction.get("prediction_summary", {}).get("peak_day", "N/A")}
- **峰值调度次数**: {prediction.get("prediction_summary", {}).get("peak_dispatches", "N/A")}
- **预测置信度**: {prediction.get("prediction_summary", {}).get("confidence_level", "N/A")}

### 影响因素分析
"""
            
            # 添加影响因素分析
            factor_analysis = prediction.get("factor_analysis", {})
            for factor, analysis in factor_analysis.items():
                report_md += f"\n#### {factor}\n{analysis}\n"
            
            # 添加每日预测详情
            report_md += "\n---\n## 二、每日预测详情\n\n"
            report_md += "| 日期 | 预测调度次数 | 预测故障数 | 置信度 | 风险等级 | 主要影响因素 |\n"
            report_md += "|------|--------------|------------|--------|----------|--------------|\n"
            
            for day in prediction.get("daily_predictions", []):
                factors = ", ".join(day.get("key_factors", []))
                report_md += f"| {day.get('date')} | {day.get('predicted_dispatches')} | {day.get('predicted_faults')} | {day.get('confidence')} | {day.get('risk_level')} | {factors} |\n"
            
            # 添加人员调整决策
            report_md += "\n---\n## 三、人员调整决策\n\n"
            
            decision_summary = decision.get("decision_summary", {})
            report_md += f"""### 决策概要
- **需增补人员总数**: {decision_summary.get("total_additional_staff_needed", "N/A")}
- **人员配置峰值日**: {decision_summary.get("peak_staffing_date", "N/A")}
- **峰值人员数**: {decision_summary.get("peak_staffing_count", "N/A")}
- **平均每日人员**: {decision_summary.get("average_daily_staff", "N/A")}
- **成本影响**: {decision_summary.get("cost_impact_estimate", "N/A")}

### 每日人员配置建议
"""
            
            report_md += "\n| 日期 | 预测调度 | 预测故障 | 建议人数 | 现有人数 | 调整人数 | 班次分配 | 人均负荷 | 理由 |\n"
            report_md += "|------|----------|----------|----------|----------|----------|----------|----------|------|\n"
            
            for day in decision.get("daily_staffing_decisions", []):
                shift = day.get("shift_allocation", {})
                shift_str = f"早{shift.get('早班', 0)}/中{shift.get('中班', 0)}/晚{shift.get('晚班', 0)}"
                
                report_md += f"| {day.get('date')} | {day.get('predicted_dispatches')} | {day.get('predicted_faults')} | {day.get('recommended_staff')} | {day.get('current_staff')} | {day.get('staff_adjustment', '+0')} | {shift_str} | {day.get('workload_per_person')} | {day.get('rationale', '')[:30]} |\n"
            
            # 添加风险预警
            report_md += "\n---\n## 四、风险预警与缓解措施\n\n"
            
            for risk in prediction.get("risk_warnings", []):
                report_md += f"""### {risk.get('type', '未知风险')} - {risk.get('date', '')}
**风险描述**: {risk.get('description', 'N/A')}

**建议措施**:
"""
                for action in risk.get("suggested_actions", []):
                    report_md += f"- {action}\n"
                report_md += "\n"
            
            # 添加实施建议
            report_md += "\n---\n## 五、实施建议\n\n"
            
            for idx, recommendation in enumerate(
                decision.get("implementation_recommendations", []), 1
            ):
                report_md += f"{idx}. {recommendation}\n"
            
            # 添加合规性检查
            compliance = decision.get("compliance_check", {})
            report_md += f"""

---

## 六、合规性检查

- **劳动法规合规**: {'✅ 通过' if compliance.get('labor_law_compliance') else '❌ 不通过'}
- **安全标准达标**: {'✅ 通过' if compliance.get('safety_standards_met') else '❌ 不通过'}

"""
            
            issues = compliance.get("issues", [])
            if issues:
                report_md += "**存在问题**:\n"
                for issue in issues:
                    report_md += f"- {issue}\n"
            
            # 添加成本效益分析
            cost_benefit = decision.get("cost_benefit_analysis", {})
            report_md += f"""

---

## 七、成本效益分析

- **额外成本估算**: {cost_benefit.get("additional_cost_estimate", "N/A")}
- **效率提升估算**: {cost_benefit.get("efficiency_gain_estimate", "N/A")}
- **风险降低价值**: {cost_benefit.get("risk_reduction_value", "N/A")}

---

**报告结束**
"""
            
            return report_md
        
    except Exception as e:
        return f"报告生成失败: {str(e)}"
