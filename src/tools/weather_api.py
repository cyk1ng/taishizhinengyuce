"""
天气数据获取工具

提供实时天气信息获取功能，支持：
- 实时天气状况
- 温度、湿度、风力等信息
- 天气预警信息
"""

import os
import requests
from typing import Dict, Optional
from datetime import datetime


class WeatherAPI:
    """天气API调用类"""
    
    def __init__(self):
        """初始化天气API"""
        # 优先使用环境变量中的API配置
        self.api_key = os.getenv("WEATHER_API_KEY", "")
        self.api_endpoint = os.getenv("WEATHER_API_ENDPOINT", "https://devapi.qweather.com/v7")
        
        # 默认城市（北京）
        self.default_city = os.getenv("DEFAULT_CITY", "101010100")
        
        # 如果没有配置API Key，使用免费模拟数据
        self.use_mock = not bool(self.api_key)
        
        if self.use_mock:
            print("⚠️ 未配置天气API密钥，使用模拟数据")
            print("   提示：请在.env文件中配置 WEATHER_API_KEY")
    
    def get_weather_now(self, city: str = None) -> Dict:
        """
        获取实时天气
        
        参数:
            city: 城市代码（默认北京101010100）
        
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
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == "200":
                    now = data.get("now", {})
                    return {
                        "success": True,
                        "data": {
                            "temp": now.get("temp", "--"),
                            "feels_like": now.get("feelsLike", "--"),
                            "text": now.get("text", "未知"),
                            "icon": self._get_weather_icon(now.get("text", "")),
                            "wind_dir": now.get("windDir", "--"),
                            "wind_scale": now.get("windScale", "--"),
                            "wind_speed": now.get("windSpeed", "--"),
                            "humidity": now.get("humidity", "--"),
                            "pressure": now.get("pressure", "--"),
                            "visibility": now.get("vis", "--"),
                            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    }
                else:
                    print(f"天气API返回错误: {data.get('code')}")
                    return self._get_mock_weather()
            else:
                print(f"天气API请求失败: {response.status_code}")
                return self._get_mock_weather()
                
        except Exception as e:
            print(f"获取天气数据失败: {e}")
            return self._get_mock_weather()
    
    def _get_mock_weather(self) -> Dict:
        """
        获取模拟天气数据
        
        返回:
            模拟的天气信息
        """
        import random
        from datetime import datetime
        
        # 模拟天气状况
        weather_options = [
            {"text": "晴", "icon": "☀️"},
            {"text": "多云", "icon": "⛅"},
            {"text": "阴", "icon": "☁️"},
            {"text": "小雨", "icon": "🌧️"},
            {"text": "中雨", "icon": "🌧️"},
            {"text": "雷阵雨", "icon": "⛈️"},
        ]
        
        wind_options = [
            {"dir": "东风", "scale": "2级", "speed": "2.5"},
            {"dir": "东南风", "scale": "3级", "speed": "3.8"},
            {"dir": "南风", "scale": "2级", "speed": "2.2"},
            {"dir": "西南风", "scale": "1级", "speed": "1.5"},
            {"dir": "西风", "scale": "3级", "speed": "4.2"},
            {"dir": "北风", "scale": "2级", "speed": "2.8"},
        ]
        
        weather = random.choice(weather_options)
        wind = random.choice(wind_options)
        
        # 根据时间模拟温度（早晚凉，中午热）
        hour = datetime.now().hour
        if 6 <= hour <= 9:
            temp = random.randint(18, 24)
        elif 10 <= hour <= 16:
            temp = random.randint(26, 32)
        elif 17 <= hour <= 19:
            temp = random.randint(24, 28)
        else:
            temp = random.randint(16, 22)
        
        return {
            "success": True,
            "data": {
                "temp": str(temp),
                "feels_like": str(temp - random.randint(1, 3)),
                "text": weather["text"],
                "icon": weather["icon"],
                "wind_dir": wind["dir"],
                "wind_scale": wind["scale"],
                "wind_speed": wind["speed"],
                "humidity": str(random.randint(40, 80)),
                "pressure": str(random.randint(1000, 1020)),
                "visibility": str(random.randint(10, 30)),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_mock": True
            }
        }
    
    def _get_weather_icon(self, text: str) -> str:
        """
        根据天气文本获取图标
        
        参数:
            text: 天气描述文本
        
        返回:
            天气图标
        """
        icon_map = {
            "晴": "☀️",
            "多云": "⛅",
            "阴": "☁️",
            "小雨": "🌧️",
            "中雨": "🌧️",
            "大雨": "🌧️",
            "暴雨": "⛈️",
            "雷阵雨": "⛈️",
            "小雪": "🌨️",
            "中雪": "🌨️",
            "大雪": "🌨️",
            "雾": "🌫️",
            "霾": "🌫️",
            "沙尘暴": "🏜️",
        }
        
        for key, icon in icon_map.items():
            if key in text:
                return icon
        
        return "🌤️"


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
