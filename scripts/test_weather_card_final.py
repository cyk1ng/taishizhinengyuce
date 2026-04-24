#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天气卡片事件监听器测试脚本
测试天气卡片是否正确使用事件监听器
"""

import re
from pathlib import Path

def test_html_event_listener():
    """测试HTML是否使用事件监听器（移除onclick）"""
    html_path = Path('/workspace/projects/frontend/index.html')
    html_content = html_path.read_text(encoding='utf-8')

    tests = [
        {
            'name': '天气卡片使用id而非onclick',
            'check': 'id="weather-card"' in html_content and
                     'onclick="showWeatherModal(event)"' not in html_content,
            'expected': True
        },
        {
            'name': '天气卡片具有cursor: pointer',
            'check': 'weather-card' in html_content and
                     'cursor: pointer' in html_content,
            'expected': True
        }
    ]

    print("=== HTML事件监听器测试 ===")
    for test in tests:
        result = "✅ 通过" if test['check'] == test['expected'] else "❌ 失败"
        print(f"{test['name']}: {result}")
        if test['check'] != test['expected']:
            print(f"   期望: {test['expected']}, 实际: {test['check']}")

    return all(test['check'] == test['expected'] for test in tests)

def test_js_event_listener():
    """测试JavaScript是否添加了事件监听器"""
    js_path = Path('/workspace/projects/frontend/js/app.js')
    js_content = js_path.read_text(encoding='utf-8')

    tests = [
        {
            'name': 'showWeatherModal函数存在',
            'check': 'function showWeatherModal' in js_content,
            'expected': True
        },
        {
            'name': '函数接收event参数',
            'check': 'function showWeatherModal(event)' in js_content,
            'expected': True
        },
        {
            'name': 'addEventListener绑定weather-card',
            'check': "getElementById('weather-card')" in js_content and
                     'addEventListener' in js_content,
            'expected': True
        },
        {
            'name': '函数体中处理event参数',
            'check': 'preventDefault()' in js_content and
                     'stopPropagation()' in js_content,
            'expected': True
        }
    ]

    print("\n=== JavaScript事件监听器测试 ===")
    for test in tests:
        result = "✅ 通过" if test['check'] == test['expected'] else "❌ 失败"
        print(f"{test['name']}: {result}")
        if test['check'] != test['expected']:
            print(f"   期望: {test['expected']}, 实际: {test['check']}")

    return all(test['check'] == test['expected'] for test in tests)

def main():
    """运行所有测试"""
    print("=" * 60)
    print("天气卡片事件监听器完整测试")
    print("=" * 60)

    html_ok = test_html_event_listener()
    js_ok = test_js_event_listener()

    print("\n" + "=" * 60)
    if html_ok and js_ok:
        print("✅ 所有测试通过！天气卡片点击事件已修复。")
        print("\n修复说明：")
        print("1. 移除了HTML中的onclick属性")
        print("2. 添加了id属性（id='weather-card'）")
        print("3. 在JavaScript中添加了事件监听器")
        print("4. 函数正确接收和处理event参数")
        print("\n优势：")
        print("- 避免了onclick和addEventListener冲突")
        print("- 更符合现代JavaScript最佳实践")
        print("- 更好的事件处理控制")
        return 0
    else:
        print("❌ 部分测试失败，请检查代码。")
        return 1

if __name__ == '__main__':
    exit(main())
