#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气卡片修改按钮功能测试
"""

import os
import sys
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_weather_edit_button():
    """测试天气卡片修改按钮功能"""
    print("=" * 60)
    print("天气卡片修改按钮功能测试")
    print("=" * 60)
    
    # 测试1：检查 showWeatherModal 函数
    print("\n[测试1] 检查 showWeatherModal 函数...")
    with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    if 'function showWeatherModal()' in js_content:
        print("✅ showWeatherModal 函数存在")
    else:
        print("❌ showWeatherModal 函数不存在")
        return False
    
    # 测试2：检查是否存在编辑模式
    print("\n[测试2] 检查是否存在编辑模式...")
    if 'weather-edit-mode' in js_content:
        print("✅ 编辑模式HTML存在")
    else:
        print("❌ 编辑模式HTML不存在")
        return False
    
    # 测试3：检查是否存在查看模式
    if 'weather-view-mode' in js_content:
        print("✅ 查看模式HTML存在")
    else:
        print("❌ 查看模式HTML不存在")
        return False
    
    # 测试4：检查是否移除了错误的函数调用
    print("\n[测试4] 检查是否移除了错误的函数调用...")
    if 'openWeatherAdjustModal()' in js_content:
        print("❌ 仍然存在 openWeatherAdjustModal() 调用")
        return False
    else:
        print("✅ 已移除 openWeatherAdjustModal() 调用")
    
    # 测试5：检查编辑按钮事件
    print("\n[测试5] 检查编辑按钮事件...")
    if 'weather-edit-btn' in js_content and "addEventListener('click'" in js_content:
        print("✅ 编辑按钮事件存在")
    else:
        print("❌ 编辑按钮事件不存在")
        return False
    
    # 测试6：检查保存按钮事件
    print("\n[测试6] 检查保存按钮事件...")
    if 'weather-save-btn' in js_content:
        print("✅ 保存按钮存在")
    else:
        print("❌ 保存按钮不存在")
        return False
    
    # 测试7：检查编辑表单样式
    print("\n[测试7] 检查编辑表单样式...")
    with open('frontend/css/workload-modal.css', 'r', encoding='utf-8') as f:
        css_content = f.read()
    
    if '.weather-edit-form' in css_content:
        print("✅ 编辑表单样式存在")
    else:
        print("❌ 编辑表单样式不存在")
        return False
    
    # 测试8：检查表单控件样式
    print("\n[测试8] 检查表单控件样式...")
    if '.form-group' in css_content and 'input' in css_content and 'select' in css_content:
        print("✅ 表单控件样式存在")
    else:
        print("❌ 表单控件样式不完整")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_weather_edit_button()
    sys.exit(0 if success else 1)
