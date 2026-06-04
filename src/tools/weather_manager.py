"""
天气信息管理模块 - 支持非计划工作量预测的天气数据管理

功能：
1. 天气分类：温度、降水量、风力、极端天气
2. 历史天气数据管理
3. 极端天气与月份关联
4. 智能识别高发事件
5. 天气自动填写（预测时）

天气分类规则：
- 温度：摄氏度区段
- 降水量：大（25mm以上）中（10-24.9mm）小（9.9mm以下）
- 风力：大（11级及以上）中（7级-10级）小（6级及以下）
- 极端天气情况：寒潮、冰雹、雷雨等（会引起大面积线路跳闸）

季节特点：
- 雨季高发期：6月中旬到8月中旬
- 大风天气：春季、秋季
- 冬季用电高峰期：12月到次年2月
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from langchain.tools import tool, ToolRuntime
from coze_coding_utils.runtime_ctx.context import new_context

# 配置日志
logger = logging.getLogger(__name__)


# ============================================================
# 天气分类规则
# ============================================================

class WeatherClassifier:
    """天气分类器"""
    
    @staticmethod
    def classify_temperature(temp_min: float, temp_max: float) -> Dict:
        """
        温度分类
        
        参数：
            temp_min: 最低温度（摄氏度）
            temp_max: 最高温度（摄氏度）
        
        返回：温度分类信息
        """
        temp_range = f"{temp_min}℃~{temp_max}℃"
        
        # 根据温度范围给出描述
        avg_temp = (temp_min + temp_max) / 2
        if avg_temp < 0:
            level = "严寒"
            impact = "high"  # 高影响
        elif avg_temp < 10:
            level = "寒冷"
            impact = "medium"  # 中影响
        elif avg_temp < 20:
            level = "凉爽"
            impact = "low"  # 低影响
        elif avg_temp < 30:
            level = "温暖"
            impact = "low"  # 低影响
        else:
            level = "炎热"
            impact = "medium"  # 中影响
        
        return {
            "temp_min": temp_min,
            "temp_max": temp_max,
            "temp_range": temp_range,
            "avg_temp": round(avg_temp, 1),
            "level": level,
            "impact": impact
        }
    
    @staticmethod
    def classify_precipitation(precipitation: float) -> Dict:
        """
        降水量分类
        
        业务规则：
        - 大：25mm以上
        - 中：10-24.9mm
        - 小：9.9mm以下
        
        参数：
            precipitation: 降水量（mm）
        
        返回：降水量分类信息
        """
        if precipitation >= 25:
            level = "大"
            impact = "high"  # 高影响（易引发故障）
        elif precipitation >= 10:
            level = "中"
            impact = "medium"  # 中影响
        else:
            level = "小"
            impact = "low"  # 低影响
        
        return {
            "precipitation": precipitation,
            "level": level,
            "impact": impact,
            "description": f"降水量{level}（{precipitation}mm）"
        }
    
    @staticmethod
    def classify_wind(wind_speed: float) -> Dict:
        """
        风力分类
        
        业务规则：
        - 大：11级及以上（28.5m/s及以上）
        - 中：7级-10级（13.9-24.4m/s）
        - 小：6级及以下（13.8m/s及以下）
        
        参数：
            wind_speed: 风速（m/s）
        
        返回：风力分类信息
        """
        if wind_speed >= 28.5:
            level = "大"
            beaufort = "11级及以上"
            impact = "high"  # 高影响
        elif wind_speed >= 13.9:
            level = "中"
            beaufort = "7级-10级"
            impact = "medium"  # 中影响
        else:
            level = "小"
            beaufort = "6级及以下"
            impact = "low"  # 低影响
        
        return {
            "wind_speed": wind_speed,
            "level": level,
            "beaufort": beaufort,
            "impact": impact,
            "description": f"风力{level}（{beaufort}）"
        }
    
    @staticmethod
    def classify_extreme_weather(weather_text: str) -> Dict:
        """
        极端天气分类
        
        极端天气情况：寒潮、冰雹、雷雨等（会引起大面积线路跳闸）
        
        参数：
            weather_text: 天气描述文本
        
        返回：极端天气分类信息
        """
        extreme_weather_types = [
            "寒潮", "冰雹", "雷雨", "暴雨", "暴雪", 
            "台风", "大风", "龙卷风", "沙尘暴", 
            "冻雨", "霜冻", "高温", "干旱"
        ]
        
        detected_types = []
        for etype in extreme_weather_types:
            if etype in weather_text:
                detected_types.append(etype)
        
        if detected_types:
            return {
                "has_extreme": True,
                "types": detected_types,
                "description": ",".join(detected_types),
                "impact": "high"  # 高影响（会引起大面积线路跳闸）
            }
        else:
            return {
                "has_extreme": False,
                "types": [],
                "description": "无极端天气",
                "impact": "low"
            }


# ============================================================
# 季节特点管理
# ============================================================

class SeasonCharacteristics:
    """季节特点管理"""
    
    SEASON_PERIODS = {
        "rainy_season": {
            "name": "雨季高发期",
            "months": [6, 7, 8],
            "description": "6月中旬到8月中旬，易发雷雨、暴雨天气",
            "typical_weather": {
                "temperature": (17, 30),
                "precipitation_level": "大",
                "wind_level": "中",
                "extreme_weather": ["暴雨", "雷雨"]
            },
            "workload_impact": "high"  # 高影响
        },
        "windy_spring": {
            "name": "春季大风期",
            "months": [3, 4, 5],
            "description": "春季多风，易发大风天气",
            "typical_weather": {
                "temperature": (10, 25),
                "precipitation_level": "小",
                "wind_level": "大",
                "extreme_weather": ["大风", "沙尘暴"]
            },
            "workload_impact": "medium"  # 中影响
        },
        "windy_autumn": {
            "name": "秋季大风期",
            "months": [9, 10, 11],
            "description": "秋季多风，易发大风天气",
            "typical_weather": {
                "temperature": (5, 20),
                "precipitation_level": "小",
                "wind_level": "中",
                "extreme_weather": ["大风"]
            },
            "workload_impact": "medium"  # 中影响
        },
        "winter_peak": {
            "name": "冬季用电高峰期",
            "months": [12, 1, 2],
            "description": "12月到次年2月，用电负荷高，易发重过载",
            "typical_weather": {
                "temperature": (-5, 10),
                "precipitation_level": "小",
                "wind_level": "小",
                "extreme_weather": ["寒潮", "暴雪", "冻雨"]
            },
            "workload_impact": "high"  # 高影响
        }
    }
    
    @staticmethod
    def get_season_by_month(month: int) -> Optional[Dict]:
        """
        根据月份获取季节特点
        
        参数：
            month: 月份（1-12）
        
        返回：季节特点信息
        """
        for season_id, season_info in SeasonCharacteristics.SEASON_PERIODS.items():
            if month in season_info["months"]:
                return {
                    "season_id": season_id,
                    **season_info
                }
        return None
    
    @staticmethod
    def get_season_by_date(date_str: str) -> Optional[Dict]:
        """
        根据日期获取季节特点
        
        参数：
            date_str: 日期字符串 (YYYY-MM-DD)
        
        返回：季节特点信息
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return SeasonCharacteristics.get_season_by_month(date_obj.month)
        except Exception as e:
            logger.error(f"获取季节特点失败: {e}")
            return None
    
    @staticmethod
    def get_typical_weather_for_prediction(month: int) -> Dict:
        """
        获取某月的典型天气（用于预测时自动填写）
        
        参数：
            month: 月份（1-12）
        
        返回：典型天气信息
        """
        season = SeasonCharacteristics.get_season_by_month(month)
        if season:
            return {
                "temperature": f"{season['typical_weather']['temperature'][0]}℃~{season['typical_weather']['temperature'][1]}℃",
                "precipitation_level": season['typical_weather']['precipitation_level'],
                "wind_level": season['typical_weather']['wind_level'],
                "extreme_weather": season['typical_weather']['extreme_weather'],
                "season_name": season['name'],
                "workload_impact": season['workload_impact']
            }
        else:
            # 非特殊季节，返回默认值
            return {
                "temperature": "15℃~25℃",
                "precipitation_level": "小",
                "wind_level": "小",
                "extreme_weather": [],
                "season_name": "普通季节",
                "workload_impact": "low"
            }


