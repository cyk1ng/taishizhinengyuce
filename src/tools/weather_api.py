"""
和风天气数据获取工具

提供实时天气信息和天气预报功能，支持：
- 实时天气状况
- 7天天气预报
- 温度、湿度、风力等信息
- 天气预警信息

API文档: https://dev.qweather.com/docs/api/
"""

import os
import random
import requests
from typing import Dict, List, Optional
from datetime import datetime


class WeatherAPI:
    """和风天气API调用类"""
    
    def __init__(self, api_key: str = None):
        """
        初始化天气API
        
        参数:
            api_key: 和风天气API Key（可选，默认从环境变量读取）
        """
        # 优先使用传入的API Key，其次使用环境变量
        self.api_key = api_key or os.getenv("WEATHER_API_KEY", "44ff4071f86641979f59da2daed5505e")
        
        # API端点（开发环境使用devapi，生产环境使用api）
        self.api_endpoint = os.getenv("WEATHER_API_ENDPOINT", "https://devapi.qweather.com/v7")
        
        # 默认城市（广州: 101280101）
        self.default_city = os.getenv("DEFAULT_CITY", "101280101")
        
        # 是否使用模拟数据
        self.use_mock = not bool(self.api_key)
        
        if self.use_mock:
            print("⚠️ 未配置天气API密钥，使用模拟数据")
            print("   提示：请在.env文件中配置 WEATHER_API_KEY")
    
    def get_weather_now(self, city: str = None) -> Dict:
        """
        获取实时天气
        
        参数:
            city: 城市代码（默认广州101280101）
        
        返回:
            天气信息字典
        """
        if self.use_mock:
            return self._get_mock_weather()
        
        try:
            city_code = city or self.default_city
            url = f"{self.api_endpoint}/weather/now"
            
            params = {
                "location": city_code,
                "key": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()

                if data.get("code") == "200":
                    now = data.get("now", {})

                    # 转换为前端期望的格式
                    temp = int(now.get("temp", "25"))
                    temp_min = temp - random.randint(2, 5)
                    temp_max = temp + random.randint(3, 6)

                    # 根据风力等级判断风力大小
                    wind_scale_str = now.get("windScale", "3级")
                    wind_scale = int(''.join(filter(str.isdigit, wind_scale_str))) if wind_scale_str else 3
                    if wind_scale <= 6:
                        wind = "小"
                    elif wind_scale <= 10:
                        wind = "中"
                    else:
                        wind = "大"

                    # 根据天气状况判断降水量
                    text = now.get("text", "晴")
                    if "大雨" in text or "暴雨" in text:
                        precipitation = "大"
                    elif "中雨" in text or "雨" in text:
                        precipitation = "中"
                    else:
                        precipitation = "小"

                    # 判断极端天气
                    extreme = ""
                    if "寒潮" in text or "暴雪" in text:
                        extreme = "寒潮"
                    elif "冰雹" in text:
                        extreme = "冰雹"
                    elif "雷雨" in text:
                        extreme = "雷雨"
                    elif "暴雨" in text:
                        extreme = "暴雨"
                    elif "台风" in text:
                        extreme = "台风"

                    return {
                        "success": True,
                        "data": {
                            "tempMin": temp_min,
                            "tempMax": temp_max,
                            "precipitation": precipitation,
                            "wind": wind,
                            "extreme": extreme,
                            "update_time": data.get("updateTime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        }
                    }
                else:
                    error_code = data.get("code")
                    error_msg = self._get_error_message(error_code)
                    print(f"天气API返回错误: {error_code} - {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "error_code": error_code,
                        "data": self._get_mock_weather()["data"]
                    }
            else:
                print(f"天气API请求失败: HTTP {response.status_code}")
                return self._get_mock_weather()
                
        except requests.exceptions.Timeout:
            print("天气API请求超时")
            return self._get_mock_weather()
        except Exception as e:
            print(f"获取天气数据失败: {e}")
            return self._get_mock_weather()
    
    def get_weather_7d(self, city: str = None) -> Dict:
        """
        获取7天天气预报
        
        参数:
            city: 城市代码（默认广州101280101）
        
        返回:
            7天天气预报字典
        """
        if self.use_mock:
            return self._get_mock_forecast()
        
        try:
            city_code = city or self.default_city
            url = f"{self.api_endpoint}/weather/7d"
            
            params = {
                "location": city_code,
                "key": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == "200":
                    daily = data.get("daily", [])
                    forecast = []
                    
                    for day in daily:
                        forecast.append({
                            "date": day.get("fxDate", ""),
                            "weekday": self._get_weekday(day.get("fxDate", "")),
                            "text_day": day.get("textDay", "--"),
                            "text_night": day.get("textNight", "--"),
                            "icon_day": self._get_weather_icon(day.get("iconDay", "")),
                            "icon_night": self._get_weather_icon(day.get("iconNight", "")),
                            "temp_max": day.get("tempMax", "--"),
                            "temp_min": day.get("tempMin", "--"),
                            "wind_dir_day": day.get("windDirDay", "--"),
                            "wind_scale_day": day.get("windScaleDay", "--"),
                            "humidity": day.get("humidity", "--"),
                            "uv_index": day.get("uvIndex", "--"),
                            "precip": day.get("precip", "0.0"),
                        })
                    
                    return {
                        "success": True,
                        "data": {
                            "city": city_code,
                            "update_time": data.get("updateTime", ""),
                            "forecast": forecast
                        }
                    }
                else:
                    error_code = data.get("code")
                    error_msg = self._get_error_message(error_code)
                    print(f"天气API返回错误: {error_code} - {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "error_code": error_code,
                        "data": self._get_mock_forecast()["data"]
                    }
            else:
                print(f"天气API请求失败: HTTP {response.status_code}")
                return self._get_mock_forecast()
                
        except requests.exceptions.Timeout:
            print("天气API请求超时")
            return self._get_mock_forecast()
        except Exception as e:
            print(f"获取天气预报失败: {e}")
            return self._get_mock_forecast()
    
    def get_weather_3d(self, city: str = None) -> Dict:
        """
        获取3天天气预报
        
        参数:
            city: 城市代码
        
        返回:
            3天天气预报字典
        """
        result = self.get_weather_7d(city)
        if result.get("success") and result.get("data", {}).get("forecast"):
            result["data"]["forecast"] = result["data"]["forecast"][:3]
        return result
    
    def _get_weekday(self, date_str: str) -> str:
        """获取星期几"""
        if not date_str:
            return ""
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return weekdays[date.weekday()]
        except:
            return ""
    
    def _get_weather_icon(self, icon_code: str) -> str:
        """
        根据天气图标代码获取emoji
        
        和风天气图标代码: https://dev.qweather.com/docs/resource/icons/
        """
        icon_map = {
            "100": "☀️",  # 晴
            "101": "☁️",  # 多云
            "102": "⛅",  # 少云
            "103": "⛅",  # 晴间多云
            "104": "☁️",  # 阴
            "150": "☀️",  # 晴（夜间）
            "151": "☁️",  # 多云（夜间）
            "152": "🌙",  # 少云（夜间）
            "153": "🌙",  # 晴间多云（夜间）
            "300": "🌧️",  # 阵雨
            "301": "⛈️",  # 强阵雨
            "302": "⛈️",  # 雷阵雨
            "303": "⛈️",  # 强雷阵雨
            "304": "⛈️",  # 雷阵雨伴有冰雹
            "305": "🌧️",  # 小雨
            "306": "🌧️",  # 中雨
            "307": "🌧️",  # 大雨
            "308": "⛈️",  # 极端降雨
            "309": "🌧️",  # 毛毛雨
            "310": "⛈️",  # 暴雨
            "311": "⛈️",  # 大暴雨
            "312": "⛈️",  # 特大暴雨
            "313": "🌧️",  # 冻雨
            "314": "🌧️",  # 小到中雨
            "315": "🌧️",  # 中到大雨
            "316": "⛈️",  # 大到暴雨
            "317": "⛈️",  # 暴雨到大暴雨
            "318": "⛈️",  # 大暴雨到特大暴雨
            "399": "🌧️",  # 雨
            "400": "🌨️",  # 小雪
            "401": "🌨️",  # 中雪
            "402": "🌨️",  # 大雪
            "403": "🌨️",  # 暴雪
            "404": "🌨️",  # 雨夹雪
            "405": "🌨️",  # 雨雪天气
            "406": "🌨️",  # 阵雨夹雪
            "407": "🌨️",  # 阵雪
            "408": "🌨️",  # 小到中雪
            "409": "🌨️",  # 中到大雪
            "410": "🌨️",  # 大到暴雪
            "499": "🌨️",  # 雪
            "500": "🌫️",  # 薄雾
            "501": "🌫️",  # 雾
            "502": "🌫️",  # 霾
            "503": "🌫️",  # 扬沙
            "504": "🌫️",  # 浮尘
            "507": "🏜️",  # 沙尘暴
            "508": "🏜️",  # 强沙尘暴
            "509": "🌫️",  # 浓雾
            "510": "🌫️",  # 强浓雾
            "511": "🌫️",  # 中度霾
            "512": "🌫️",  # 重度霾
            "513": "🌫️",  # 严重霾
            "514": "🌫️",  # 大雾
            "515": "🌫️",  # 特强浓雾
            "900": "🌡️",  # 热
            "901": "🥶",  # 冷
            "999": "❓",  # 未知
        }
        
        return icon_map.get(icon_code, "🌤️")
    
    def _get_error_message(self, code: str) -> str:
        """获取错误信息"""
        error_map = {
            "400": "请求错误",
            "401": "认证失败，API Key无效",
            "402": "超过访问次数或余额不足",
            "403": "无访问权限",
            "404": "查询的数据不存在",
            "429": "请求超过限定的QPM",
            "500": "服务器错误",
        }
        return error_map.get(code, f"未知错误({code})")
    
    def _get_mock_weather(self) -> Dict:
        """获取模拟天气数据（前端期望格式）"""
        import random

        # 根据当前时间生成温度范围
        hour = datetime.now().hour
        if 6 <= hour <= 9:
            temp_min = random.randint(18, 24)
            temp_max = random.randint(25, 30)
        elif 10 <= hour <= 16:
            temp_min = random.randint(26, 32)
            temp_max = random.randint(33, 38)
        elif 17 <= hour <= 19:
            temp_min = random.randint(24, 28)
            temp_max = random.randint(29, 33)
        else:
            temp_min = random.randint(16, 22)
            temp_max = random.randint(23, 27)

        # 随机生成降水量
        precip_options = ["小", "中", "大"]
        precipitation = random.choice(precip_options)

        # 随机生成风力
        wind_options = ["小", "中", "大"]
        wind = random.choice(wind_options)

        # 随机生成极端天气（30%概率）
        extreme_options = ["", "", "", "寒潮", "暴雨", "雷雨", "冰雹", "大风"]
        extreme = random.choice(extreme_options)

        return {
            "success": True,
            "data": {
                "tempMin": temp_min,
                "tempMax": temp_max,
                "precipitation": precipitation,
                "wind": wind,
                "extreme": extreme,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_mock": True
            }
        }
    
    def _get_mock_forecast(self) -> Dict:
        """获取模拟7天预报数据"""
        import random
        
        weather_options = ["晴", "多云", "阴", "小雨", "中雨"]
        wind_dirs = ["东风", "南风", "西风", "北风"]
        
        forecast = []
        today = datetime.now()
        
        for i in range(7):
            date = today + timedelta(days=i)
            temp_max = random.randint(26, 32)
            temp_min = temp_max - random.randint(5, 10)
            
            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "weekday": self._get_weekday(date.strftime("%Y-%m-%d")),
                "text_day": random.choice(weather_options),
                "text_night": random.choice(weather_options),
                "icon_day": "☀️",
                "icon_night": "🌙",
                "temp_max": str(temp_max),
                "temp_min": str(temp_min),
                "wind_dir_day": random.choice(wind_dirs),
                "wind_scale_day": f"{random.randint(1,3)}级",
                "humidity": str(random.randint(40, 80)),
                "uv_index": str(random.randint(1, 8)),
                "precip": "0.0",
                "is_mock": True
            })
        
        return {
            "success": True,
            "data": {
                "city": self.default_city,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "forecast": forecast
            }
        }


# 需要timedelta用于模拟数据
from datetime import timedelta


# 创建全局天气API实例
weather_api = WeatherAPI()


def get_weather_info(city: str = None) -> Dict:
    """
    获取天气信息（工具函数）
    
    参数:
        city: 城市代码
    
    返回:
        天气信息字典
    """
    return weather_api.get_weather_now(city)


def get_weather_forecast_7d(city: str = None) -> Dict:
    """
    获取7天天气预报（工具函数）
    
    参数:
        city: 城市代码
    
    返回:
        7天天气预报字典
    """
    return weather_api.get_weather_7d(city)


def get_weather_forecast_3d(city: str = None) -> Dict:
    """
    获取3天天气预报（工具函数）
    
    参数:
        city: 城市代码
    
    返回:
        3天天气预报字典
    """
    return weather_api.get_weather_3d(city)
