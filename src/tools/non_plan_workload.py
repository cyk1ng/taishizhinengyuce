"""
非计划工作量统计模块 - 严格按照业务需求实现

功能：
1. 故障日志统计：统计前三天未交班的故障单数
2. 异常缺陷统计：统计未交班的所有缺陷单数
3. 重过载统计：统计未解决的所有重过载数

业务规则：
1. 故障日志：配网OMS系统-调度工作台-故障日志-当值记录-前三天未交班的故障单数
2. 异常缺陷：配网OMS系统-调度工作台-异常缺陷-当值记录-未交班的所有缺陷单数
3. 重过载：配网OMS系统-调度工作台-重过载-当值记录-未解决的所有重过载数

以上三项相加为实时分析的非计划工作量
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 工作量权重配置
# ============================================================

WORKLOAD_WEIGHTS = {
    "non_plan_task": {
        "items": {
            "B1_success": {
                "name": "跳闸重合成功",
                "weight": 0.1
            },
            "B1_fail_known": {
                "name": "跳闸重合不成功(确定故障)",
                "weight": 0.3
            },
            "B1_fail_unknown": {
                "name": "跳闸重合不成功(不确定故障)",
                "weight": 0.5
            },
            "B1_bus_ground": {
                "name": "母线接地",
                "weight": 0.5
            },
            "B2": {
                "name": "异常缺陷",
                "weight": 0.5
            },
            "B3": {
                "name": "重过载",
                "weight": 0.1
            }
        }
    }
}


# ============================================================
# 数据库操作类
# ============================================================

class NonPlanWorkloadDatabase:
    """非计划工作量数据库操作类"""
    
    @staticmethod
    def get_session():
        """获取数据库会话"""
        try:
            from storage.database.db import get_session, is_database_connected
            if is_database_connected():
                return get_session()
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
        return None
    
    @staticmethod
    def collect_fault_logs(target_date: str, days_back: int = 3) -> List[Dict]:
        """
        采集故障日志
        
        业务规则：
        配网OMS系统-调度工作台-故障日志-当值记录-前三天未交班的故障单数
        
        参数：
            target_date: 目标日期 (YYYY-MM-DD)
            days_back: 向前追溯天数，默认3天
        
        返回：故障日志记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 计算向前追溯的日期
            start_date = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=days_back)
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            # 查询前三天未交班的故障单
            sql = text("""
                SELECT 
                    RECORD_ID as record_id,
                    FAULT_ID as fault_id,
                    FAULT_TYPE as fault_type,
                    RECLOSER_RESULT as reclose_result,
                    EQUIPMENT_NAME as equipment_name,
                    VOLTAGE_LEVEL as voltage_level,
                    FAULT_TIME as fault_time,
                    EXPECTED_RESTORE_TIME as expected_restore_time,
                    ACTUAL_RESTORE_TIME as actual_restore_time,
                    IS_HANDED_OVER as is_handed_over,
                    STATUS as status,
                    DUTY_OFFICER as duty_officer,
                    CASE 
                        WHEN RECLOSER_RESULT = 'success' THEN 'B1_success'
                        WHEN RECLOSER_RESULT = 'fail' AND FAULT_TYPE = 'known' THEN 'B1_fail_known'
                        WHEN RECLOSER_RESULT = 'fail' AND FAULT_TYPE = 'unknown' THEN 'B1_fail_unknown'
                        WHEN FAULT_TYPE = 'bus_ground' THEN 'B1_bus_ground'
                        ELSE 'B1_unknown'
                    END as task_category,
                    CASE 
                        WHEN RECLOSER_RESULT = 'success' THEN '跳闸重合成功'
                        WHEN RECLOSER_RESULT = 'fail' AND FAULT_TYPE = 'known' THEN '跳闸重合不成功(确定故障)'
                        WHEN RECLOSER_RESULT = 'fail' AND FAULT_TYPE = 'unknown' THEN '跳闸重合不成功(不确定故障)'
                        WHEN FAULT_TYPE = 'bus_ground' THEN '母线接地'
                        ELSE '未知故障类型'
                    END as task_name,
                    1 as count
                FROM fault_logs
                WHERE FAULT_TIME >= :start_date
                  AND FAULT_TIME < :target_date_next
                  AND (IS_HANDED_OVER = 0 OR IS_HANDED_OVER IS NULL)
                ORDER BY FAULT_TIME DESC
            """)
            
            # 计算目标日期的下一天
            target_date_next = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            
            result = session.execute(sql, {
                "start_date": start_date_str,
                "target_date_next": target_date_next
            })
            
            for row in result:
                data = dict(row._mapping)
                # 添加权重
                category = data.get("task_category", "")
                if category in WORKLOAD_WEIGHTS["non_plan_task"]["items"]:
                    data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"][category]["weight"]
                else:
                    data["weight"] = 0.0
                records.append(data)
            
            logger.info(f"采集故障日志 {len(records)} 条（前{days_back}天未交班）")
            
        except Exception as e:
            logger.error(f"采集故障日志失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_defect_records() -> List[Dict]:
        """
        采集异常缺陷
        
        业务规则：
        配网OMS系统-调度工作台-异常缺陷-当值记录-未交班的所有缺陷单数
        
        注意：统计所有未交班的缺陷单，不限制日期范围
        
        返回：异常缺陷记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询所有未交班的缺陷单
            sql = text("""
                SELECT 
                    RECORD_ID as record_id,
                    DEFECT_ID as defect_id,
                    DEFECT_TYPE as defect_type,
                    DEFECT_LEVEL as defect_level,
                    EQUIPMENT_NAME as equipment_name,
                    DEFECT_TIME as defect_time,
                    EXPECTED_FIX_TIME as expected_fix_time,
                    ACTUAL_FIX_TIME as actual_fix_time,
                    IS_HANDED_OVER as is_handed_over,
                    STATUS as status,
                    REPORTER as reporter,
                    'B2' as task_category,
                    '异常缺陷' as task_name,
                    1 as count
                FROM defect_records
                WHERE IS_HANDED_OVER = 0 OR IS_HANDED_OVER IS NULL
                ORDER BY DEFECT_TIME DESC
            """)
            
            result = session.execute(sql)
            for row in result:
                data = dict(row._mapping)
                # 添加权重
                data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B2"]["weight"]
                records.append(data)
            
            logger.info(f"采集异常缺陷 {len(records)} 条（未交班）")
            
        except Exception as e:
            logger.error(f"采集异常缺陷失败: {e}")
        finally:
            if session:
                session.close()
        
        return records
    
    @staticmethod
    def collect_overload_records() -> List[Dict]:
        """
        采集重过载记录
        
        业务规则：
        配网OMS系统-调度工作台-重过载-当值记录-未解决的所有重过载数
        
        注意：统计所有未解决的重过载记录，不限制日期范围
        
        返回：重过载记录列表
        """
        session = NonPlanWorkloadDatabase.get_session()
        if not session:
            logger.warning("数据库未连接，返回空列表")
            return []
        
        records = []
        
        try:
            from sqlalchemy import text
            
            # 查询所有未解决的重过载记录
            sql = text("""
                SELECT 
                    RECORD_ID as record_id,
                    OVERLOAD_ID as overload_id,
                    OVERLOAD_TYPE as overload_type,
                    EQUIPMENT_NAME as equipment_name,
                    LOAD_RATE as load_rate,
                    RATED_CAPACITY as rated_capacity,
                    ACTUAL_LOAD as actual_load,
                    RECORD_TIME as record_time,
                    EXPECTED_RESOLVE_TIME as expected_resolve_time,
                    ACTUAL_RESOLVE_TIME as actual_resolve_time,
                    IS_RESOLVED as is_resolved,
                    STATUS as status,
                    MONITOR_PERSON as monitor_person,
                    'B3' as task_category,
                    '重过载' as task_name,
                    1 as count
                FROM overload_records
                WHERE IS_RESOLVED = 0 OR IS_RESOLVED IS NULL
                ORDER BY RECORD_TIME DESC
            """)
            
            result = session.execute(sql)
            for row in result:
                data = dict(row._mapping)
                # 添加权重
                data["weight"] = WORKLOAD_WEIGHTS["non_plan_task"]["items"]["B3"]["weight"]
                records.append(data)
            
            logger.info(f"采集重过载记录 {len(records)} 条（未解决）")
            
        except Exception as e:
            logger.error(f"采集重过载记录失败: {e}")
        finally:
            if session:
                session.close()
        
        return records


# ============================================================
# 工具函数
# ============================================================

@tool
def calculate_non_plan_workload(
    target_date: str = "",
    days_back: int = 3,
    runtime: ToolRuntime = None
) -> str:
    """
    计算非计划工作量
    
    功能：
    1. 采集故障日志：前三天未交班的故障单数
    2. 采集异常缺陷：未交班的所有缺陷单数
    3. 采集重过载：未解决的所有重过载数
    4. 以上三项相加为实时分析的非计划工作量
    
    参数：
        - target_date: 目标日期 (YYYY-MM-DD)，默认今天
        - days_back: 故障日志向前追溯天数，默认3天
    
    返回：非计划工作量统计结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="calculate_non_plan_workload")
    
    try:
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # 1. 采集各类非计划任务
        fault_logs = NonPlanWorkloadDatabase.collect_fault_logs(target_date, days_back=days_back)
        defect_records = NonPlanWorkloadDatabase.collect_defect_records()
        overload_records = NonPlanWorkloadDatabase.collect_overload_records()
        
        # 2. 计算工作量
        result = {
            "target_date": target_date,
            "days_back": days_back,
            "fault_logs": [],
            "defect_records": [],
            "overload_records": [],
            "summary": {
                "total_count": 0,
                "total_weight": 0.0,
                "by_category": {}
            }
        }
        
        # 2.1 处理故障日志
        fault_count = 0
        fault_weight = 0.0
        for record in fault_logs:
            fault_count += 1
            fault_weight += record.get("weight", 0.0)
            result["fault_logs"].append({
                "record_id": record["record_id"],
                "fault_id": record["fault_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"],
                "fault_time": str(record["fault_time"]),
                "weight": record["weight"]
            })
            # 记录到高发事件检测器
            from tools.weather_manager import HighIncidentDetector
            HighIncidentDetector.record_incident("fault", {
                "fault_id": record["fault_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"]
            })
        
        # 2.2 处理异常缺陷
        defect_count = 0
        defect_weight = 0.0
        for record in defect_records:
            defect_count += 1
            defect_weight += record.get("weight", 0.0)
            result["defect_records"].append({
                "record_id": record["record_id"],
                "defect_id": record["defect_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"],
                "defect_time": str(record["defect_time"]),
                "weight": record["weight"]
            })
        
        # 2.3 处理重过载
        overload_count = 0
        overload_weight = 0.0
        for record in overload_records:
            overload_count += 1
            overload_weight += record.get("weight", 0.0)
            result["overload_records"].append({
                "record_id": record["record_id"],
                "overload_id": record["overload_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"],
                "load_rate": record["load_rate"],
                "record_time": str(record["record_time"]),
                "weight": record["weight"]
            })
            # 记录到高发事件检测器
            from tools.weather_manager import HighIncidentDetector
            HighIncidentDetector.record_incident("overload", {
                "overload_id": record["overload_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"],
                "load_rate": record["load_rate"]
            })
        
        # 2.4 汇总统计
        total_count = fault_count + defect_count + overload_count
        total_weight = fault_weight + defect_weight + overload_weight
        
        result["summary"]["total_count"] = total_count
        result["summary"]["total_weight"] = round(total_weight, 2)
        result["summary"]["by_category"] = {
            "fault_logs": {
                "count": fault_count,
                "weight": round(fault_weight, 2),
                "description": f"前{days_back}天未交班故障单"
            },
            "defect_records": {
                "count": defect_count,
                "weight": round(defect_weight, 2),
                "description": "未交班缺陷单"
            },
            "overload_records": {
                "count": overload_count,
                "weight": round(overload_weight, 2),
                "description": "未解决重过载"
            }
        }
        
        result["summary"]["record_counts"] = {
            "fault_logs": len(fault_logs),
            "defect_records": len(defect_records),
            "overload_records": len(overload_records)
        }
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"计算非计划工作量失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "计算非计划工作量失败"
        }, ensure_ascii=False)


