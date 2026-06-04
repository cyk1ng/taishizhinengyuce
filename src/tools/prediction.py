"""
业务量预测模块 - 配网调度业务量智能预测系统

功能：
1. 基于历史数据的趋势分析
2. 多因素影响的业务量预测
3. 异常检测与预警
4. 预测结果可视化

技术：
- 使用LLM进行智能分析和预测
- 结合时序特征和外部因素
- 提供置信区间和风险评估
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool, ToolRuntime
from langchain_core.messages import HumanMessage, SystemMessage
from coze_coding_utils.runtime_ctx.context import new_context


# 配置文件路径
PREDICTION_CONFIG = "assets/prediction_config.json"


class PredictionConfig:
    """预测配置管理"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"),
            PREDICTION_CONFIG
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
            "prediction": {
                "model": "doubao-seed-1-8-251228",
                "temperature": 0.3,
                "max_tokens": 4000,
                "prediction_horizon_days": 7,
                "confidence_level": 0.95
            },
            "factors": {
                "weather_impact": {
                    "weight": 0.3,
                    "high_temperature_threshold": 35,
                    "heavy_rain_conditions": ["大雨", "暴雨", "雷阵雨"]
                },
                "holiday_impact": {
                    "weight": 0.2,
                    "holiday_reduction_factor": 0.7,
                    "weekend_reduction_factor": 0.8
                },
                "seasonal_impact": {
                    "weight": 0.25,
                    "peak_months": [6, 7, 8, 12],
                    "peak_factor": 1.2
                },
                "equipment_impact": {
                    "weight": 0.25,
                    "fault_threshold": 0.1
                }
            }
        }
    
    @property
    def model_config(self) -> Dict:
        return self._config.get("prediction", {})
    
    @property
    def factors_config(self) -> Dict:
        return self._config.get("factors", {})


class BusinessVolumePredictor:
    """
    业务量预测引擎
    
    移植说明：
    - 可替换为专业时序预测模型（Prophet、ARIMA、LSTM等）
    - 保持接口：predict(historical_data, external_factors) -> Dict
    """
    
    def __init__(self, config: Optional[PredictionConfig] = None):
        self.config = config or PredictionConfig()
        self.llm_client = None
    
    def _init_llm_client(self, ctx):
        """初始化LLM客户端"""
        if self.llm_client is None:
            import importlib
            _sdk = importlib.import_module('coze_coding_dev_sdk')
            LLMClient = _sdk.LLMClient
            self.llm_client = LLMClient(ctx=ctx)
        return self.llm_client
    
    def _build_prediction_prompt(
        self,
        historical_data: List[Dict],
        weather_forecast: List[Dict],
        holidays: List[Dict],
        equipment_summary: Dict,
        prediction_days: int
    ) -> str:
        """构建预测提示词"""
        
        prompt = f"""
你是一位专业的配网调度业务量预测专家。请基于以下多源数据，预测未来{prediction_days}天的配网调度业务量。

## 历史调度数据（最近30天）
{json.dumps(historical_data[-7:], ensure_ascii=False, indent=2)}

## 天气预报（未来7天）
{json.dumps(weather_forecast, ensure_ascii=False, indent=2)}

## 节假日信息
{json.dumps(holidays, ensure_ascii=False, indent=2)}

## 设备状态摘要
{json.dumps(equipment_summary, ensure_ascii=False, indent=2)}

## 预测要求
1. 预测未来{prediction_days}天的业务量（调度次数、故障数）
2. 分析影响因素（天气、节假日、季节、设备状态）
3. 提供预测置信度和风险评估
4. 识别可能的业务量高峰和低谷
5. 给出异常预警建议

## 输出格式（JSON）
请严格按照以下JSON格式输出：

```json
{{
  "prediction_summary": {{
    "total_predicted_dispatches": 数字,
    "total_predicted_faults": 数字,
    "avg_daily_dispatches": 数字,
    "peak_day": "YYYY-MM-DD",
    "peak_dispatches": 数字,
    "confidence_level": 0.0-1.0
  }},
  "daily_predictions": [
    {{
      "date": "YYYY-MM-DD",
      "predicted_dispatches": 数字,
      "predicted_faults": 数字,
      "confidence": 0.0-1.0,
      "risk_level": "低/中/高",
      "key_factors": ["因素1", "因素2"]
    }}
  ],
  "factor_analysis": {{
    "weather_impact": "分析说明",
    "holiday_impact": "分析说明",
    "seasonal_impact": "分析说明",
    "equipment_impact": "分析说明"
  }},
  "risk_warnings": [
    {{
      "date": "YYYY-MM-DD",
      "type": "预警类型",
      "description": "详细说明",
      "suggested_actions": ["建议措施"]
    }}
  ],
  "recommendations": ["整体建议"]
}}
```

请开始预测分析：
"""
        return prompt
    
    def predict(
        self,
        historical_data: List[Dict],
        weather_forecast: List[Dict],
        holidays: List[Dict],
        equipment_summary: Dict,
        prediction_days: int = 7,
        ctx=None
    ) -> Dict:
        """
        执行业务量预测
        
        参数：
        - historical_data: 历史调度数据
        - weather_forecast: 天气预报
        - holidays: 节假日信息
        - equipment_summary: 设备状态摘要
        - prediction_days: 预测天数
        - ctx: 运行时上下文
        
        返回：预测结果字典
        """
        try:
            # 初始化LLM
            client = self._init_llm_client(ctx)
            
            # 构建提示词
            prompt = self._build_prediction_prompt(
                historical_data,
                weather_forecast,
                holidays,
                equipment_summary,
                prediction_days
            )
            
            # 调用LLM
            messages = [
                SystemMessage(content="你是一位专业的配网调度业务量预测专家，擅长基于多源数据进行精准预测和分析。"),
                HumanMessage(content=prompt)
            ]
            
            response = client.invoke(
                messages=messages,
                model=self.config.model_config.get("model", "doubao-seed-1-8-251228"),
                temperature=self.config.model_config.get("temperature", 0.3),
                max_completion_tokens=self.config.model_config.get("max_tokens", 4000)
            )
            
            # 解析响应
            content = response.content
            if isinstance(content, list):
                # 多模态响应，提取文本
                content = " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            
            # 提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_str = content[json_start + 7:json_end].strip()
                prediction_result = json.loads(json_str)
            else:
                # 尝试直接解析整个响应
                prediction_result = json.loads(content)
            
            # 添加元数据
            prediction_result["metadata"] = {
                "model": self.config.model_config.get("model"),
                "prediction_time": datetime.now().isoformat(),
                "prediction_horizon": f"{prediction_days} days",
                "data_sources": ["historical", "weather", "holiday", "equipment"]
            }
            
            return prediction_result
            
        except Exception as e:
            return {
                "error": str(e),
                "message": "预测过程发生错误",
                "timestamp": datetime.now().isoformat()
            }