# ============================================================
# 历史天气数据管理
# ============================================================

class HistoricalWeatherData:
    """历史天气数据管理（内存存储）"""

    # 存储历史天气数据 {date_str: weather_data}
    _weather_history: Dict[str, Dict] = {}

    # 存储天气与工作量的关联 {date_str: {weather: ..., workload: ...}}
    _weather_workload_history: List[Dict] = []

    # 存储按高峰期分类的历史数据
    _historical_workload_by_period: Dict[str, List[Dict]] = {
        "rainy_peak": [],      # 雨季高发期数据
        "wind_peak": [],       # 大风天气数据
        "winter_peak": [],     # 冬季用电高峰期数据
        "normal": []           # 普通时期数据（月底月初、非极端天气）
    }

    # 存储手动修改的天气数据
    _manual_weather_adjustments: Dict[str, Dict] = {}

    @classmethod
    def save_weather(cls, date_str: str, weather_data: Dict):
        """
        保存天气数据

        参数：
            date_str: 日期字符串 (YYYY-MM-DD)
            weather_data: 天气数据
        """
        cls._weather_history[date_str] = {
            "date": date_str,
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_manual": False,
            **weather_data
        }
        logger.info(f"保存天气数据: {date_str}")

    @classmethod
    def get_weather(cls, date_str: str) -> Optional[Dict]:
        """
        获取天气数据（优先返回手动修改的）

        参数：
            date_str: 日期字符串 (YYYY-MM-DD)

        返回：天气数据
        """
        # 优先返回手动修改的数据
        if date_str in cls._manual_weather_adjustments:
            return {
                "date": date_str,
                "is_manual": True,
                **cls._manual_weather_adjustments[date_str]
            }
        return cls._weather_history.get(date_str)

    @classmethod
    def manual_adjust_weather(cls, date_str: str, weather_data: Dict, reason: str = ""):
        """
        手动修改天气数据

        参数：
            date_str: 日期字符串 (YYYY-MM-DD)
            weather_data: 天气数据
            reason: 修改原因
        """
        cls._manual_weather_adjustments[date_str] = {
            "weather_data": weather_data,
            "adjustment_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason
        }
        logger.info(f"手动修改天气数据: {date_str}, 原因: {reason}")

    @classmethod
    def save_weather_workload_association(cls, date_str: str, weather_data: Dict, workload_data: Dict):
        """
        保存天气与工作量的关联数据（用于智能体训练）

        参数：
            date_str: 日期字符串 (YYYY-MM-DD)
            weather_data: 天气数据
            workload_data: 工作量数据
        """
        association = {
            "date": date_str,
            "weather": weather_data,
            "workload": workload_data,
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        cls._weather_workload_history.append(association)

        # 自动分类存储到对应的高峰期类别
        period_type = cls._classify_period(date_str, weather_data)
        if period_type:
            cls._historical_workload_by_period[period_type].append(association)

        logger.info(f"保存天气-工作量关联数据: {date_str}, 分类: {period_type}")

    @classmethod
    def _classify_period(cls, date_str: str, weather_data: Dict) -> str:
        """
        分类历史数据所属时期

        参数：
            date_str: 日期字符串 (YYYY-MM-DD)
            weather_data: 天气数据

        返回：时期类型（rainy_peak, wind_peak, winter_peak, normal）
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month = date_obj.month
            day = date_obj.day

            # 检查极端天气
            extreme_weather = weather_data.get("extreme_weather", [])
            if isinstance(extreme_weather, list) and len(extreme_weather) > 0:
                # 有极端天气
                if month in [6, 7, 8]:
                    return "rainy_peak"
                elif month in [3, 4, 5, 9, 10, 11]:
                    return "wind_peak"
                elif month in [12, 1, 2]:
                    return "winter_peak"

            # 按季节分类
            season = SeasonCharacteristics.get_season_by_month(month)
            if season:
                if season.get("season_id") == "rainy_season":
                    return "rainy_peak"
                elif season.get("season_id") in ["windy_spring", "windy_autumn"]:
                    return "wind_peak"
                elif season.get("season_id") == "winter_peak":
                    return "winter_peak"

            # 检查是否是月底月初（1-5号或25-31号）
            if day <= 5 or day >= 25:
                return "normal"

            # 检查是否有中等以上的降水
            precip_level = weather_data.get("precipitation_level", "小")
            if precip_level in ["中", "大"]:
                return "rainy_peak"

            # 检查是否有中等以上的风力
            wind_level = weather_data.get("wind_level", "小")
            if wind_level in ["中", "大"]:
                return "wind_peak"

            return "normal"

        except Exception as e:
            logger.error(f"分类时期失败: {e}")
            return "normal"

    @classmethod
    def collect_historical_workload_by_period(cls, period_type: str, limit: int = 100) -> List[Dict]:
        """
        按时期类型收集历史业务量数据

        参数：
            period_type: 时期类型（rainy_peak, wind_peak, winter_peak, normal）
            limit: 返回的最大数量

        返回：历史数据列表
        """
        if period_type not in cls._historical_workload_by_period:
            logger.warning(f"未知的时期类型: {period_type}")
            return []

        data = cls._historical_workload_by_period[period_type]
        # 返回最近的数据
        return data[-limit:] if len(data) > limit else data

    @classmethod
    def get_historical_patterns(cls, weather_condition: str, days_back: int = 30) -> List[Dict]:
        """
        获取历史天气模式（按天气条件筛选）

        参数：
            weather_condition: 天气条件（如"大雨"、"大风"等）
            days_back: 向前追溯天数

        返回：历史模式列表
        """
        patterns = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for association in cls._weather_workload_history:
            record_date = datetime.strptime(association["date"], "%Y-%m-%d")
            if record_date >= cutoff_date:
                weather = association["weather"]
                if weather_condition in str(weather):
                    patterns.append(association)

        logger.info(f"找到 {len(patterns)} 条历史天气模式（{weather_condition}）")
        return patterns

    @classmethod
    def get_manual_adjustments(cls, date_str: str = None) -> List[Dict]:
        """
        获取手动修改记录

        参数：
            date_str: 日期字符串（可选），如果不提供则返回所有记录

        返回：手动修改记录列表
        """
        if date_str:
            if date_str in cls._manual_weather_adjustments:
                return [{
                    "date": date_str,
                    **cls._manual_weather_adjustments[date_str]
                }]
            return []
        else:
            return [
                {"date": date, **data}
                for date, data in cls._manual_weather_adjustments.items()
            ]


# ============================================================
# 高发事件智能识别
# ============================================================

class HighIncidentDetector:
    """高发事件智能识别"""
    
    # 存储最近时间段的高发事件
    _recent_incidents: Dict[str, List[Dict]] = {
        "fault": [],  # 故障事件
        "overload": []  # 重过载事件
    }
    
    @classmethod
    def record_incident(cls, incident_type: str, incident_data: Dict):
        """
        记录事件
        
        参数：
            incident_type: 事件类型（"fault"或"overload"）
            incident_data: 事件数据
        """
        if incident_type in cls._recent_incidents:
            cls._recent_incidents[incident_type].append({
                "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **incident_data
            })
            logger.info(f"记录{incident_type}事件")
    
    @classmethod
    def detect_high_incidents(cls, incident_type: str, hours_back: int = 24) -> List[Dict]:
        """
        检测最近时间段的高发事件
        
        参数：
            incident_type: 事件类型（"fault"或"overload"）
            hours_back: 向前追溯小时数
        
        返回：高发事件列表
        """
        if incident_type not in cls._recent_incidents:
            return []
        
        incidents = cls._recent_incidents[incident_type]
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        # 筛选最近时间段的事件
        recent_incidents = []
        for incident in incidents:
            record_time = datetime.strptime(incident["recorded_at"], "%Y-%m-%d %H:%M:%S")
            if record_time >= cutoff_time:
                recent_incidents.append(incident)
        
        # 统计事件类型和数量
        type_counts = {}
        for incident in recent_incidents:
            task_type = incident.get("task_category", "unknown")
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        # 识别高发类型（数量超过阈值）
        high_incident_types = []
        threshold = 3  # 阈值：3次及以上算高发
        for task_type, count in type_counts.items():
            if count >= threshold:
                high_incident_types.append({
                    "type": task_type,
                    "count": count,
                    "is_high": True
                })
        
        result = {
            "incident_type": incident_type,
            "hours_back": hours_back,
            "total_count": len(recent_incidents),
            "type_counts": type_counts,
            "high_incident_types": high_incident_types,
            "has_high_incidents": len(high_incident_types) > 0
        }
        
        logger.info(f"检测{incident_type}高发事件: {result}")
        return result
    
    @classmethod
    def get_prediction_impact(cls) -> Dict:
        """
        获取对未来几天非计划工作量的预测影响
        
        返回：预测影响信息
        """
        fault_analysis = cls.detect_high_incidents("fault", hours_back=24)
        overload_analysis = cls.detect_high_incidents("overload", hours_back=24)
        
        prediction_impact = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fault_analysis": fault_analysis,
            "overload_analysis": overload_analysis,
            "overall_impact": "low",
            "recommendations": []
        }
        
        # 生成建议
        if fault_analysis["has_high_incidents"] or overload_analysis["has_high_incidents"]:
            prediction_impact["overall_impact"] = "high"
            prediction_impact["recommendations"].append("检测到最近高发事件，建议未来几天增加值班人员")
            prediction_impact["recommendations"].append("加强对相关设备和线路的巡检")
        
        if fault_analysis["has_high_incidents"]:
            for high_type in fault_analysis["high_incident_types"]:
                prediction_impact["recommendations"].append(f"近期{high_type['type']}频发（{high_type['count']}次），需重点关注")
        
        if overload_analysis["has_high_incidents"]:
            for high_type in overload_analysis["high_incident_types"]:
                prediction_impact["recommendations"].append(f"近期{high_type['type']}频发（{high_type['count']}次），需密切监控负荷")
        
        return prediction_impact


# ============================================================
# 天气获取工具（基于Web Search）
# ============================================================

@tool
def get_weather_by_search(
    date: str,
    location: str = "云南昆明",
    runtime: ToolRuntime = None
) -> str:
    """
    通过Web搜索获取天气信息
    
    参数：
        date: 日期字符串 (YYYY-MM-DD)
        location: 地点，默认"云南昆明"
    
    返回：天气信息JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_weather_by_search")
    
    try:
        # 构造搜索查询
        query = f"{date} {location} 天气预报 温度 降雨 风力"
        
        import importlib
        _sdk = importlib.import_module('coze_coding_dev_sdk')
        SearchClient = _sdk.SearchClient
        client = SearchClient(ctx=ctx)
        response = client.web_search(
            query=query,
            count=5,
            need_summary=True
        )
        
        # 提取天气信息
        weather_data = {
            "date": date,
            "location": location,
            "search_result": {
                "summary": response.summary if hasattr(response, 'summary') else "",
                "items": []
            }
        }
        
        if hasattr(response, 'web_items') and response.web_items:
            for item in response.web_items:
                weather_data["search_result"]["items"].append({
                    "title": item.title,
                    "snippet": item.snippet,
                    "url": item.url
                })
        
        # 尝试从搜索结果中提取温度、降水、风力信息
        # 这里简化处理，实际可以添加更复杂的解析逻辑
        all_text = weather_data["search_result"]["summary"] + " " + " ".join(
            [item["snippet"] for item in weather_data["search_result"]["items"]]
        )
        
        # 简单提取温度信息
        import re
        temp_matches = re.findall(r'(-?\d+).*?℃', all_text)
        if temp_matches:
            temps = [int(t) for t in temp_matches]
            temp_min = min(temps)
            temp_max = max(temps)
            
            # 分类温度
            temp_class = WeatherClassifier.classify_temperature(temp_min, temp_max)
            weather_data["temperature"] = temp_class
        else:
            # 无法提取温度，使用季节典型值
            month = datetime.strptime(date, "%Y-%m-%d").month
            typical_weather = SeasonCharacteristics.get_typical_weather_for_prediction(month)
            weather_data["temperature"] = {
                "temp_range": typical_weather["temperature"],
                "level": "默认值",
                "impact": "unknown"
            }
        
        # 分类降水量和风力（默认值）
        weather_data["precipitation"] = {
            "level": "未知",
            "impact": "unknown"
        }
        weather_data["wind"] = {
            "level": "未知",
            "impact": "unknown"
        }
        
        # 分类极端天气
        extreme_class = WeatherClassifier.classify_extreme_weather(all_text)
        weather_data["extreme_weather"] = extreme_class
        
        # 保存到历史
        HistoricalWeatherData.save_weather(date, weather_data)
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": weather_data
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取天气信息失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取天气信息失败"
        }, ensure_ascii=False)


