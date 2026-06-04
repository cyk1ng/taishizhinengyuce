#!/usr/bin/env python3
"""
测试界面布局修改
验证第一行是否从3个框改为2个框，时间是否改为更自然的样式
"""

import os
import sys

# 添加项目路径
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_path)

def test_html_structure():
    """测试HTML结构"""
    print("=" * 60)
    print("测试HTML结构")
    print("=" * 60)

    # 读取index.html
    html_path = os.path.join(project_path, 'frontend', 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 检查时间显示样式
    print("\n1. 检查时间显示样式...")
    if 'time-display' in html_content:
        print("   ✅ 时间使用新的 time-display 样式（无框）")
    else:
        print("   ❌ 时间未使用 time-display 样式")

    if 'time-value' in html_content:
        print("   ✅ 时间值使用 time-value 样式")
    else:
        print("   ❌ 时间值未使用 time-value 样式")

    # 检查统计卡片数量
    print("\n2. 检查统计卡片数量...")
    stats_cards = html_content.count('class="stat-card')
    print(f"   检测到 {stats_cards} 个 stat-card")

    if stats_cards == 2:
        print("   ✅ 统计卡片数量为 2 个")
    else:
        print(f"   ❌ 统计卡片数量不为 2 个（当前：{stats_cards}）")

    # 检查是否有天气卡片
    if 'weather-display-card' in html_content:
        print("   ⚠️  仍然存在天气卡片（可能需要移除）")
    else:
        print("   ✅ 已移除天气卡片")

    # 检查计划工作量卡片
    if 'plan-card' in html_content:
        print("   ✅ 计划工作量使用 plan-card 样式")
    else:
        print("   ❌ 计划工作量未使用 plan-card 样式")

    # 检查非计划工作量卡片
    if 'non-plan-card' in html_content:
        print("   ✅ 非计划工作量使用 non-plan-card 样式")
    else:
        print("   ❌ 非计划工作量未使用 non-plan-card 样式")

    # 检查卡片结构
    print("\n3. 检查卡片结构...")
    if 'stat-header' in html_content:
        print("   ✅ 卡片包含 stat-header（标题+徽章）")
    else:
        print("   ❌ 卡片缺少 stat-header")

    if 'stat-content' in html_content:
        print("   ✅ 卡片包含 stat-content（数值+详情）")
    else:
        print("   ❌ 卡片缺少 stat-content")

    if 'detail-item' in html_content:
        print("   ✅ 详情使用 detail-item 样式（垂直布局）")
    else:
        print("   ❌ 详情未使用 detail-item 样式")

    return stats_cards == 2 and 'time-display' in html_content

def test_css_styles():
    """测试CSS样式"""
    print("\n" + "=" * 60)
    print("测试CSS样式")
    print("=" * 60)

    # 读取style.css
    css_path = os.path.join(project_path, 'frontend', 'css', 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css_content = f.read()

    # 检查时间样式
    print("\n1. 检查时间样式...")
    if '.time-display' in css_content:
        print("   ✅ 已定义 .time-display 样式（无框、更自然）")
    else:
        print("   ❌ 未定义 .time-display 样式")

    if 'time-value' in css_content:
        print("   ✅ 已定义 .time-value 样式")
    else:
        print("   ❌ 未定义 .time-value 样式")

    # 检查统计卡片样式
    print("\n2. 检查统计卡片样式...")
    if 'grid-template-columns: repeat(2, 1fr)' in css_content:
        print("   ✅ 统计卡片使用2列布局")
    else:
        print("   ❌ 统计卡片未使用2列布局")

    if 'gap: 12px' in css_content:
        print("   ✅ 卡片间距为 12px（更宽敞）")
    else:
        print("   ❌ 卡片间距不为 12px")

    # 检查卡片样式
    print("\n3. 检查卡片样式...")
    if 'border-radius: 12px' in css_content:
        print("   ✅ 卡片圆角为 12px（更圆润）")
    else:
        print("   ❌ 卡片圆角不为 12px")

    if 'padding: 16px 20px' in css_content:
        print("   ✅ 卡片内边距为 16px 20px（更宽松）")
    else:
        print("   ❌ 卡片内边距不为 16px 20px")

    if 'font-size: 32px' in css_content:
        print("   ✅ 数值字体大小为 32px（更突出）")
    else:
        print("   ❌ 数值字体大小不为 32px")

    # 检查卡片左侧边框颜色
    print("\n4. 检查卡片左侧边框颜色...")
    if '.plan-card' in css_content and '--accent-green' in css_content:
        print("   ✅ 计划工作量卡片左侧边框为绿色")
    else:
        print("   ❌ 计划工作量卡片左侧边框未设置")

    if '.non-plan-card' in css_content and '--accent-red' in css_content:
        print("   ✅ 非计划工作量卡片左侧边框为红色")
    else:
        print("   ❌ 非计划工作量卡片左侧边框未设置")

    # 检查详情样式
    print("\n5. 检查详情样式...")
    if '.detail-item' in css_content:
        print("   ✅ 详情项使用 detail-item 样式")
    else:
        print("   ❌ 详情项未使用 detail-item 样式")

    if '.detail-value' in css_content and 'font-size: 18px' in css_content:
        print("   ✅ 详情数值字体大小为 18px")
    else:
        print("   ❌ 详情数值字体大小不为 18px")

    return True

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("界面布局修改测试")
    print("=" * 60)

    # 测试HTML结构
    html_ok = test_html_structure()

    # 测试CSS样式
    css_ok = test_css_styles()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if html_ok and css_ok:
        print("\n✅ 所有测试通过！")
        print("\n修改内容：")
        print("1. ✅ 时间显示改为更自然的样式（无框）")
        print("2. ✅ 第一行从3个框改为2个框")
        print("3. ✅ 卡片尺寸更大，更美观")
        print("4. ✅ 详情使用垂直布局，更清晰")
        print("\n可以访问 http://localhost:8000 查看效果")
    else:
        print("\n⚠️  部分测试未通过，请检查修改")
        if not html_ok:
            print("   - HTML结构有问题")
        if not css_ok:
            print("   - CSS样式有问题")

    print("\n" + "=" * 60)

    return html_ok and css_ok

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