@tool
def predict_non_plan_workload_with_weather(
    target_date: str,
    location: str = "云南昆明",
    use_typical_weather: bool = False,
    runtime: ToolRuntime = None
) -> str:
    """
    预测非计划工作量（带天气信息）
    
    功能：
    1. 获取目标日期的天气信息（或使用季节典型天气）
    2. 统计当前非计划工作量
    3. 检测最近高发事件
    4. 基于天气、历史模式和高发事件预测未来工作量
    
    参数：
        - target_date: 目标日期 (YYYY-MM-DD)
        - location: 地点，默认"云南昆明"
        - use_typical_weather: 是否使用季节典型天气，默认False（使用实际天气）
    
    返回：非计划工作量预测结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="predict_non_plan_workload_with_weather")
    
    try:
        from tools.weather_manager import (
            SeasonCharacteristics,
            HistoricalWeatherData,
            WeatherClassifier,
            HighIncidentDetector
        )
        
        # 1. 获取天气信息
        if use_typical_weather:
            # 使用季节典型天气（预测时自动填写）
            month = datetime.strptime(target_date, "%Y-%m-%d").month
            typical_weather = SeasonCharacteristics.get_typical_weather_for_prediction(month)
            
            weather_data = {
                "date": target_date,
                "month": month,
                "weather_info": {
                    "temperature": typical_weather["temperature"],
                    "precipitation_level": typical_weather["precipitation_level"],
                    "wind_level": typical_weather["wind_level"],
                    "extreme_weather": typical_weather["extreme_weather"]
                },
                "season_name": typical_weather["season_name"],
                "workload_impact": typical_weather["workload_impact"]
            }
            
            # 保存到历史
            HistoricalWeatherData.save_weather(target_date, weather_data["weather_info"])
        else:
            # 通过搜索获取实际天气
            import importlib; _sdk = importlib.import_module('coze_coding_dev_sdk'); SearchClient = _sdk.SearchClient
            query = f"{target_date} {location} 天气预报 温度 降雨 风力"
            client = SearchClient(ctx=ctx)
            response = client.web_search(query=query, count=5, need_summary=True)
            
            # 提取天气信息
            all_text = response.summary if (hasattr(response, 'summary') and response.summary) else ""
            if hasattr(response, 'web_items') and response.web_items:
                snippets = [item.snippet for item in response.web_items if item.snippet]
                all_text += " " + " ".join(snippets)
            
            # 简单提取温度信息
            import re
            temp_matches = re.findall(r'(-?\d+).*?℃', all_text)
            if temp_matches:
                temps = [int(t) for t in temp_matches]
                temp_min = min(temps)
                temp_max = max(temps)
                temp_class = WeatherClassifier.classify_temperature(temp_min, temp_max)
                temp_info = {"temp_range": temp_class["temp_range"]}
            else:
                month = datetime.strptime(target_date, "%Y-%m-%d").month
                typical_weather = SeasonCharacteristics.get_typical_weather_for_prediction(month)
                temp_info = {"temp_range": typical_weather["temperature"]}
            
            # 分类降水量和风力（默认值）
            precip_info = {"level": "未知"}
            wind_info = {"level": "未知"}
            
            # 分类极端天气
            extreme_class = WeatherClassifier.classify_extreme_weather(all_text)
            extreme_info = {
                "has_extreme": extreme_class["has_extreme"],
                "types": extreme_class["types"]
            }
            
            weather_data = {
                "date": target_date,
                "location": location,
                "weather_info": {
                    "temperature": temp_info["temp_range"],
                    "precipitation_level": precip_info["level"],
                    "wind_level": wind_info["level"],
                    "extreme_weather": extreme_info["types"]
                }
            }
            
            # 保存到历史
            HistoricalWeatherData.save_weather(target_date, weather_data["weather_info"])
        
        # 2. 获取当前非计划工作量（作为基线）
        fault_logs = NonPlanWorkloadDatabase.collect_fault_logs(target_date, days_back=3)
        defect_records = NonPlanWorkloadDatabase.collect_defect_records()
        overload_records = NonPlanWorkloadDatabase.collect_overload_records()
        
        base_count = len(fault_logs) + len(defect_records) + len(overload_records)
        base_weight = 0.0
        
        for record in fault_logs:
            base_weight += record.get("weight", 0.0)
            # 记录到高发事件检测器
            HighIncidentDetector.record_incident("fault", {
                "fault_id": record["fault_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"]
            })
        
        for record in defect_records:
            base_weight += record.get("weight", 0.0)
        
        for record in overload_records:
            base_weight += record.get("weight", 0.0)
            # 记录到高发事件检测器
            HighIncidentDetector.record_incident("overload", {
                "overload_id": record["overload_id"],
                "task_category": record["task_category"],
                "task_name": record["task_name"],
                "equipment_name": record["equipment_name"],
                "load_rate": record["load_rate"]
            })
        
        base_weight = round(base_weight, 2)
        
        current_data = {
            "summary": {
                "total_count": base_count,
                "total_weight": base_weight
            }
        }
        
        # 3. 检测高发事件
        prediction_impact = HighIncidentDetector.get_prediction_impact()
        
        # 4. 获取季节特点
        month = datetime.strptime(target_date, "%Y-%m-%d").month
        season = SeasonCharacteristics.get_season_by_month(month)
        
        # 5. 计算天气影响因子
        weather_impact_factor = 1.0  # 默认无影响
        if weather_data:
            weather_info = weather_data.get("weather_info", {})
            extreme = weather_info.get("extreme_weather", [])
            
            # 极端天气影响
            if extreme:
                weather_impact_factor *= 2.0  # 极端天气翻倍
            
            # 降水影响
            precip_level = weather_info.get("precipitation_level", "小")
            if precip_level == "大":
                weather_impact_factor *= 1.5
            elif precip_level == "中":
                weather_impact_factor *= 1.2
            
            # 风力影响
            wind_level = weather_info.get("wind_level", "小")
            if wind_level == "大":
                weather_impact_factor *= 1.3
            elif wind_level == "中":
                weather_impact_factor *= 1.1
            
            # 季节影响
            if season:
                season_impact = season.get("workload_impact", "low")
                if season_impact == "high":
                    weather_impact_factor *= 1.4
                elif season_impact == "medium":
                    weather_impact_factor *= 1.2
        
        # 6. 高发事件影响因子
        incident_impact_factor = 1.0
        if prediction_impact.get("overall_impact") == "high":
            incident_impact_factor = 1.5
        elif prediction_impact.get("overall_impact") == "medium":
            incident_impact_factor = 1.2
        
        # 7. 综合预测
        predicted_count = int(base_count * weather_impact_factor * incident_impact_factor)
        predicted_weight = round(base_weight * weather_impact_factor * incident_impact_factor, 2)
        
        # 8. 生成预测结果
        result = {
            "target_date": target_date,
            "location": location,
            "prediction": {
                "base_count": base_count,
                "base_weight": base_weight,
                "predicted_count": predicted_count,
                "predicted_weight": predicted_weight,
                "weather_impact_factor": round(weather_impact_factor, 2),
                "incident_impact_factor": round(incident_impact_factor, 2),
                "total_impact_factor": round(weather_impact_factor * incident_impact_factor, 2)
            },
            "weather": weather_data,
            "current_workload": current_data,
            "incidents": prediction_impact,
            "season": season,
            "recommendations": []
        }
        
        # 生成建议
        if weather_impact_factor > 1.3:
            result["recommendations"].append(f"天气影响较大（因子{weather_impact_factor}），建议增加值班人员")
        
        if incident_impact_factor > 1.2:
            result["recommendations"].append(f"近期高发事件影响（因子{incident_impact_factor}），需重点关注")
        
        if season and season.get("workload_impact") == "high":
            result["recommendations"].append(f"属于{season['name']}，{season['description']}，需加强设备巡检")
        
        # 保存天气-工作量关联（用于训练）
        if weather_data and current_data:
            HistoricalWeatherData.save_weather_workload_association(
                target_date,
                weather_data,
                current_data.get("summary", {})
            )
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"预测非计划工作量失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "预测非计划工作量失败"
        }, ensure_ascii=False)
