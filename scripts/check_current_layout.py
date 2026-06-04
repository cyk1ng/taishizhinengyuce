#!/usr/bin/env python3
"""
检查当前界面的布局和功能
"""

import os
import re

def check_html_structure():
    """检查HTML结构"""
    print("=" * 60)
    print("HTML结构检查")
    print("=" * 60)

    html_file = "/workspace/projects/frontend/index.html"
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查天气信息条
    if '<div class="weather-info-bar"' in content:
        print("✅ 天气信息条存在")
    else:
        print("❌ 天气信息条不存在")

    # 检查统计卡片数量
    stat_cards = re.findall(r'<div class="stat-card', content)
    print(f"✅ 统计卡片数量: {len(stat_cards)}")

    # 检查时间显示
    if '<div class="time-display"' in content:
        print("✅ 时间显示存在")
    else:
        print("❌ 时间显示不存在")

def check_css_styles():
    """检查CSS样式"""
    print("\n" + "=" * 60)
    print("CSS样式检查")
    print("=" * 60)

    css_file = "/workspace/projects/frontend/css/style.css"
    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查天气信息条样式
    if '.weather-info-bar' in content:
        print("✅ 天气信息条样式存在")
    else:
        print("❌ 天气信息条样式不存在")

    # 检查统计卡片样式
    if '.stats-grid' in content:
        print("✅ 统计卡片网格样式存在")
    else:
        print("❌ 统计卡片网格样式不存在")

    # 检查网格列数
    grid_match = re.search(r'\.stats-grid\s*{[^}]*grid-template-columns:\s*([^;]+);', content, re.DOTALL)
    if grid_match:
        print(f"✅ 网格列数: {grid_match.group(1)}")
    else:
        print("❌ 无法找到网格列数")

def check_javascript():
    """检查JavaScript功能"""
    print("\n" + "=" * 60)
    print("JavaScript功能检查")
    print("=" * 60)

    js_file = "/workspace/projects/frontend/js/app.js"
    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查天气数据更新函数
    if 'function updateWeatherData' in content:
        print("✅ updateWeatherData函数存在")
    else:
        print("❌ updateWeatherData函数不存在")

    # 检查天气弹窗函数
    if 'function showWeatherModal' in content:
        print("✅ showWeatherModal函数存在")
    else:
        print("❌ showWeatherModal函数不存在")

def generate_html_preview():
    """生成HTML预览"""
    print("\n" + "=" * 60)
    print("HTML预览")
    print("=" * 60)

    html_file = "/workspace/projects/frontend/index.html"
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取导航栏
    header_start = content.find('<header class="header">')
    if header_start > 0:
        header_end = content.find('</header>', header_start)
        header_content = content[header_start:header_end+9]
        print("\n导航栏结构:")
        print(header_content[:500] + "...")

    # 提取统计卡片
    stats_start = content.find('<section class="stats-overview">')
    if stats_start > 0:
        stats_end = content.find('</section>', stats_start)
        stats_content = content[stats_start:stats_end+11]
        print("\n统计卡片结构:")
        print(stats_content[:500] + "...")

if __name__ == '__main__':
    check_html_structure()
    check_css_styles()
    check_javascript()
    generate_html_preview()

    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    print("\n如果发现任何问题，请告诉我具体需要修复的地方。")
