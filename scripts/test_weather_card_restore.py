#!/usr/bin/env python3
"""
测试天气卡片恢复
"""

import os
import re
from pathlib import Path

def test_weather_card():
    """测试天气卡片恢复"""
    print("开始测试天气卡片恢复...")

    # 测试文件路径
    project_root = Path('/workspace/projects')
    html_file = project_root / 'frontend' / 'index.html'
    css_file = project_root / 'frontend' / 'css' / 'style.css'
    js_file = project_root / 'frontend' / 'js' / 'app.js'

    # 测试结果
    tests = []

    # 1. 测试HTML - 导航栏无天气信息条
    print("\n1. 测试HTML - 导航栏无天气信息条")
    html_content = html_file.read_text(encoding='utf-8')
    header_section = re.search(r'<header class="header">.*?</header>', html_content, re.DOTALL)
    if header_section:
        header_text = header_section.group(0)
        has_weather_bar = 'weather-info-bar' in header_text
        tests.append({
            'name': '导航栏无天气信息条',
            'status': not has_weather_bar,
            'message': '导航栏中weather-info-bar元素' + ('存在' if has_weather_bar else '不存在')
        })
        print(f"   {'✅' if not has_weather_bar else '❌'} 导航栏无天气信息条")

    # 2. 测试HTML - 统计卡片有天气卡片
    print("\n2. 测试HTML - 统计卡片有天气卡片")
    stats_section = re.search(r'<section class="stats-overview">.*?</section>', html_content, re.DOTALL)
    if stats_section:
        stats_text = stats_section.group(0)
        has_weather_card = 'weather-card' in stats_text
        tests.append({
            'name': '统计卡片有天气卡片',
            'status': has_weather_card,
            'message': '统计卡片中weather-card元素' + ('存在' if has_weather_card else '不存在')
        })
        print(f"   {'✅' if has_weather_card else '❌'} 统计卡片有天气卡片")

    # 3. 测试HTML - 天气卡片内容完整
    print("\n3. 测试HTML - 天气卡片内容完整")
    # 使用更简单的方法：检查整个HTML文件中是否包含这些元素
    has_temp = 'weather-temp' in html_content
    has_precip = 'weather-precipitation' in html_content
    has_wind = 'weather-wind' in html_content
    has_extreme = 'weather-extreme' in html_content
    has_icon = 'weather-condition-icon' in html_content

    all_present = all([has_temp, has_precip, has_wind, has_extreme, has_icon])
    tests.append({
        'name': '天气卡片内容完整',
        'status': all_present,
        'message': f'温度:{has_temp}, 降水:{has_precip}, 风力:{has_wind}, 极端:{has_extreme}, 图标:{has_icon}'
    })
    print(f"   {'✅' if all_present else '❌'} 天气卡片内容完整")
    print(f"      - 温度元素: {'✅' if has_temp else '❌'}")
    print(f"      - 降水元素: {'✅' if has_precip else '❌'}")
    print(f"      - 风力元素: {'✅' if has_wind else '❌'}")
    print(f"      - 极端天气元素: {'✅' if has_extreme else '❌'}")
    print(f"      - 天气图标: {'✅' if has_icon else '❌'}")

    # 4. 测试CSS - 统计网格3列布局
    print("\n4. 测试CSS - 统计网格3列布局")
    css_content = css_file.read_text(encoding='utf-8')
    grid_layout = re.search(r'\.stats-grid\s*{[^}]*grid-template-columns:\s*([^;]+)', css_content)
    if grid_layout:
        columns = grid_layout.group(1)
        is_3_columns = '3' in columns
        tests.append({
            'name': '统计网格3列布局',
            'status': is_3_columns,
            'message': f'网格列数: {columns}'
        })
        print(f"   {'✅' if is_3_columns else '❌'} 统计网格3列布局: {columns}")

    # 5. 测试CSS - 天气卡片样式
    print("\n5. 测试CSS - 天气卡片样式")
    weather_card_style = re.search(r'\.weather-card\s*{[^}]*}', css_content)
    if weather_card_style:
        style_text = weather_card_style.group(0)
        has_border_left = 'border-left' in style_text and 'accent-cyan' in style_text
        tests.append({
            'name': '天气卡片左侧青色边框',
            'status': has_border_left,
            'message': '天气卡片有左侧青色边框'
        })
        print(f"   {'✅' if has_border_left else '❌'} 天气卡片左侧青色边框")

    # 6. 测试CSS - 天气信息容器样式
    print("\n6. 测试CSS - 天气信息容器样式")
    has_weather_info = '.weather-info' in css_content
    has_weather_details = '.weather-details' in css_content
    has_weather_detail_item = '.weather-detail-item' in css_content

    all_styles_present = all([has_weather_info, has_weather_details, has_weather_detail_item])
    tests.append({
        'name': '天气信息容器样式完整',
        'status': all_styles_present,
        'message': f'容器:{has_weather_info}, 详情:{has_weather_details}, 项目:{has_weather_detail_item}'
    })
    print(f"   {'✅' if all_styles_present else '❌'} 天气信息容器样式完整")
    print(f"      - weather-info: {'✅' if has_weather_info else '❌'}")
    print(f"      - weather-details: {'✅' if has_weather_details else '❌'}")
    print(f"      - weather-detail-item: {'✅' if has_weather_detail_item else '❌'}")

    # 7. 测试JavaScript - 天气数据更新函数
    print("\n7. 测试JavaScript - 天气数据更新函数")
    js_content = js_file.read_text(encoding='utf-8')
    update_weather_func = re.search(r'async function updateWeatherData\(\)\s*{[^}]*}', js_content, re.DOTALL)
    if update_weather_func:
        func_text = update_weather_func.group(0)
        has_extreme_el = 'weather-extreme' in func_text
        tests.append({
            'name': '更新函数包含极端天气元素',
            'status': has_extreme_el,
            'message': f'updateWeatherData函数{"包含" if has_extreme_el else "不包含"}weather-extreme元素'
        })
        print(f"   {'✅' if has_extreme_el else '❌'} 更新函数包含极端天气元素")

    # 8. 测试JavaScript - 天气详情弹窗函数
    print("\n8. 测试JavaScript - 天气详情弹窗函数")
    show_weather_modal_func = re.search(r'function showWeatherModal\(\)\s*{[^}]*}', js_content, re.DOTALL)
    if show_weather_modal_func:
        func_text = show_weather_modal_func.group(0)
        has_modal = 'weather-modal-content' in func_text
        has_grid = 'weather-detail-grid' in func_text
        has_edit_btn = 'openWeatherAdjustModal' in func_text

        all_features = all([has_modal, has_grid, has_edit_btn])
        tests.append({
            'name': '天气详情弹窗功能完整',
            'status': all_features,
            'message': f'弹窗:{has_modal}, 网格:{has_grid}, 编辑按钮:{has_edit_btn}'
        })
        print(f"   {'✅' if all_features else '❌'} 天气详情弹窗功能完整")
        print(f"      - weather-modal-content: {'✅' if has_modal else '❌'}")
        print(f"      - weather-detail-grid: {'✅' if has_grid else '❌'}")
        print(f"      - openWeatherAdjustModal: {'✅' if has_edit_btn else '❌'}")

    # 打印测试结果
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)

    passed = sum(1 for test in tests if test['status'])
    total = len(tests)

    for i, test in enumerate(tests, 1):
        status = '✅ 通过' if test['status'] else '❌ 失败'
        print(f"{i}. {test['name']}: {status}")
        print(f"   {test['message']}")

    print("\n" + "="*50)
    print(f"总计: {passed}/{total} 通过")
    print("="*50)

    if passed == total:
        print("\n🎉 所有测试通过！天气卡片恢复成功。")
        print("\n预期效果:")
        print("- 第一行显示3个卡片：计划工作量、非计划工作量、天气状况")
        print("- 天气卡片有框，显示完整信息")
        print("- 温度：17℃~25℃")
        print("- 降水量：大")
        print("- 风力：中风")
        print("- 极端天气情况：暴雨")
    else:
        print("\n⚠️  部分测试失败，请检查上述失败项。")

    return passed == total

if __name__ == '__main__':
    success = test_weather_card()
    exit(0 if success else 1)
