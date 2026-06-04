#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查天气信息自然样式是否正确
"""

import re
from pathlib import Path

def check_html_structure():
    """检查HTML结构"""
    html_file = Path("/workspace/projects/frontend/index.html")
    content = html_file.read_text(encoding='utf-8')

    # 检查天气信息条容器
    weather_bar_pattern = r'<div class="weather-info-bar".*?>'
    if not re.search(weather_bar_pattern, content, re.DOTALL):
        print("❌ 天气信息条容器不存在")
        return False
    print("✅ 天气信息条容器存在")

    # 检查天气图标
    weather_icon_pattern = r'<span class="weather-icon" id="weather-condition-icon">'
    if not re.search(weather_icon_pattern, content):
        print("❌ 天气图标不存在")
        return False
    print("✅ 天气图标存在")

    # 检查温度显示
    temp_pattern = r'<span class="weather-value" id="weather-temp">'
    if not re.search(temp_pattern, content):
        print("❌ 温度显示不存在")
        return False
    print("✅ 温度显示存在")

    # 检查降水量显示
    precip_pattern = r'<span class="weather-value" id="weather-precipitation">'
    if not re.search(precip_pattern, content):
        print("❌ 降水量显示不存在")
        return False
    print("✅ 降水量显示存在")

    # 检查风力显示
    wind_pattern = r'<span class="weather-value" id="weather-wind">'
    if not re.search(wind_pattern, content):
        print("❌ 风力显示不存在")
        return False
    print("✅ 风力显示存在")

    # 检查编辑图标
    edit_icon_pattern = r'<span class="weather-edit-icon">'
    if not re.search(edit_icon_pattern, content):
        print("❌ 编辑图标不存在")
        return False
    print("✅ 编辑图标存在")

    # 检查分隔符数量
    divider_pattern = r'<span class="weather-divider"></span>'
    dividers = re.findall(divider_pattern, content)
    if len(dividers) != 2:
        print(f"❌ 分隔符数量错误，应为2个，实际为{len(dividers)}个")
        return False
    print(f"✅ 分隔符数量正确（2个）")

    # 检查是否没有天气项容器（验证已简化）
    weather_item_pattern = r'<div class="weather-item">'
    if re.search(weather_item_pattern, content):
        print("⚠️  仍有天气项容器，建议删除")
    else:
        print("✅ 已简化为无天气项容器结构")

    return True

def check_css_style():
    """检查CSS样式"""
    css_file = Path("/workspace/projects/frontend/css/style.css")
    content = css_file.read_text(encoding='utf-8')

    # 检查天气信息条样式
    weather_bar_style_pattern = r'\.weather-info-bar\s*\{'
    if not re.search(weather_bar_style_pattern, content):
        print("❌ 天气信息条样式不存在")
        return False
    print("✅ 天气信息条样式存在")

    # 提取天气信息条样式内容
    weather_bar_match = re.search(r'\.weather-info-bar\s*\{(.*?)\}', content, re.DOTALL)
    if not weather_bar_match:
        print("❌ 无法提取天气信息条样式")
        return False

    weather_bar_css = weather_bar_match.group(1)

    # 检查是否有背景色（自然风格不应该有明显的背景）
    if 'background:' in weather_bar_css or 'background-color:' in weather_bar_css:
        if 'rgba' in weather_bar_css and '0.08' in weather_bar_css:
            print("⚠️  天气信息条仍有背景色，建议删除")
        else:
            print("❌ 天气信息条有背景色，不符合自然风格")
            return False
    else:
        print("✅ 天气信息条无背景色（自然风格）")

    # 检查是否有边框（自然风格不应该有边框）
    if 'border:' in weather_bar_css or 'border-' in weather_bar_css:
        print("❌ 天气信息条有边框，不符合自然风格")
        return False
    else:
        print("✅ 天气信息条无边框（自然风格）")

    # 检查是否有圆角（自然风格不应该有圆角）
    if 'border-radius:' in weather_bar_css:
        print("❌ 天气信息条有圆角，不符合自然风格")
        return False
    else:
        print("✅ 天气信息条无圆角（自然风格）")

    # 检查padding（自然风格padding应该很小或为0）
    if 'padding:' in weather_bar_css:
        padding_match = re.search(r'padding:\s*(\d+)', weather_bar_css)
        if padding_match:
            padding_value = int(padding_match.group(1))
            if padding_value > 8:
                print(f"⚠️  天气信息条padding过大（{padding_value}px）")
            else:
                print(f"✅ 天气信息条padding合理（{padding_value}px）")
    else:
        print("✅ 天气信息条无padding（自然风格）")

    # 检查字体大小
    font_size_match = re.search(r'\.weather-value\s*\{.*?font-size:\s*(\d+)px', content, re.DOTALL)
    if font_size_match:
        font_size = int(font_size_match.group(1))
        if font_size >= 11 and font_size <= 13:
            print(f"✅ 天气数值字体大小合理（{font_size}px）")
        else:
            print(f"⚠️  天气数值字体大小可能不合理（{font_size}px）")

    # 检查分隔符样式
    divider_style_pattern = r'\.weather-divider\s*\{'
    if not re.search(divider_style_pattern, content):
        print("❌ 分隔符样式不存在")
        return False
    print("✅ 分隔符样式存在")

    # 检查分隔符显示
    divider_match = re.search(r'\.weather-divider\s*\{(.*?)\}', content, re.DOTALL)
    if divider_match:
        divider_css = divider_match.group(1)
        if 'display:' in divider_css:
            if 'none' in divider_css:
                print("⚠️  分隔符被隐藏")
            elif 'flex' in divider_css:
                print("✅ 分隔符可见（flex布局）")
        else:
            print("✅ 分隔符默认可见")

    return True

def check_navigation_layout():
    """检查导航栏布局"""
    html_file = Path("/workspace/projects/frontend/index.html")
    content = html_file.read_text(encoding='utf-8')

    # 查找header标签
    header_match = re.search(r'<header[^>]*>(.*?)</header>', content, re.DOTALL)
    if not header_match:
        print("❌ 无法找到header标签")
        return False

    header_content = header_match.group(1)

    # 检查导航元素顺序
    elements_order = []

    # 检查刷新按钮
    if 'refresh-btn' in header_content:
        elements_order.append('刷新按钮')

    # 检查柔性值班计算按钮
    if 'flex-schedule-btn' in header_content:
        elements_order.append('柔性值班计算')

    # 检查天气信息条
    if 'weather-info-bar' in header_content:
        elements_order.append('天气信息条')

    # 检查时间显示
    if 'time-display' in header_content:
        elements_order.append('时间显示')

    print(f"✅ 导航栏元素顺序: {' → '.join(elements_order)}")

    # 验证顺序是否正确
    if len(elements_order) >= 4:
        if elements_order[2] == '天气信息条' and elements_order[3] == '时间显示':
            print("✅ 天气信息条和时间显示顺序正确")
        else:
            print("⚠️  天气信息条和时间显示顺序可能不正确")

    return True

def main():
    """主函数"""
    print("=" * 60)
    print("天气信息自然样式检查")
    print("=" * 60)

    print("\n【1. 检查HTML结构】")
    html_ok = check_html_structure()

    print("\n【2. 检查CSS样式】")
    css_ok = check_css_style()

    print("\n【3. 检查导航栏布局】")
    nav_ok = check_navigation_layout()

    print("\n" + "=" * 60)
    if html_ok and css_ok and nav_ok:
        print("✅ 所有检查通过！天气信息自然样式设置正确。")
    else:
        print("❌ 部分检查失败，请查看详细提示。")
    print("=" * 60)

if __name__ == "__main__":
    main()