@tool
def get_typical_weather_by_season(
    date: str,
    runtime: ToolRuntime = None
) -> str:
    """
    根据月份获取典型天气（用于预测时自动填写）
    
    参数：
        date: 日期字符串 (YYYY-MM-DD)
    
    返回：典型天气信息JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_typical_weather_by_season")
    
    try:
        month = datetime.strptime(date, "%Y-%m-%d").month
        
        # 获取季节特点
        season = SeasonCharacteristics.get_season_by_month(month)
        
        if season:
            result = {
                "date": date,
                "month": month,
                "season": season,
                "typical_weather": season["typical_weather"],
                "weather_info": {
                    "temperature": f"{season['typical_weather']['temperature'][0]}℃~{season['typical_weather']['temperature'][1]}℃",
                    "precipitation_level": season['typical_weather']['precipitation_level'],
                    "wind_level": season['typical_weather']['wind_level'],
                    "extreme_weather": season['typical_weather']['extreme_weather']
                },
                "workload_impact": season['workload_impact'],
                "description": f"{date}属于{season['name']}，{season['description']}"
            }
        else:
            # 非特殊季节，返回默认值
            result = {
                "date": date,
                "month": month,
                "season": None,
                "typical_weather": {
                    "temperature": (15, 25),
                    "precipitation_level": "小",
                    "wind_level": "小",
                    "extreme_weather": []
                },
                "weather_info": {
                    "temperature": "15℃~25℃",
                    "precipitation_level": "小",
                    "wind_level": "小",
                    "extreme_weather": []
                },
                "workload_impact": "low",
                "description": f"{date}属于普通季节，天气较为平稳"
            }
        
        # 保存到历史
        HistoricalWeatherData.save_weather(date, result["weather_info"])
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取典型天气失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "获取典型天气失败"
        }, ensure_ascii=False)


@tool
def detect_high_incidents_for_prediction(
    hours_back: int = 24,
    runtime: ToolRuntime = None
) -> str:
    """
    检测最近时间段高发的故障、重过载事件，用于预测
    
    参数：
        hours_back: 向前追溯小时数，默认24小时
    
    返回：高发事件检测结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="detect_high_incidents_for_prediction")
    
    try:
        prediction_impact = HighIncidentDetector.get_prediction_impact()
        
        return json.dumps({
            "success": True,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": prediction_impact
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"检测高发事件失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "检测高发事件失败"
        }, ensure_ascii=False)


