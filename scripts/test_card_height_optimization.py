#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统计卡片高度优化
验证第一行三个卡片的高度调整效果
"""

import re

def test_card_height():
    """测试卡片高度调整"""
    print("=" * 60)
    print("测试统计卡片高度优化")
    print("=" * 60)

    with open('/workspace/projects/frontend/css/style.css', 'r', encoding='utf-8') as f:
        css_content = f.read()

    tests_passed = 0
    tests_total = 0

    # 测试1: 检查卡片padding是否减小
    tests_total += 1
    if 'padding: 12px 16px' in css_content:
        print("✅ 测试1通过: 卡片padding已减小为12px 16px")
        tests_passed += 1
    else:
        print("❌ 测试1失败: 卡片padding未正确设置")

    # 测试2: 检查头部margin-bottom是否减小
    tests_total += 1
    if 'margin-bottom: 6px' in css_content:
        print("✅ 测试2通过: 头部margin-bottom已减小为6px")
        tests_passed += 1
    else:
        print("❌ 测试2失败: 头部margin-bottom未正确设置")

    # 测试3: 检查天气详情是否为水平布局
    tests_total += 1
    if 'flex-direction: row' in css_content:
        print("✅ 测试3通过: 天气详情已改为水平布局")
        tests_passed += 1
    else:
        print("❌ 测试3失败: 天气详情未改为水平布局")

    # 测试4: 检查天气图标大小是否减小
    tests_total += 1
    if 'font-size: 32px' in css_content and 'weather-condition-icon' in css_content:
        print("✅ 测试4通过: 天气图标大小已减小为32px")
        tests_passed += 1
    else:
        print("❌ 测试4失败: 天气图标大小未正确设置")

    # 测试5: 检查weather-info gap是否减小
    tests_total += 1
    if 'gap: 12px' in css_content and '.weather-info' in css_content:
        print("✅ 测试5通过: weather-info gap已减小为12px")
        tests_passed += 1
    else:
        print("❌ 测试5失败: weather-info gap未正确设置")

    # 测试6: 检查天气详情gap是否减小
    tests_total += 1
    if 'gap: 6px 12px' in css_content:
        print("✅ 测试6通过: 天气详情gap已减小为6px 12px")
        tests_passed += 1
    else:
        print("❌ 测试6失败: 天气详情gap未正确设置")

    # 测试7: 检查天气字体大小是否减小
    tests_total += 1
    weather_label_count = css_content.count('.weather-label') + css_content.count('.weather-value')
    if weather_label_count >= 2 and 'font-size: 10px' in css_content:
        print("✅ 测试7通过: 天气字体大小已减小为10px")
        tests_passed += 1
    else:
        print("❌ 测试7失败: 天气字体大小未正确设置")

    print("\n" + "=" * 60)
    print(f"测试结果: {tests_passed}/{tests_total} 通过")
    print("=" * 60)

    if tests_passed == tests_total:
        print("✅ 所有测试通过！卡片高度优化完成。")
        return True
    else:
        print("❌ 部分测试失败，请检查CSS文件。")
        return False

if __name__ == '__main__':
    test_card_height()