# 工具函数
@tool
def predict_dispatch_volume(
    start_date: str,
    end_date: str,
    prediction_days: int = 7,
    runtime: ToolRuntime = None
) -> str:
    """
    预测配网调度业务量
    
    参数：
    - start_date: 历史数据开始日期 (YYYY-MM-DD)
    - end_date: 历史数据结束日期 (YYYY-MM-DD)
    - prediction_days: 预测天数 (默认7天)
    
    返回：业务量预测结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="predict_dispatch_volume")
    
    try:
        # 1. 获取融合数据
        from tools.data_fusion import fuse_multi_source_data
        
        fused_data_json = fuse_multi_source_data.invoke({
            "start_date": start_date,
            "end_date": end_date,
            "runtime": runtime
        })
        fused_data = json.loads(fused_data_json)
        
        if not fused_data.get("success"):
            raise ValueError("多源数据融合失败")
        
        # 2. 执行预测
        predictor = BusinessVolumePredictor()
        prediction_result = predictor.predict(
            historical_data=fused_data["fused_data"]["historical_records"],
            weather_forecast=fused_data["fused_data"]["weather_forecast"],
            holidays=fused_data["fused_data"]["holidays"],
            equipment_summary=fused_data["fused_data"]["equipment_summary"],
            prediction_days=prediction_days,
            ctx=ctx
        )
        
        # 3. 整合结果
        result = {
            "success": True,
            "prediction_timestamp": datetime.now().isoformat(),
            "prediction_horizon": f"{prediction_days} days",
            "data_sources": fused_data["data_sources"],
            "prediction": prediction_result,
            "model_info": {
                "model_name": predictor.config.model_config.get("model"),
                "temperature": predictor.config.model_config.get("temperature")
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "业务量预测失败"
        }, ensure_ascii=False)


@tool
def analyze_prediction_trend(
    prediction_result: str,
    runtime: ToolRuntime = None
) -> str:
    """
    分析预测趋势并生成洞察
    
    参数：
    - prediction_result: 预测结果JSON字符串
    
    返回：趋势分析报告JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="analyze_prediction_trend")
    
    try:
        prediction_data = json.loads(prediction_result)
        
        if not prediction_data.get("success"):
            raise ValueError("无效的预测结果")
        
        prediction = prediction_data.get("prediction", {})
        daily_predictions = prediction.get("daily_predictions", [])
        
        # 趋势分析
        dispatches = [d["predicted_dispatches"] for d in daily_predictions]
        
        trend_analysis = {
            "success": True,
            "analysis_timestamp": datetime.now().isoformat(),
            "trend_summary": {
                "trend_direction": "上升" if dispatches[-1] > dispatches[0] else "下降" if dispatches[-1] < dispatches[0] else "平稳",
                "average_daily_dispatches": sum(dispatches) / len(dispatches) if dispatches else 0,
                "max_dispatches": max(dispatches) if dispatches else 0,
                "min_dispatches": min(dispatches) if dispatches else 0,
                "volatility": max(dispatches) - min(dispatches) if dispatches else 0
            },
            "peak_analysis": {
                "peak_date": prediction.get("prediction_summary", {}).get("peak_day"),
                "peak_value": prediction.get("prediction_summary", {}).get("peak_dispatches"),
                "peak_factors": prediction.get("daily_predictions", [{}])[0].get("key_factors", [])
            },
            "risk_summary": {
                "total_warnings": len(prediction.get("risk_warnings", [])),
                "high_risk_days": sum(1 for d in daily_predictions if d.get("risk_level") == "高"),
                "medium_risk_days": sum(1 for d in daily_predictions if d.get("risk_level") == "中"),
                "low_risk_days": sum(1 for d in daily_predictions if d.get("risk_level") == "低")
            },
            "key_insights": prediction.get("recommendations", []),
            "factor_impact": prediction.get("factor_analysis", {})
        }
        
        return json.dumps(trend_analysis, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "趋势分析失败"
        }, ensure_ascii=False)
