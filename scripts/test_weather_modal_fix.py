#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试天气卡片弹窗修复
验证showWeatherModal函数是否正确接收event参数
"""

import re

def test_weather_modal_function():
    """测试天气弹窗函数"""
    print("=" * 60)
    print("测试天气卡片弹窗修复")
    print("=" * 60)

    # 读取app.js文件
    with open('/workspace/projects/frontend/js/app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 测试1: 检查函数定义是否接收event参数
    pattern = r'function showWeatherModal\s*\(\s*event\s*\)'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试1通过: showWeatherModal函数接收event参数")
    else:
        print("❌ 测试1失败: showWeatherModal函数未接收event参数")
        print("   当前定义: function showWeatherModal()")

    # 测试2: 检查函数体中是否处理了event
    pattern = r'if\s*\(\s*event\s*\)\s*{'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试2通过: showWeatherModal函数体中处理event参数")
    else:
        print("❌ 测试2失败: showWeatherModal函数体中未处理event参数")

    # 测试3: 检查是否调用preventDefault和stopPropagation
    pattern = r'event\.preventDefault\(\)|event\.stopPropagation\(\)'
    matches = re.findall(pattern, content)
    if len(matches) >= 2:
        print(f"✅ 测试3通过: 调用了preventDefault和stopPropagation (共{len(matches)}次)")
    else:
        print(f"⚠️  测试3警告: 只调用了{len(matches)}个事件处理方法")

    # 测试4: 对比其他卡片函数
    print("\n对比测试:")
    pattern = r'function (showPlanWorkloadModal|showNonPlanWorkloadModal)\s*\(\s*event\s*\)'
    matches = re.findall(pattern, content)
    if matches:
        print(f"✅ 测试4通过: 其他卡片函数也接收event参数: {matches}")
    else:
        print("❌ 测试4失败: 其他卡片函数未接收event参数")

    # 测试5: 检查编辑模式是否存在
    pattern = r'id=["\']weather-edit-mode["\']'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试5通过: 天气编辑模式HTML存在")
    else:
        print("❌ 测试5失败: 天气编辑模式HTML不存在")

    # 测试6: 检查查看模式是否存在
    pattern = r'id=["\']weather-view-mode["\']'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试6通过: 天气查看模式HTML存在")
    else:
        print("❌ 测试6失败: 天气查看模式HTML不存在")

    # 测试7: 检查编辑按钮是否存在
    pattern = r'id=["\']weather-edit-btn["\']'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试7通过: 编辑按钮存在")
    else:
        print("❌ 测试7失败: 编辑按钮不存在")

    # 测试8: 检查保存按钮是否存在
    pattern = r'id=["\']weather-save-btn["\']'
    match = re.search(pattern, content)
    if match:
        print("✅ 测试8通过: 保存按钮存在")
    else:
        print("❌ 测试8失败: 保存按钮不存在")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_weather_modal_function()