@tool
def save_weather_workload_association(
    date: str,
    weather_data: str,
    workload_data: str,
    runtime: ToolRuntime = None
) -> str:
    """
    保存天气与工作量的关联数据（用于智能体训练）

    参数：
        date: 日期字符串 (YYYY-MM-DD)
        weather_data: 天气数据JSON字符串
        workload_data: 工作量数据JSON字符串

    返回：操作结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="save_weather_workload_association")

    try:
        weather = json.loads(weather_data)
        workload = json.loads(workload_data)

        period_type = HistoricalWeatherData.save_weather_workload_association(date, weather, workload)

        return json.dumps({
            "success": True,
            "message": f"成功保存{date}的天气-工作量关联数据",
            "period_type": period_type,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"保存关联数据失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "保存关联数据失败"
        }, ensure_ascii=False)


@tool
def manual_adjust_weather(
    date: str,
    temperature: str = "",
    precipitation_level: str = "",
    wind_level: str = "",
    extreme_weather: str = "",
    reason: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    手动修改天气数据（天气总有突发情况，需人工查看当天天气后进行手动修改）

    参数：
        date: 日期字符串 (YYYY-MM-DD)
        temperature: 温度范围（如"17℃~25℃"）
        precipitation_level: 降水量级别（大/中/小）
        wind_level: 风力级别（大/中/小）
        extreme_weather: 极端天气类型（如"暴雨"、"雷雨"、"寒潮"等）
        reason: 修改原因（如"天气预报不准确"、"实际天气变化"等）

    返回：操作结果JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="manual_adjust_weather")

    try:
        # 解析极端天气
        extreme_types = []
        if extreme_weather:
            extreme_types = [et.strip() for et in extreme_weather.split(",") if et.strip()]

        weather_data = {
            "temperature": temperature,
            "precipitation_level": precipitation_level,
            "wind_level": wind_level,
            "extreme_weather": extreme_types
        }

        # 如果某些字段为空，保留原有值
        existing_weather = HistoricalWeatherData.get_weather(date)
        if existing_weather and not existing_weather.get("is_manual"):
            if not temperature:
                weather_data["temperature"] = existing_weather.get("temperature", "")
            if not precipitation_level:
                weather_data["precipitation_level"] = existing_weather.get("precipitation_level", "小")
            if not wind_level:
                weather_data["wind_level"] = existing_weather.get("wind_level", "小")
            if not extreme_weather:
                weather_data["extreme_weather"] = existing_weather.get("extreme_weather", [])

        HistoricalWeatherData.manual_adjust_weather(date, weather_data, reason)

        return json.dumps({
            "success": True,
            "message": f"成功修改{date}的天气数据",
            "weather_data": weather_data,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"手动修改天气失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "手动修改天气失败"
        }, ensure_ascii=False)


@tool
def get_weather_adjustments(
    date: str = "",
    runtime: ToolRuntime = None
) -> str:
    """
    查询手动修改的天气数据

    参数：
        date: 日期字符串 (YYYY-MM-DD)，可选，如果不提供则返回所有记录

    返回：手动修改记录JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="get_weather_adjustments")

    try:
        adjustments = HistoricalWeatherData.get_manual_adjustments(date if date else None)

        return json.dumps({
            "success": True,
            "count": len(adjustments),
            "adjustments": adjustments,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"查询天气修改记录失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "查询天气修改记录失败"
        }, ensure_ascii=False)


