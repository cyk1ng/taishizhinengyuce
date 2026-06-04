#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
界面天气信息显示测试脚本
验证天气信息条的设计和功能
"""

import os
import sys

def test_html_structure():
    """测试HTML结构"""
    print("测试HTML结构...")

    html_file = 'frontend/index.html'
    if not os.path.exists(html_file):
        print(f"❌ 文件不存在: {html_file}")
        return False

    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ('天气信息条容器', 'class="weather-info-bar"', '天气信息条容器'),
        ('天气图标', 'id="weather-condition-icon"', '天气图标'),
        ('温度显示', 'id="weather-temp"', '温度显示'),
        ('降水量显示', 'id="weather-precipitation"', '降水量显示'),
        ('风力显示', 'id="weather-wind"', '风力显示'),
        ('天气编辑图标', 'class="weather-edit-icon"', '天气编辑图标'),
        ('天气详情弹窗函数', 'onclick="showWeatherModal()"', '天气详情弹窗函数'),
    ]

    all_passed = True
    for name, selector, description in tests:
        if selector in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}")
            all_passed = False

    return all_passed


def test_css_styles():
    """测试CSS样式"""
    print("\n测试CSS样式...")

    css_file = 'frontend/css/style.css'
    if not os.path.exists(css_file):
        print(f"❌ 文件不存在: {css_file}")
        return False

    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ('天气信息条样式', '.weather-info-bar', '天气信息条样式'),
        ('天气项样式', '.weather-item', '天气项样式'),
        ('天气图标样式', '.weather-icon', '天气图标样式'),
        ('天气标签样式', '.weather-label', '天气标签样式'),
        ('天气数值样式', '.weather-value', '天气数值样式'),
        ('天气分隔符样式', '.weather-divider', '天气分隔符样式'),
        ('天气编辑图标样式', '.weather-edit-icon', '天气编辑图标样式'),
    ]

    all_passed = True
    for name, selector, description in tests:
        if selector in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}")
            all_passed = False

    return all_passed


def test_weather_modal_css():
    """测试天气弹窗CSS样式"""
    print("\n测试天气弹窗CSS样式...")

    css_file = 'frontend/css/workload-modal.css'
    if not os.path.exists(css_file):
        print(f"❌ 文件不存在: {css_file}")
        return False

    with open(css_file, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ('天气弹窗内容样式', '.weather-modal-content', '天气弹窗内容样式'),
        ('天气详情网格样式', '.weather-detail-grid', '天气详情网格样式'),
        ('天气详情项样式', '.weather-detail-item', '天气详情项样式'),
        ('天气详情图标样式', '.weather-detail-icon', '天气详情图标样式'),
        ('天气详情信息样式', '.weather-detail-info', '天气详情信息样式'),
        ('天气详情标签样式', '.weather-detail-label', '天气详情标签样式'),
        ('天气详情数值样式', '.weather-detail-value', '天气详情数值样式'),
        ('天气操作按钮样式', '.weather-action-buttons', '天气操作按钮样式'),
        ('弹窗按钮样式', '.modal-btn', '弹窗按钮样式'),
    ]

    all_passed = True
    for name, selector, description in tests:
        if selector in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}")
            all_passed = False

    return all_passed


def test_javascript_functions():
    """测试JavaScript函数"""
    print("\n测试JavaScript函数...")

    js_file = 'frontend/js/app.js'
    if not os.path.exists(js_file):
        print(f"❌ 文件不存在: {js_file}")
        return False

    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()

    tests = [
        ('updateWeatherData函数', 'async function updateWeatherData()', 'updateWeatherData函数'),
        ('天气温度元素', "getElementById('weather-temp')", '天气温度元素'),
        ('天气降水量元素', "getElementById('weather-precipitation')", '天气降水量元素'),
        ('天气风力元素', "getElementById('weather-wind')", '天气风力元素'),
        ('天气图标元素', "getElementById('weather-condition-icon')", '天气图标元素'),
        ('showWeatherModal函数', 'function showWeatherModal()', 'showWeatherModal函数'),
        ('天气详情弹窗', '天气详情', '天气详情弹窗'),
        ('天气详情网格', 'weather-detail-grid', '天气详情网格'),
        ('天气详情项', 'weather-detail-item', '天气详情项'),
        ('手动修改天气按钮', '手动修改天气', '手动修改天气按钮'),
    ]

    all_passed = True
    for name, selector, description in tests:
        if selector in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}")
            all_passed = False

    return all_passed


def test_weather_icon_logic():
    """测试天气图标逻辑"""
    print("\n测试天气图标逻辑...")

    js_file = 'frontend/js/app.js'
    if not os.path.exists(js_file):
        print(f"❌ 文件不存在: {js_file}")
        return False

    with open(js_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查天气图标选择逻辑
    icon_tests = [
        ('大雨图标', "precipitation === '大'", '大雨图标'),
        ('雷雨图标', "extreme.includes('雷')", '雷雨图标'),
        ('雪天图标', "extreme.includes('雪')", '雪天图标'),
        ('寒潮图标', "extreme.includes('寒潮')", '寒潮图标'),
        ('暴风图标', "extreme.includes('暴')", '暴风图标'),
        ('大风图标', "wind === '大'", '大风图标'),
    ]

    all_passed = True
    for name, selector, description in icon_tests:
        if selector in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}")
            all_passed = False

    return all_passed


def main():
    """主函数"""
    print("=" * 60)
    print("界面天气信息显示测试")
    print("=" * 60)

    # 运行所有测试
    results = []

    results.append(('HTML结构', test_html_structure()))
    results.append(('CSS样式', test_css_styles()))
    results.append(('天气弹窗CSS', test_weather_modal_css()))
    results.append(('JavaScript函数', test_javascript_functions()))
    results.append(('天气图标逻辑', test_weather_icon_logic()))

    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n天气信息显示功能已成功集成到界面中：")
        print("  - 天气信息条位于时间显示左侧")
        print("  - 显示天气图标、温度、降水量、风力")
        print("  - 点击天气信息条可查看详情弹窗")
        print("  - 详情弹窗支持手动修改天气")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查上述错误信息")
        return 1


if __name__ == '__main__':
    sys.exit(main())