@tool
def collect_historical_workload(
    period_type: str = "normal",
    limit: int = 50,
    runtime: ToolRuntime = None
) -> str:
    """
    按时期类型收集历史业务量数据

    时期类型说明：
    - rainy_peak: 雨季高发期（6月中旬到8月中旬），易发雷雨、暴雨天气
    - wind_peak: 大风天气期（春季3-5月、秋季9-11月），易发大风天气
    - winter_peak: 冬季用电高峰期（12月到次年2月），用电负荷高，易发重过载
    - normal: 普通时期（月底月初、非极端天气），工作量适中

    参数：
        period_type: 时期类型，默认"normal"
        limit: 返回的最大数量，默认50

    返回：历史业务量数据JSON字符串
    """
    ctx = runtime.context if runtime else new_context(method="collect_historical_workload")

    try:
        valid_periods = ["rainy_peak", "wind_peak", "winter_peak", "normal"]
        if period_type not in valid_periods:
            return json.dumps({
                "success": False,
                "error": f"无效的时期类型: {period_type}",
                "valid_types": valid_periods
            }, ensure_ascii=False)

        historical_data = HistoricalWeatherData.collect_historical_workload_by_period(
            period_type, limit=limit
        )

        period_names = {
            "rainy_peak": "雨季高发期",
            "wind_peak": "大风天气期",
            "winter_peak": "冬季用电高峰期",
            "normal": "普通时期"
        }

        # 统计分析
        workload_stats = {
            "total_count": len(historical_data),
            "avg_workload_count": 0,
            "avg_workload_weight": 0,
            "max_workload_count": 0,
            "min_workload_count": 0
        }

        if historical_data:
            total_count = sum(d["workload"].get("summary", {}).get("total_count", 0) for d in historical_data)
            total_weight = sum(d["workload"].get("summary", {}).get("total_weight", 0) for d in historical_data)
            counts = [d["workload"].get("summary", {}).get("total_count", 0) for d in historical_data]

            workload_stats["avg_workload_count"] = round(total_count / len(historical_data), 2)
            workload_stats["avg_workload_weight"] = round(total_weight / len(historical_data), 2)
            workload_stats["max_workload_count"] = max(counts) if counts else 0
            workload_stats["min_workload_count"] = min(counts) if counts else 0

        return json.dumps({
            "success": True,
            "period_type": period_type,
            "period_name": period_names.get(period_type, period_type),
            "statistics": workload_stats,
            "historical_data": historical_data,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"收集历史业务量数据失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "收集历史业务量数据失败"
        }, ensure_ascii=False)
